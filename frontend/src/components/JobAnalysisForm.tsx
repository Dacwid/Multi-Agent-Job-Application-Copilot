import { useState } from 'react'
import { apiFetch } from '../lib/api'

type JobAnalysis = {
  role_title: string
  seniority: string
  required_skills: string[]
  nice_to_have_skills: string[]
  keywords: string[]
  company_signals: string[]
  summary: string
}

type MatchReport = {
  match_score: number
  strengths: string[]
  gaps: string[]
  suggestions: string[]
}

type CoverLetter = {
  body: string
}

type InterviewPrep = {
  questions: { question: string; talking_points: string[] }[]
}

type CriticFeedback = {
  cover_letter_pass: boolean
  cover_letter_score: number
  cover_letter_feedback: string[]
  interview_prep_pass: boolean
  interview_prep_score: number
  interview_prep_feedback: string[]
}

type RunResult = {
  job_analysis: JobAnalysis
  match_report: MatchReport
  cover_letter: CoverLetter
  interview_prep: InterviewPrep
  critic_feedback: CriticFeedback
  revision_count: number
}

const AGENT_ORDER = [
  'job_analyst',
  'resume_matcher',
  'cover_letter',
  'interview_prep',
  'critic',
] as const

const AGENT_LABELS: Record<(typeof AGENT_ORDER)[number], string> = {
  job_analyst: 'Job Analyst',
  resume_matcher: 'Resume Matcher',
  cover_letter: 'Cover Letter',
  interview_prep: 'Interview Prep',
  critic: 'Critic',
}

type NodeStatus = 'pending' | 'running' | 'completed' | 'failed'

type AgentState = { status: NodeStatus; attempt: number }

type StreamEvent =
  | { type: 'node_start'; agent_name: string; attempt: number }
  | {
      type: 'node_finish'
      agent_name: string
      attempt: number
      status: 'completed' | 'failed'
      output?: unknown
    }
  | ({ type: 'done' } & RunResult)
  | { type: 'error'; message: string }

function initialAgentStates(): Record<string, AgentState> {
  return Object.fromEntries(
    AGENT_ORDER.map((name) => [name, { status: 'pending', attempt: 0 }]),
  )
}

