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

export function JobAnalysisForm() {
  const [postingText, setPostingText] = useState('')
  const [status, setStatus] = useState<
    'idle' | 'submitting' | 'analyzing' | 'done' | 'error'
  >('idle')
  const [error, setError] = useState<string | null>(null)
  const [analysis, setAnalysis] = useState<JobAnalysis | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setAnalysis(null)
    setStatus('submitting')

    const createRes = await apiFetch('/applications', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_posting_text: postingText }),
    })
    if (!createRes.ok) {
      setStatus('error')
      setError(await createRes.text())
      return
    }
    const application = await createRes.json()

    setStatus('analyzing')
    const analyzeRes = await apiFetch(
      `/applications/${application.id}/analyze`,
      { method: 'POST' },
    )
    if (!analyzeRes.ok) {
      setStatus('error')
      setError(await analyzeRes.text())
      return
    }
    const artifact = await analyzeRes.json()
    setAnalysis(artifact.content)
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
          disabled={status === 'submitting' || status === 'analyzing'}
          className="rounded bg-black px-4 py-2 text-white disabled:opacity-50"
        >
          {status === 'submitting' || status === 'analyzing'
            ? 'Analyzing...'
            : 'Analyze posting'}
        </button>
      </form>

      {status === 'error' && <p className="text-red-600">{error}</p>}

      {analysis && (
        <div className="space-y-2 rounded border p-4 text-left">
          <h2 className="text-lg font-semibold">
            {analysis.role_title}{' '}
            <span className="text-sm font-normal text-gray-500">
              ({analysis.seniority})
            </span>
          </h2>
          <p>{analysis.summary}</p>
          <div>
            <strong>Required skills:</strong>{' '}
            {analysis.required_skills.join(', ')}
          </div>
          <div>
            <strong>Nice to have:</strong>{' '}
            {analysis.nice_to_have_skills.join(', ')}
          </div>
          <div>
            <strong>Keywords:</strong> {analysis.keywords.join(', ')}
          </div>
          <div>
            <strong>Company signals:</strong>{' '}
            {analysis.company_signals.join(', ')}
          </div>
        </div>
      )}
    </div>
  )
}
