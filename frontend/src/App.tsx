import { useEffect, useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL

function App() {
  const [status, setStatus] = useState<'loading' | 'ok' | 'error'>('loading')

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((res) => (res.ok ? res.json() : Promise.reject(res)))
      .then((data) => setStatus(data.status === 'ok' ? 'ok' : 'error'))
      .catch(() => setStatus('error'))
  }, [])

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <h1 className="text-2xl font-semibold">ApplyPilot</h1>
        <p className="mt-2">
          Backend status:{' '}
          <span
            className={
              status === 'ok'
                ? 'text-green-600'
                : status === 'error'
                  ? 'text-red-600'
                  : 'text-gray-500'
            }
          >
            {status}
          </span>
        </p>
      </div>
    </div>
  )
}

export default App
