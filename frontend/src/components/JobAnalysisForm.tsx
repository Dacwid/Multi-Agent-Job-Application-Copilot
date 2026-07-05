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

type RunResult = {
  job_analysis: JobAnalysis
  match_report: MatchReport
  cover_letter: CoverLetter
  interview_prep: InterviewPrep
}

export function JobAnalysisForm({ resumeId }: { resumeId: string }) {
  const [postingText, setPostingText] = useState('')
  const [status, setStatus] = useState<
    'idle' | 'submitting' | 'running' | 'done' | 'error'
  >('idle')
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<RunResult | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setResult(null)
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
    const runRes = await apiFetch(`/applications/${application.id}/run`, {
      method: 'POST',
    })
    if (!runRes.ok) {
      setStatus('error')
      setError(await runRes.text())
      return
    }
    setResult(await runRes.json())
    setStatus('done')
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

      {result && (
        <div className="space-y-4 text-left">
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
