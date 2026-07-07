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

type Draft = {
  cover_letter: CoverLetter
  interview_prep: InterviewPrep
  critic_feedback: CriticFeedback
  revision_count: number
}

type RunResult = Draft & {
  job_analysis: JobAnalysis
  match_report: MatchReport
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
  | ({ type: 'awaiting_approval' } & Draft)
  | ({ type: 'done' } & RunResult)
  | { type: 'error'; message: string }

function initialAgentStates(): Record<string, AgentState> {
  return Object.fromEntries(
    AGENT_ORDER.map((name) => [name, { status: 'pending', attempt: 0 }]),
  )
}

async function consumeStream(
  response: Response,
  onEvent: (event: StreamEvent) => void,
) {
  if (!response.body) return
  const reader = response.body.getReader()
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
      onEvent(JSON.parse(line.slice('data: '.length)) as StreamEvent)
    }
  }
}

export function JobAnalysisForm({ resumeId }: { resumeId: string }) {
  const [postingText, setPostingText] = useState('')
  const [applicationId, setApplicationId] = useState<string | null>(null)
  const [phase, setPhase] = useState<
    'idle' | 'submitting' | 'running' | 'awaiting_approval' | 'done' | 'error'
  >('idle')
  const [error, setError] = useState<string | null>(null)
  const [draft, setDraft] = useState<Draft | null>(null)
  const [result, setResult] = useState<RunResult | null>(null)
  const [agentStates, setAgentStates] = useState<Record<string, AgentState>>(
    initialAgentStates(),
  )
  const [log, setLog] = useState<string[]>([])
  const [feedbackText, setFeedbackText] = useState('')

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
    } else if (event.type === 'awaiting_approval') {
      const { type: _type, ...rest } = event
      setDraft(rest)
      setPhase('awaiting_approval')
    } else if (event.type === 'done') {
      const { type: _type, ...rest } = event
      setResult(rest as RunResult)
      setPhase('done')
    } else if (event.type === 'error') {
      setError(event.message)
      setPhase('error')
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setResult(null)
    setDraft(null)
    setLog([])
    setAgentStates(initialAgentStates())
    setPhase('submitting')

    const createRes = await apiFetch('/applications', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        job_posting_text: postingText,
        resume_id: resumeId,
      }),
    })
    if (!createRes.ok) {
      setPhase('error')
      setError(await createRes.text())
      return
    }
    const application = await createRes.json()
    setApplicationId(application.id)

    setPhase('running')
    const streamRes = await apiFetch(`/applications/${application.id}/run/stream`)
    if (!streamRes.ok) {
      setPhase('error')
      setError(await streamRes.text())
      return
    }
    await consumeStream(streamRes, handleEvent)
  }

  async function handleApprove() {
    if (!applicationId) return
    setPhase('running')
    const res = await apiFetch(`/applications/${applicationId}/approve`, {
      method: 'POST',
    })
    if (!res.ok) {
      setPhase('error')
      setError(await res.text())
      return
    }
    await consumeStream(res, handleEvent)
  }

  async function handleRequestChanges(e: React.FormEvent) {
    e.preventDefault()
    if (!applicationId) return
    setPhase('running')
    const res = await apiFetch(`/applications/${applicationId}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ feedback: feedbackText }),
    })
    if (!res.ok) {
      setPhase('error')
      setError(await res.text())
      return
    }
    setFeedbackText('')
    await consumeStream(res, handleEvent)
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
          disabled={phase === 'submitting' || phase === 'running'}
          className="rounded bg-black px-4 py-2 text-white disabled:opacity-50"
        >
          {phase === 'submitting' || phase === 'running'
            ? 'Running pipeline...'
            : 'Run pipeline'}
        </button>
      </form>

      {phase === 'error' && <p className="text-red-600">{error}</p>}

      {phase !== 'idle' && (
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

      {phase === 'awaiting_approval' && draft && (
        <div className="space-y-3 rounded border-2 border-yellow-400 p-4 text-left">
          <h2 className="text-lg font-semibold">Awaiting your approval</h2>
          <p className="text-sm">
            Critic: cover letter {draft.critic_feedback.cover_letter_score}/100,
            interview prep {draft.critic_feedback.interview_prep_score}/100
            (revision {draft.revision_count})
          </p>
          <div className="rounded border p-3">
            <h3 className="font-medium">Cover letter</h3>
            <p className="whitespace-pre-wrap text-sm">{draft.cover_letter.body}</p>
          </div>
          <div className="rounded border p-3">
            <h3 className="font-medium">Interview prep</h3>
            {draft.interview_prep.questions.map((q, i) => (
              <div key={i} className="mt-2">
                <p className="text-sm font-medium">{q.question}</p>
                <ul className="list-disc pl-5 text-sm">
                  {q.talking_points.map((point, j) => (
                    <li key={j}>{point}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleApprove}
              className="rounded bg-green-600 px-4 py-2 text-white"
            >
              Approve
            </button>
          </div>
          <form onSubmit={handleRequestChanges} className="space-y-2">
            <textarea
              required
              placeholder="What should change?"
              value={feedbackText}
              onChange={(e) => setFeedbackText(e.target.value)}
              rows={3}
              className="w-full rounded border px-3 py-2"
            />
            <button
              type="submit"
              className="rounded bg-orange-600 px-4 py-2 text-white"
            >
              Request changes
            </button>
          </form>
        </div>
      )}

      {result && (
        <div className="space-y-4 text-left">
          <div className="space-y-1 rounded border p-4 text-sm">
            <p className="font-medium text-green-700">Approved</p>
            <p>
              Critic: cover letter {result.critic_feedback.cover_letter_score}/100,
              interview prep {result.critic_feedback.interview_prep_score}/100
              (revision {result.revision_count})
            </p>
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
