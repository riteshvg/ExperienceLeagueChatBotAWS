import { useCallback, useEffect, useState } from 'react'
import {
  adminLogin, adminLogout, getAdminStatus, getAdminSettings, getAdminAnalytics,
  listGoogleUsers, updateGoogleUser, getGoogleUserSummary, getQueryLogs,
  exportQueriesExcel, exportUsersExcel,
  getKillSwitchStatus, setKillSwitch as apiSetKillSwitch,
  setUserDailyLimit, setDefaultDailyLimit, applyDefaultLimitToAll, getDefaultDailyLimit,
  setUserMonthlyLimit, getDefaultMonthlyLimit, setDefaultMonthlyLimit,
  type GoogleUser, type GoogleUserSummary, type QueryLog,
  type PaginatedQueryLogs, type PaginatedGoogleUsers,
} from '@/lib/api'

const TOKEN_KEY = 'el_admin_token'
const API_BASE = import.meta.env.VITE_API_URL ?? ''

async function adminGetJson(path: string, token: string): Promise<unknown | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export interface RefreshStatus {
  state: 'idle' | 'running' | 'success' | 'failed'
  last_run: string | null
  last_run_duration_s: number | null
  files_updated: number
  chunks_indexed: number
  last_run_source?: string
  last_run_source_label?: string
  error: string | null
  log: string[]
  started_at?: string
}

export { type GoogleUser, type GoogleUserSummary, type QueryLog }

