import { useState } from 'react'
import type { Session } from '@supabase/supabase-js'
import { apiFetch } from '../lib/api'
import { supabase } from '../lib/supabase'
import { JobAnalysisForm } from '../components/JobAnalysisForm'
import { ApplicationsList } from '../components/ApplicationsList'

export function Dashboard({ session }: { session: Session }) {
  const [status, setStatus] = useState<
    'idle' | 'uploading' | 'done' | 'error'
  >('idle')
  const [error, setError] = useState<string | null>(null)
  const [resumeId, setResumeId] = useState<string | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    setStatus('uploading')
    setError(null)

    const formData = new FormData()
    formData.append('file', file)

    const res = await apiFetch('/resumes', { method: 'POST', body: formData })
    if (res.ok) {
      const resume = await res.json()
      setResumeId(resume.id)
      setStatus('done')
    } else {
      setStatus('error')
      setError(await res.text())
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 py-8">
      <p>Signed in as {session.user.email}</p>

      <ApplicationsList refreshKey={refreshKey} />

      <label className="cursor-pointer rounded bg-black px-4 py-2 text-white">
        Upload resume (.pdf or .docx)
        <input
          type="file"
          accept=".pdf,.docx"
          className="hidden"
          onChange={handleUpload}
        />
      </label>

      {status === 'uploading' && <p>Uploading...</p>}
      {status === 'done' && <p className="text-green-600">Resume saved.</p>}
      {status === 'error' && <p className="text-red-600">{error}</p>}

      {resumeId ? (
        <JobAnalysisForm
          resumeId={resumeId}
          onCompleted={() => setRefreshKey((k) => k + 1)}
        />
      ) : (
        <p className="text-sm text-gray-500">
          Upload a resume to analyze a job posting.
        </p>
      )}

      <button
        onClick={() => supabase.auth.signOut()}
        className="text-sm underline"
      >
        Sign out
      </button>
    </div>
  )
}
