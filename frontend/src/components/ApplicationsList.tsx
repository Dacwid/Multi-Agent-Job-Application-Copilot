import { useEffect, useState } from 'react'
import { apiFetch } from '../lib/api'

type ApplicationSummary = {
  id: string
  job_title: string | null
  company: string | null
  status: string
  created_at: string
  match_score: number | null
}

const STATUS_COLOR: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-700',
  running: 'bg-yellow-100 text-yellow-800',
  awaiting_approval: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
}

export function ApplicationsList({ refreshKey }: { refreshKey: number }) {
  const [applications, setApplications] = useState<ApplicationSummary[] | null>(
    null,
  )

  useEffect(() => {
    apiFetch('/applications')
      .then((res) => (res.ok ? res.json() : []))
      .then(setApplications)
  }, [refreshKey])

  if (applications === null) return null

  if (applications.length === 0) {
    return (
      <p className="text-sm text-gray-500">
        No applications yet — paste a job posting below to get started.
      </p>
    )
  }

  return (
    <div className="w-full max-w-xl space-y-2 text-left">
      <h2 className="text-lg font-semibold">Past applications</h2>
      {applications.map((app) => (
        <div
          key={app.id}
          className="flex items-center justify-between rounded border p-3 text-sm"
        >
          <div>
            <div className="font-medium">
              {app.job_title || 'Untitled role'}
              {app.company ? ` at ${app.company}` : ''}
            </div>
            <div className="text-gray-500">
              {new Date(app.created_at).toLocaleString()}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {app.match_score !== null && (
              <span className="text-gray-600">{app.match_score}/100</span>
            )}
            <span
              className={`rounded px-2 py-1 text-xs ${STATUS_COLOR[app.status] ?? 'bg-gray-100 text-gray-700'}`}
            >
              {app.status}
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}