export function JobAnalysisForm({ resumeId }: { resumeId: string }) {
  const [postingText, setPostingText] = useState('')
  const [status, setStatus] = useState<
    'idle' | 'submitting' | 'running' | 'done' | 'error'
  >('idle')
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<RunResult | null>(null)
  const [agentStates, setAgentStates] = useState<Record<string, AgentState>>(
    initialAgentStates(),
  )
  const [log, setLog] = useState<string[]>([])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setResult(null)
    setLog([])
    setAgentStates(initialAgentStates())
    setStatus('submitting')

    const createRes = await apiFetch('/applications', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        job_posting_text: postingText,
        resume_id: resumeId,
      }),
    })
    if (!createRes.ok) {
      setStatus('error')
      setError(await createRes.text())
      return
    }
    const application = await createRes.json()

    setStatus('running')
    const streamRes = await apiFetch(`/applications/${application.id}/run/stream`)
    if (!streamRes.ok || !streamRes.body) {
      setStatus('error')
      setError(await streamRes.text())
      return
    }

    const reader = streamRes.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      const frames = buffer.split('\n\n')
      buffer = frames.pop() ?? ''

      for (const frame of frames) {
        const line = frame.split('\n').find((l) => l.startsWith('data: '))
        if (!line) continue
        const event = JSON.parse(line.slice('data: '.length)) as StreamEvent
        handleEvent(event)
      }
    }
  }

  function handleEvent(event: StreamEvent) {
    if (event.type === 'node_start') {
      setAgentStates((prev) => ({
        ...prev,
        [event.agent_name]: { status: 'running', attempt: event.attempt },
      }))
      setLog((prev) => [
        ...prev,
        `${AGENT_LABELS[event.agent_name as keyof typeof AGENT_LABELS] ?? event.agent_name} started (attempt ${event.attempt})`,
      ])
    } else if (event.type === 'node_finish') {
      setAgentStates((prev) => ({
        ...prev,
        [event.agent_name]: { status: event.status, attempt: event.attempt },
      }))
      setLog((prev) => [
        ...prev,
        `${AGENT_LABELS[event.agent_name as keyof typeof AGENT_LABELS] ?? event.agent_name} ${event.status} (attempt ${event.attempt})`,
      ])
    } else if (event.type === 'done') {
      const { type: _type, ...rest } = event
      setResult(rest as RunResult)
      setStatus('done')
    } else if (event.type === 'error') {
      setError(event.message)
      setStatus('error')
    }
  }

  return (
    <div className="w-full max-w-xl space-y-4">
      <form onSubmit={handleSubmit} className="space-y-2">
        <textarea
          required
          placeholder="Paste job posting text here"
          value={postingText}
          onChange={(e) => setPostingText(e.target.value)}
          rows={8}
          className="w-full rounded border px-3 py-2"
        />
        <button
          type="submit"
          disabled={status === 'submitting' || status === 'running'}
          className="rounded bg-black px-4 py-2 text-white disabled:opacity-50"
        >
          {status === 'submitting' || status === 'running'
            ? 'Running pipeline...'
            : 'Run pipeline'}
        </button>
      </form>

      {status === 'error' && <p className="text-red-600">{error}</p>}

      {status !== 'idle' && (
        <div className="grid grid-cols-5 gap-2 text-center text-xs">
          {AGENT_ORDER.map((name) => {
            const agent = agentStates[name]
            const color =
              agent.status === 'completed'
                ? 'bg-green-100 text-green-800'
                : agent.status === 'failed'
                  ? 'bg-red-100 text-red-800'
                  : agent.status === 'running'
                    ? 'bg-yellow-100 text-yellow-800'
                    : 'bg-gray-100 text-gray-500'
            return (
              <div key={name} className={`rounded p-2 ${color}`}>
                <div className="font-medium">{AGENT_LABELS[name]}</div>
                <div>
                  {agent.status}
                  {agent.attempt > 1 ? ` (#${agent.attempt})` : ''}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {log.length > 0 && (
        <div className="max-h-40 space-y-1 overflow-y-auto rounded border p-2 text-left text-xs text-gray-600">
          {log.map((line, i) => (
            <div key={i}>{line}</div>
          ))}
        </div>
      )}

      {result && (
        <div className="space-y-4 text-left">
          <div className="space-y-1 rounded border p-4 text-sm">
            <p>
              Critic rounds: {result.revision_count} — cover letter{' '}
              <span
                className={
                  result.critic_feedback.cover_letter_pass
                    ? 'text-green-600'
                    : 'text-red-600'
                }
              >
                {result.critic_feedback.cover_letter_pass ? 'passed' : 'flagged'}
              </span>{' '}
              ({result.critic_feedback.cover_letter_score}/100), interview prep{' '}
              <span
                className={
                  result.critic_feedback.interview_prep_pass
                    ? 'text-green-600'
                    : 'text-red-600'
                }
              >
                {result.critic_feedback.interview_prep_pass ? 'passed' : 'flagged'}
              </span>{' '}
              ({result.critic_feedback.interview_prep_score}/100)
            </p>
            {!result.critic_feedback.cover_letter_pass && (
              <p>
                Cover letter feedback:{' '}
                {result.critic_feedback.cover_letter_feedback.join('; ')}
              </p>
            )}
            {!result.critic_feedback.interview_prep_pass && (
              <p>
                Interview prep feedback:{' '}
                {result.critic_feedback.interview_prep_feedback.join('; ')}
              </p>
            )}
          </div>

          <div className="space-y-2 rounded border p-4">
            <h2 className="text-lg font-semibold">
              {result.job_analysis.role_title}{' '}
              <span className="text-sm font-normal text-gray-500">
                ({result.job_analysis.seniority})
              </span>
            </h2>
            <p>{result.job_analysis.summary}</p>
            <div>
              <strong>Required skills:</strong>{' '}
              {result.job_analysis.required_skills.join(', ')}
            </div>
            <div>
              <strong>Nice to have:</strong>{' '}
              {result.job_analysis.nice_to_have_skills.join(', ')}
            </div>
            <div>
              <strong>Keywords:</strong>{' '}
              {result.job_analysis.keywords.join(', ')}
            </div>
            <div>
              <strong>Company signals:</strong>{' '}
              {result.job_analysis.company_signals.join(', ')}
            </div>
          </div>

          <div className="space-y-2 rounded border p-4">
            <h2 className="text-lg font-semibold">
              Match report ({result.match_report.match_score}/100)
            </h2>
            <div>
              <strong>Strengths:</strong>{' '}
              {result.match_report.strengths.join(', ')}
            </div>
            <div>
              <strong>Gaps:</strong> {result.match_report.gaps.join(', ')}
            </div>
            <div>
              <strong>Suggestions:</strong>{' '}
              {result.match_report.suggestions.join(', ')}
            </div>
          </div>

          <div className="space-y-2 rounded border p-4">
            <h2 className="text-lg font-semibold">Cover letter</h2>
            <p className="whitespace-pre-wrap">{result.cover_letter.body}</p>
          </div>

          <div className="space-y-2 rounded border p-4">
            <h2 className="text-lg font-semibold">Interview prep</h2>
            {result.interview_prep.questions.map((q, i) => (
              <div key={i}>
                <p className="font-medium">{q.question}</p>
                <ul className="list-disc pl-5">
                  {q.talking_points.map((point, j) => (
                    <li key={j}>{point}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
