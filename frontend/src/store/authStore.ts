import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

export interface DemoStatus {
  questions_used: number
  questions_limit: number
  questions_remaining: number
  exhausted: boolean
}

interface AuthState {
  token: string | null
  role: 'user' | 'demo' | null
  isAuthenticated: boolean
  isDemo: boolean
  demoStatus: DemoStatus | null
  error: string | null

  login: (username: string, password: string) => Promise<void>
  refreshDemoStatus: () => Promise<void>
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      role: null,
      isAuthenticated: false,
      isDemo: false,
      demoStatus: null,
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
          const data = await res.json()
          const isDemo = data.role === 'demo'
          set({
            token: data.token,
            role: data.role ?? 'user',
            isAuthenticated: true,
            isDemo,
            demoStatus: isDemo ? (data.demo ?? null) : null,
            error: null,
          })
        } catch {
          set({ error: 'Could not reach the server. Try again.' })
        }
      },

      refreshDemoStatus: async () => {
        if (!get().isDemo) return
        try {
          const res = await fetch(`${API_BASE}/api/auth/demo/status`)
          if (res.ok) {
            const demoStatus = await res.json()
            set({ demoStatus })
          }
        } catch { /* ignore */ }
      },

      logout: () => set({
        token: null, role: null, isAuthenticated: false,
        isDemo: false, demoStatus: null, error: null,
      }),
    }),
    {
      name: 'el-auth',
      partialize: (s) => ({
        token: s.token,
        role: s.role,
        isAuthenticated: s.isAuthenticated,
        isDemo: s.isDemo,
        demoStatus: s.demoStatus,
      }),
    }
  )
)
