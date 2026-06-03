import { useCallback, useEffect, useState } from 'react'
import { adminLogin, adminLogout, getAdminStatus, getAdminSettings, getAdminAnalytics } from '@/lib/api'

const TOKEN_KEY = 'el_admin_token'
const API_BASE = import.meta.env.VITE_API_URL ?? ''

export function useAdmin() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
  const [status, setStatus] = useState<Record<string, unknown> | null>(null)
  const [settings, setSettings] = useState<Record<string, unknown> | null>(null)
  const [analytics, setAnalytics] = useState<Record<string, unknown> | null>(null)
  const [demoStatus, setDemoStatus] = useState<Record<string, unknown> | null>(null)
  const [feedback, setFeedback] = useState<Record<string, unknown> | null>(null)
  const [refreshStatus, setRefreshStatus] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const login = useCallback(async (password: string) => {
    setError(null)
    setLoading(true)
    try {
      const t = await adminLogin(password)
      localStorage.setItem(TOKEN_KEY, t)
      setToken(t)
    } catch (e) {
      setError('Invalid password')
    } finally {
      setLoading(false)
    }
  }, [])

  const logout = useCallback(async () => {
    if (token) await adminLogout(token).catch(() => {})
    localStorage.removeItem(TOKEN_KEY)
    setToken(null)
    setStatus(null)
    setSettings(null)
    setAnalytics(null)
  }, [token])

  const refresh = useCallback(async () => {
    if (!token) return
    setLoading(true)
    try {
      const [s, cfg, a, demo, fb, rs] = await Promise.all([
        getAdminStatus(token),
        getAdminSettings(token),
        getAdminAnalytics(token),
        fetch(`${API_BASE}/api/admin/demo/status`, {
          headers: { Authorization: `Bearer ${token}` },
        }).then((r) => r.json()),
        fetch(`${API_BASE}/api/admin/feedback`, {
          headers: { Authorization: `Bearer ${token}` },
        }).then((r) => r.json()),
        fetch(`${API_BASE}/api/admin/refresh/status`, {
          headers: { Authorization: `Bearer ${token}` },
        }).then((r) => r.json()),
      ])
      setStatus(s)
      setSettings(cfg)
      setAnalytics(a)
      setDemoStatus(demo)
      setFeedback(fb)
      setRefreshStatus(rs)
    } catch {
      logout()
    } finally {
      setLoading(false)
    }
  }, [token, logout])

  const resetDemo = useCallback(async () => {
    if (!token) return
    const res = await fetch(`${API_BASE}/api/admin/demo/reset`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    })
    if (res.ok) {
      const updated = await res.json()
      setDemoStatus(updated)
    }
  }, [token])

  useEffect(() => {
    if (token) refresh()
  }, [token]) // eslint-disable-line react-hooks/exhaustive-deps

  const triggerRefresh = useCallback(async (force = false) => {
    if (!token) return
    const res = await fetch(`${API_BASE}/api/admin/refresh/start?force=${force}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    })
    if (res.ok) {
      const updated = await res.json()
      // Poll status every 3s while running
      if (updated.started) {
        const poll = setInterval(async () => {
          const sr = await fetch(`${API_BASE}/api/admin/refresh/status`, {
            headers: { Authorization: `Bearer ${token}` },
          }).then((r) => r.json())
          setRefreshStatus(sr)
          if (sr.state !== 'running') clearInterval(poll)
        }, 3000)
      }
    }
  }, [token])

  return { isAuthenticated: !!token, login, logout, refresh, resetDemo, triggerRefresh, status, settings, analytics, demoStatus, feedback, refreshStatus, loading, error }
}