export function useAdmin() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
  const [status, setStatus] = useState<Record<string, unknown> | null>(null)
  const [settings, setSettings] = useState<Record<string, unknown> | null>(null)
  const [analytics, setAnalytics] = useState<Record<string, unknown> | null>(null)
  const [demoStatus, setDemoStatus] = useState<Record<string, unknown> | null>(null)
  const [feedback, setFeedback] = useState<Record<string, unknown> | null>(null)
  const [refreshStatus, setRefreshStatus] = useState<RefreshStatus | null>(null)
  const [googleUsers, setGoogleUsers] = useState<PaginatedGoogleUsers | null>(null)
  const [googleUserSummary, setGoogleUserSummary] = useState<GoogleUserSummary | null>(null)
  const [queryLogs, setQueryLogs] = useState<PaginatedQueryLogs | null>(null)
  const [exporting, setExporting] = useState(false)
  const [exportingUsers, setExportingUsers] = useState(false)
  const [killSwitchEnabled, setKillSwitchEnabled] = useState<boolean>(true)
  const [defaultDailyLimit, setDefaultDailyLimitState] = useState<number>(20)
  const [defaultMonthlyLimit, setDefaultMonthlyLimitState] = useState<number>(20)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const login = useCallback(async (password: string) => {
    setError(null)
    setLoading(true)
    try {
      const t = await adminLogin(password)
      localStorage.setItem(TOKEN_KEY, t)
      setToken(t)
    } catch {
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
    setGoogleUsers(null)
    setGoogleUserSummary(null)
    setQueryLogs(null)
  }, [token])

  const refresh = useCallback(async () => {
    if (!token) return
    setLoading(true)
    try {
      const [s, cfg, a, demo, fb, rs, summary, ks, defaultLimit, defaultMonthly] = await Promise.all([
        getAdminStatus(token),
        getAdminSettings(token),
        getAdminAnalytics(token),
        adminGetJson('/api/admin/demo/status', token),
        adminGetJson('/api/admin/feedback', token),
        adminGetJson('/api/admin/refresh/status', token),
        getGoogleUserSummary(token).catch(() => null),
        getKillSwitchStatus(token).catch(() => ({ enabled: true })),
        getDefaultDailyLimit(token).catch(() => ({ default_daily_limit: 20 })),
        getDefaultMonthlyLimit(token).catch(() => ({ default_monthly_limit: 20 })),
      ])
      setStatus(s)
      setSettings(cfg)
      setAnalytics(a)
      setDemoStatus(demo as Record<string, unknown> | null)
      setFeedback(fb as Record<string, unknown> | null)
      setRefreshStatus(rs as RefreshStatus | null)
      setGoogleUserSummary(summary)
      setQueryLogs(null)
      setGoogleUsers(null)
      setKillSwitchEnabled((ks as { enabled: boolean }).enabled)
      setDefaultDailyLimitState((defaultLimit as { default_daily_limit: number }).default_daily_limit)
      setDefaultMonthlyLimitState((defaultMonthly as { default_monthly_limit: number }).default_monthly_limit)
    } catch {
      logout()
    } finally {
      setLoading(false)
    }
  }, [token, logout])


  const fetchUserPage = useCallback(async (
    page = 1,
    pageSize = 25,
    sortBy = 'last_seen',
    sortOrder = 'desc',
    search = '',
  ) => {
    if (!token) return
    try {
      const data = await listGoogleUsers(token, { page, pageSize, sortBy, sortOrder, search })
      setGoogleUsers(data)
    } catch { /* silent */ }
  }, [token])

  const fetchQueryPage = useCallback(async (
    page = 1,
    pageSize = 25,
    sortBy = 'created_at',
    sortOrder = 'desc',
  ) => {
    if (!token) return
    try {
      const data = await getQueryLogs(token, { page, pageSize, sortBy, sortOrder })
      setQueryLogs(data)
    } catch { /* silent — don't log out on a pagination call */ }
  }, [token])

  const exportUsers = useCallback(async (search?: string) => {
    if (!token) return
    setExportingUsers(true)
    try {
      await exportUsersExcel(token, search)
    } finally {
      setExportingUsers(false)
    }
  }, [token])

  const patchGoogleUserInPage = useCallback((updated: GoogleUser) => {
    setGoogleUsers((prev) => {
      if (!prev) return prev
      return {
        ...prev,
        data: prev.data.map((u) => (u.user_id === updated.user_id ? updated : u)),
      }
    })
  }, [])

  const exportQueries = useCallback(async (dateFrom?: string, dateTo?: string) => {
    if (!token) return
    setExporting(true)
    try {
      await exportQueriesExcel(token, dateFrom, dateTo)
    } finally {
      setExporting(false)
    }
  }, [token])

  const resetDemo = useCallback(async () => {
    if (!token) return
    const res = await fetch(`${API_BASE}/api/admin/demo/reset`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    })
    if (res.ok) setDemoStatus(await res.json())
  }, [token])

  useEffect(() => {
    if (token) refresh()
  }, [token]) // eslint-disable-line react-hooks/exhaustive-deps

  const triggerGitHubActions = useCallback(async (force = false) => {
    if (!token) return { triggered: false }
    const res = await fetch(`${API_BASE}/api/admin/refresh/trigger-actions?force=${force}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    })
    return res.json()
  }, [token])

  const triggerRefresh = useCallback(async (force = false) => {
    if (!token) return
    const res = await fetch(`${API_BASE}/api/admin/refresh/start?force=${force}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    })
    if (res.ok) {
      const updated = await res.json()
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

  const setGoogleUserAdmin = useCallback(async (userId: string, isAdmin: boolean) => {
    if (!token) throw new Error('Not authenticated')
    const updated = await updateGoogleUser(token, userId, { is_admin: isAdmin })
    patchGoogleUserInPage(updated)
    return updated
  }, [token, patchGoogleUserInPage])

  const setUserDisabled = useCallback(async (userId: string, isDisabled: boolean) => {
    if (!token) throw new Error('Not authenticated')
    const updated = await updateGoogleUser(token, userId, { is_disabled: isDisabled })
    patchGoogleUserInPage(updated)
    return updated
  }, [token, patchGoogleUserInPage])

  const toggleKillSwitch = useCallback(async (enabled: boolean) => {
    if (!token) throw new Error('Not authenticated')
    const result = await apiSetKillSwitch(token, enabled)
    setKillSwitchEnabled(result.enabled)
    return result
  }, [token])

  const updateUserDailyLimit = useCallback(async (userId: string, limit: number) => {
    if (!token) throw new Error('Not authenticated')
    const updated = await setUserDailyLimit(token, userId, limit)
    patchGoogleUserInPage(updated)
    return updated
  }, [token, patchGoogleUserInPage])

  const updateDefaultLimit = useCallback(async (limit: number) => {
    if (!token) throw new Error('Not authenticated')
    await setDefaultDailyLimit(token, limit)
    setDefaultDailyLimitState(limit)
  }, [token])

  const updateUserMonthlyLimit = useCallback(async (userId: string, limit: number) => {
    if (!token) throw new Error('Not authenticated')
    const updated = await setUserMonthlyLimit(token, userId, limit)
    patchGoogleUserInPage(updated)
    return updated
  }, [token, patchGoogleUserInPage])

  const updateDefaultMonthlyLimit = useCallback(async (limit: number) => {
    if (!token) throw new Error('Not authenticated')
    await setDefaultMonthlyLimit(token, limit)
    setDefaultMonthlyLimitState(limit)
  }, [token])

  const bulkApplyDefaultLimit = useCallback(async () => {
    if (!token) throw new Error('Not authenticated')
    return applyDefaultLimitToAll(token)
  }, [token])

  return {
    isAuthenticated: !!token,
    login, logout, refresh, resetDemo,
    triggerRefresh, triggerGitHubActions,
    status, settings, analytics, demoStatus, feedback, refreshStatus,
    googleUsers, googleUserSummary, queryLogs,
    fetchUserPage, fetchQueryPage, exportUsers, exportQueries,
    exportingUsers, exporting,
    setGoogleUserAdmin, setUserDisabled,
    killSwitchEnabled, toggleKillSwitch,
    defaultDailyLimit, updateUserDailyLimit, updateDefaultLimit, bulkApplyDefaultLimit,
    defaultMonthlyLimit, updateUserMonthlyLimit, updateDefaultMonthlyLimit,
    loading, error,
  }
}
