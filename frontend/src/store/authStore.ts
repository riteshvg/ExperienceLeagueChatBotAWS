import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

interface AuthState {
  token: string | null
  isAuthenticated: boolean
  error: string | null

  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      isAuthenticated: false,
      error: null,

      login: async (username, password) => {
        set({ error: null })
        try {
          const res = await fetch(`${API_BASE}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
          })
          if (!res.ok) {
            const data = await res.json().catch(() => ({}))
            set({ error: data.detail ?? 'Invalid username or password' })
            return
          }
          const { token } = await res.json()
          set({ token, isAuthenticated: true, error: null })
        } catch {
          set({ error: 'Could not reach the server. Try again.' })
        }
      },

      logout: () => set({ token: null, isAuthenticated: false, error: null }),
    }),
    {
      name: 'el-auth',
      partialize: (s) => ({ token: s.token, isAuthenticated: s.isAuthenticated }),
    }
  )
)
