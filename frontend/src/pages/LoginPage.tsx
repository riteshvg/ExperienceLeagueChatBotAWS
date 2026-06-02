import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'

export function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const { login, error } = useAuthStore()
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!username.trim() || !password.trim()) return
    setLoading(true)
    await login(username.trim(), password)
    setLoading(false)
    // Navigate to app if login succeeded (no error in store)
    if (useAuthStore.getState().isAuthenticated) {
      navigate('/', { replace: true })
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-violet-600
            flex items-center justify-center mb-4 shadow-md">
            <span className="text-white font-bold text-lg">EL</span>
          </div>
          <h1 className="text-xl font-semibold text-slate-800">Experience League Assistant</h1>
          <p className="text-sm text-slate-400 mt-1">Sign in to continue</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-slate-200
          shadow-sm px-6 py-7 space-y-4">

          <div className="space-y-1">
            <label className="text-xs font-medium text-slate-600">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              autoComplete="username"
              placeholder="Enter your username"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm
                text-slate-800 placeholder:text-slate-400 focus:outline-none
                focus:border-blue-400 focus:ring-1 focus:ring-blue-400 transition"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-slate-600">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              placeholder="Enter your password"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm
                text-slate-800 placeholder:text-slate-400 focus:outline-none
                focus:border-blue-400 focus:ring-1 focus:ring-blue-400 transition"
            />
          </div>

          {error && (
            <p className="text-xs text-red-600 bg-red-50 border border-red-200
              rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading || !username.trim() || !password.trim()}
            className="w-full py-2.5 rounded-xl text-sm font-medium transition-colors
              bg-blue-600 text-white hover:bg-blue-700
              disabled:bg-slate-200 disabled:text-slate-400 disabled:cursor-not-allowed"
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="text-center text-xs text-slate-400 mt-6">
          Unofficial tool — not an Adobe product
        </p>
      </div>
    </div>
  )
}
