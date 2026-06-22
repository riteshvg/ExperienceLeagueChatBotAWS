import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore, type SessionData } from '@/store/authStore'

/**
 * Landing page for the Google OAuth redirect.
 *
 * The FastAPI callback endpoint sends the user here with session data
 * as query parameters:
 *   ?token=...&user_id=...&email=...&name=...&picture=...&expires_at=...
 *
 * On error:
 *   ?error=<reason>
 */
export function OAuthCallback() {
  const { setSession } = useAuthStore()
  const navigate = useNavigate()

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)

    const error = params.get('error')
    if (error) {
      // Strip query string and forward error to login page
      navigate(`/login?error=${error}`, { replace: true })
      return
    }

    const token = params.get('token')
    const userId = params.get('user_id')
    const email = params.get('email')
    const name = params.get('name') ?? email ?? ''
    const picture = params.get('picture') ?? ''
    const expiresAtRaw = params.get('expires_at')

    if (!token || !userId || !email) {
      navigate('/login?error=missing_params', { replace: true })
      return
    }

    const expiresAt = expiresAtRaw
      ? parseInt(expiresAtRaw, 10)
      : Math.floor(Date.now() / 1000) + 30 * 24 * 60 * 60

    const is_admin = params.get('is_admin') === '1'

    const data: SessionData = { sessionToken: token, userId, email, name, picture, expiresAt, is_admin }
    setSession(data)

    // Remove sensitive params from browser history before navigating
    window.history.replaceState({}, '', window.location.pathname)
    navigate('/', { replace: true })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
        <p className="text-sm text-slate-500">Signing you in…</p>
      </div>
    </div>
  )
}
