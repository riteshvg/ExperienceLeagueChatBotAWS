/**
 * Typed API client for the FastAPI backend.
 */
// In production, VITE_API_URL points to the Railway backend.
// In development, empty string → Vite proxy handles /api/* → localhost:8000
const API_BASE = import.meta.env.VITE_API_URL ?? ''

function authHeaders(): Record<string, string> {
  try {
    const stored = localStorage.getItem('exl_session')
    const session = stored ? JSON.parse(stored) : null
    return session?.sessionToken ? { Authorization: `Bearer ${session.sessionToken}` } : {}
  } catch {
    return {}
  }
}

export interface Citation {
  url: string
  title: string
  product?: string
  doc_type?: string
  score?: number
  description?: string
  video_url?: string
  thumbnail_url?: string
  image_urls?: string[]
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  model?: string
  streaming?: boolean
  follow_ups?: string[]
  feedback?: 1 | -1
}

export type SSEEvent =
  | { type: 'token'; content: string }
  | { type: 'citations'; citations: Citation[] }
  | { type: 'done'; model: string; session_id: string; input_tokens?: number; output_tokens?: number; queries_used?: number; queries_remaining?: number; queries_limit?: number }
  | { type: 'error'; message: string }

// ── Chat ─────────────────────────────────────────────────────────────────────

export async function* streamChat(
  query: string,
  sessionId: string,
  haikuOnly = false,
  messageId?: string,
): AsyncGenerator<SSEEvent> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ query, session_id: sessionId, haiku_only: haikuOnly, message_id: messageId }),
  })

  if (!res.ok) {
    if (res.status === 403) {
      const data = await res.json().catch(() => ({}))
      const err = new Error(data.detail ?? 'Access denied')
      ;(err as any).status = 403
      throw err
    }
    if (res.status === 429) {
      const data = await res.json().catch(() => ({}))
      const err = new Error(data.detail?.message ?? 'Daily limit reached')
      ;(err as any).status = 429
      ;(err as any).detail = data.detail ?? data
      throw err
    }
    throw new Error(`Chat request failed: ${res.status}`)
  }

  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const raw = line.slice(6).trim()
        if (raw && raw !== '[DONE]') {
          try {
            yield JSON.parse(raw) as SSEEvent
          } catch {
            // skip malformed chunk
          }
        }
      }
    }
  }
}

export async function getFollowUps(query: string, answer: string): Promise<string[]> {
  try {
    const res = await fetch(`${API_BASE}/api/chat/follow-ups`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ query, answer }),
    })
    if (!res.ok) return []
    const data = await res.json()
    return data.follow_ups as string[]
  } catch {
    return []
  }
}

export async function submitFeedback(
  messageId: string,
  sessionId: string,
  rating: 1 | -1,
  query: string,
): Promise<void> {
  await fetch(`${API_BASE}/api/chat/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ message_id: messageId, session_id: sessionId, rating, query }),
  })
}

export async function newSession(): Promise<string> {
  const res = await fetch(`${API_BASE}/api/chat/session`, { method: 'POST' })
  const data = await res.json()
  return data.session_id as string
}

export async function clearHistory(sessionId: string): Promise<void> {
  await fetch(`${API_BASE}/api/chat/history/${sessionId}`, { method: 'DELETE' })
}

// ── Admin ─────────────────────────────────────────────────────────────────────

export async function adminLogin(password: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/admin/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  })
  if (!res.ok) throw new Error('Invalid password')
  const data = await res.json()
  return data.token as string
}

async function adminFetch(path: string, token: string) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error(`Admin request failed: ${res.status}`)
  return res.json()
}

export const getAdminStatus = (token: string) => adminFetch('/api/admin/status', token)
export const getAdminSettings = (token: string) => adminFetch('/api/admin/settings', token)
export const getAdminAnalytics = (token: string) => adminFetch('/api/admin/analytics', token)

export async function adminLogout(token: string): Promise<void> {
  await fetch(`${API_BASE}/api/admin/logout`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  })
}

// ── Google OAuth user management ─────────────────────────────────────────────

export interface GoogleUser {
  user_id: string
  email: string
  name: string
  picture: string
  first_seen: string
  last_seen: string | null
  total_queries: number
  is_admin: boolean
  is_disabled: boolean
  daily_query_limit: number
  daily_query_count: number
  daily_reset_at: string | null
}

export interface QueryLog {
  id: number
  message_id: string
  user_id: string
  email: string
  query_text: string
  llm_model: string
  input_tokens: number
  output_tokens: number
  cost_usd: number
  created_at: string
  feedback_rating?: 1 | -1 | null
}

export interface GoogleUserSummary {
  total_users: number
  total_queries_all_time: number
}

async function adminMutate(path: string, token: string, method: string, body?: unknown) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (res.status === 204) return null
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? `Request failed: ${res.status}`)
  }
  return res.json()
}

export const listGoogleUsers = (token: string): Promise<GoogleUser[]> =>
  adminFetch('/api/admin/users', token)

export const updateGoogleUser = (
  token: string,
  userId: string,
  payload: { is_admin?: boolean; is_disabled?: boolean },
): Promise<GoogleUser> =>
  adminMutate(`/api/admin/users/${encodeURIComponent(userId)}`, token, 'PATCH', payload)

export const getGoogleUserSummary = (token: string): Promise<GoogleUserSummary> =>
  adminFetch('/api/admin/users/summary', token)

export const getQueryLogs = (token: string, limit = 100): Promise<QueryLog[]> =>
  adminFetch(`/api/admin/query-logs?limit=${limit}`, token)

export const getKillSwitchStatus = (token: string): Promise<{ enabled: boolean }> =>
  adminFetch('/api/admin/kill-switch', token)

export const setKillSwitch = (token: string, enabled: boolean): Promise<{ enabled: boolean }> =>
  adminMutate('/api/admin/kill-switch', token, 'POST', { enabled })

export const setUserDailyLimit = (token: string, userId: string, limit: number): Promise<GoogleUser> =>
  adminMutate(`/api/admin/users/${encodeURIComponent(userId)}/limit`, token, 'PATCH', { daily_query_limit: limit })

export const setDefaultDailyLimit = (token: string, limit: number): Promise<{ default_daily_limit: number }> =>
  adminMutate('/api/admin/settings/default-limit', token, 'PATCH', { default_daily_limit: limit })

export const applyDefaultLimitToAll = (token: string): Promise<{ users_updated: number; applied_limit: number }> =>
  adminMutate('/api/admin/settings/apply-default-limit', token, 'POST')

export const getDefaultDailyLimit = (token: string): Promise<{ default_daily_limit: number }> =>
  adminFetch('/api/admin/settings/default-limit', token)

export async function getMe(): Promise<{ queries_used: number; queries_limit: number; queries_remaining: number }> {
  try {
    const res = await fetch(`${API_BASE}/api/auth/me`, {
      headers: authHeaders(),
    })
    if (!res.ok) return { queries_used: 0, queries_limit: 20, queries_remaining: 20 }
    return res.json()
  } catch {
    return { queries_used: 0, queries_limit: 20, queries_remaining: 20 }
  }
}
