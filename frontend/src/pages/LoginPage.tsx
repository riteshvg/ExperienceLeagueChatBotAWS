import { useEffect } from 'react'
import { useAuthStore } from '@/store/authStore'

export function LoginPage() {
  const { initiateGoogleLogin, isAuthenticated } = useAuthStore()

  // If arriving here after an error redirect from the OAuth callback
  const params = new URLSearchParams(window.location.search)
  const oauthError = params.get('error')

  // If somehow already authenticated, let ProtectedRoute handle the redirect
  useEffect(() => {
    if (isAuthenticated) {
      window.location.replace(
        import.meta.env.BASE_URL?.replace(/\/$/, '') || '/'
      )
    }
  }, [isAuthenticated])

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <img src={`${import.meta.env.BASE_URL}rovrlogo.png`} alt="Rovr" className="h-14 w-auto mb-4" />
          <h1 className="text-xl font-semibold text-slate-800">Rovr</h1>
          <p className="text-sm text-slate-400 mt-1">Sign in to continue</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm px-6 py-7 space-y-5">
          {oauthError && (
            <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              Sign-in failed ({oauthError.replace(/_/g, ' ')}). Please try again.
            </p>
          )}

          {/* Google Sign-In button */}
          <button
            onClick={initiateGoogleLogin}
            className="w-full flex items-center justify-center gap-3 px-4 py-2.5 rounded-xl
              bg-white border border-slate-300 shadow-sm text-sm font-medium text-slate-700
              hover:bg-slate-50 hover:border-slate-400 transition-colors"
          >
            {/* Google logo SVG */}
            <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
              <path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.615z"/>
              <path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.258c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z"/>
              <path fill="#FBBC05" d="M3.964 10.707A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.707V4.961H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.039l3.007-2.332z"/>
              <path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.961L3.964 7.293C4.672 5.163 6.656 3.58 9 3.58z"/>
            </svg>
            Sign in with Google
          </button>

          <p className="text-center text-xs text-slate-400 leading-relaxed">
            Sign-in is required to manage usage and prevent abuse.
            Your data is not shared.
          </p>
        </div>

      </div>
    </div>
  )
}
