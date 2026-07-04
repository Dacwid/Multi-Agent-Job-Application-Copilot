import { useEffect, useState } from 'react'
import type { Session } from '@supabase/supabase-js'
import { supabase } from './lib/supabase'
import { Auth } from './pages/Auth'
import { Dashboard } from './pages/Dashboard'

function App() {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session)
      setLoading(false)
    })

    const { data: listener } = supabase.auth.onAuthStateChange(
      (_event, session) => setSession(session),
    )
    return () => listener.subscription.unsubscribe()
  }, [])

  if (loading) return null

  return session ? <Dashboard session={session} /> : <Auth />
}

export default App
