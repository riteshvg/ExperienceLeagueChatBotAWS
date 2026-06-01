import { useCallback, useEffect, useState } from 'react'
import { adminLogin, adminLogout, getAdminStatus, getAdminSettings, getAdminAnalytics } from '@/lib/api'

const TOKEN_KEY = 'el_admin_token'

export function useAdmin() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
  const [status, setStatus] = useState<Record<string, unknown> | null>(null)
  const [settings, setSettings] = useState<Record<string, unknown> | null>(null)
  const [analytics, setAnalytics] = useState<Record<string, unknown> | null>(null)
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
      const [s, cfg, a] = await Promise.all([
        getAdminStatus(token),
        getAdminSettings(token),
        getAdminAnalytics(token),
      ])
      setStatus(s)
      setSettings(cfg)
      setAnalytics(a)
    } catch {
      logout()
    } finally {
      setLoading(false)
    }
  }, [token, logout])

  useEffect(() => {
    if (token) refresh()
  }, [token]) // eslint-disable-line react-hooks/exhaustive-deps

  return { isAuthenticated: !!token, login, logout, refresh, status, settings, analytics, loading, error }
}
