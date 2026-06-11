import { create } from 'zustand'

const API_BASE = import.meta.env.VITE_API_URL ?? ''
const SESSION_KEY = 'exl_session'

export interface SessionData {
  sessionToken: string
  userId: string
  email: string
  name: string
  picture: string
  expiresAt: number  // Unix seconds
  is_admin: boolean
}

interface AuthState {
  session: SessionData | null
  isAuthenticated: boolean

  /** Called by OAuthCallback after Google redirects back. */
  setSession: (data: SessionData) => void
  /** Redirects browser to the Google OAuth consent screen via the backend. */
  initiateGoogleLogin: () => void
  /** Invalidates the server session and clears local state. */
  logout: () => Promise<void>
}

function loadSession(): SessionData | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY)
    if (!raw) return null
    const data = JSON.parse(raw) as SessionData
    // Expired?
    if (data.expiresAt < Math.floor(Date.now() / 1000)) {
      localStorage.removeItem(SESSION_KEY)
      return null
    }
    return data
  } catch {
    return null
  }
}

const initial = loadSession()

export const useAuthStore = create<AuthState>()((set, get) => ({
  session: initial,
  isAuthenticated: initial !== null,

  setSession(data) {
    localStorage.setItem(SESSION_KEY, JSON.stringify(data))
    set({ session: data, isAuthenticated: true })
  },

  initiateGoogleLogin() {
    window.location.href = `${API_BASE}/api/auth/google`
  },

  async logout() {
    const token = get().session?.sessionToken
    if (token) {
      try {
        await fetch(`${API_BASE}/api/auth/session`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` },
        })
      } catch {
        // Non-fatal — clear locally regardless
      }
    }
    localStorage.removeItem(SESSION_KEY)
    set({ session: null, isAuthenticated: false })
  },
}))
