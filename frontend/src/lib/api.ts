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

export interface RetrievalSource {
  url: string
  title: string
  product?: string
  repo_path?: string
  score?: number
  cited?: boolean
}

export interface RetrievalEvidence {
  source_count: number
  citation_count: number
  top_score: number
  avg_score: number
  product_filter?: string | null
  evidence_level: 'none' | 'weak' | 'moderate' | 'strong'
  grounding_level: 'documented' | 'partial' | 'inferred' | 'insufficient'
  match_label: string
  grounding_label: string
  failure_reason?: 'no_retrieval' | 'no_direct_match' | 'off_topic' | null
  banner?: string | null
  sources: RetrievalSource[]
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  evidence?: RetrievalEvidence
  model?: string
  streaming?: boolean
  follow_ups?: string[]
  feedback?: 1 | -1
}

export type SSEEvent =
  | { type: 'token'; content: string }
  | { type: 'citations'; citations: Citation[] }
  | ({ type: 'evidence' } & RetrievalEvidence)
  | { type: 'done'; model: string; session_id: string; input_tokens?: number; output_tokens?: number; queries_used?: number; queries_remaining?: number; queries_limit?: number }
  | { type: 'error'; message: string }

export interface KnowledgeBankMaintenance {
  active: boolean
  message: string
  check_back_at: string
  started_at?: string
  eta_minutes?: number
}

export interface HealthResponse {
  status: 'ok' | 'updating'
  chromadb: { document_count: number }
  maintenance?: KnowledgeBankMaintenance
}

function formatFallbackCheckBack(minutes: number): { message: string; checkBackAt: string } {
  const checkBack = new Date(Date.now() + minutes * 60_000)
  const formatted = checkBack.toLocaleString(undefined, {
    hour: 'numeric',
    minute: '2-digit',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
  return {
    message: `The application knowledge bank is being updated. Please check back around ${formatted}.`,
    checkBackAt: checkBack.toISOString(),
  }
}

// ── Chat ─────────────────────────────────────────────────────────────────────

export async function* streamChat(
  query: string,
  sessionId: string | undefined,
  haikuOnly = false,
  messageId?: string,
): AsyncGenerator<SSEEvent> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({
      query,
      session_id: sessionId ?? null,
      haiku_only: haikuOnly,
      message_id: messageId,
    }),
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    if (res.status === 503) {
      if (body.detail === 'API_DISABLED') {
        const err = new Error('API_DISABLED')
        ;(err as any).status = 503
        throw err
      }
      if (body.detail === 'KNOWLEDGE_BANK_UPDATING') {
        const err = new Error('KNOWLEDGE_BANK_UPDATING')
        ;(err as any).status = 503
        ;(err as any).maintenance = body.maintenance
        throw err
      }
      const err = new Error(`Service unavailable: ${res.status}`)
      ;(err as any).status = 503
      throw err
    }
    if (res.status === 403) {
      const err = new Error(body.detail ?? 'Access denied')
      ;(err as any).status = 403
      throw err
    }
    if (res.status === 429) {
      if (body.detail === 'MONTHLY_QUOTA_EXCEEDED') {
        const err = new Error('MONTHLY_QUOTA_EXCEEDED')
        ;(err as any).status = 429
        throw err
      }
      const err = new Error(body.detail?.message ?? 'Daily limit reached')
      ;(err as any).status = 429
      ;(err as any).detail = body.detail ?? body
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
  comment = '',
): Promise<void> {
  await fetch(`${API_BASE}/api/chat/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ message_id: messageId, session_id: sessionId, rating, query, comment }),
  })
}

export interface LandingBySlug {
  slug: string
  query: string
  answer: string
  citations: Citation[]
  evidence: RetrievalEvidence | null
  created_at: string
}

/** Public, unauthenticated fetch for a single recorded query's SEO landing page. */
export async function getLandingBySlug(slug: string): Promise<LandingBySlug | null> {
  const res = await fetch(`${API_BASE}/api/landing/${encodeURIComponent(slug)}`)
  if (!res.ok) return null
  return res.json()
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
export const getAdminAnalytics = (token: string) =>
  fetch(`${API_BASE}/api/admin/analytics`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: 'no-store',
  }).then((res) => {
    if (!res.ok) throw new Error(`Admin request failed: ${res.status}`)
    return res.json()
  })

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
  monthly_query_limit: number
  monthly_queries_used: number
  quota_reset_date: string | null
}

export interface UserQuota {
  monthly_limit: number
  monthly_used: number
  monthly_remaining: number
  reset_date: string | null
  is_new_user: boolean
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
  feedback_comment?: string | null
}

export interface Pagination {
  page: number
  page_size: number
  total_records: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
}

export interface PaginatedQueryLogs {
  data: QueryLog[]
  pagination: Pagination
}

export interface PaginatedGoogleUsers {
  data: GoogleUser[]
  pagination: Pagination
}

const USER_SORT_KEYS = new Set(['last_seen', 'first_seen', 'total_queries', 'name', 'email'])

/** Accept legacy flat-array responses until backend pagination is deployed everywhere. */
export function normalizePaginatedGoogleUsers(
  raw: unknown,
  params: { page: number; pageSize: number; sortBy: string; sortOrder: string; search: string },
): PaginatedGoogleUsers {
  if (
    raw
    && typeof raw === 'object'
    && !Array.isArray(raw)
    && 'data' in raw
    && 'pagination' in raw
  ) {
    return raw as PaginatedGoogleUsers
  }

  const emptyPagination = (pageSize: number): Pagination => ({
    page: 1,
    page_size: pageSize,
    total_records: 0,
    total_pages: 1,
    has_next: false,
    has_prev: false,
  })

  if (!Array.isArray(raw)) {
    return { data: [], pagination: emptyPagination(params.pageSize) }
  }

  const sortBy = USER_SORT_KEYS.has(params.sortBy) ? params.sortBy : 'last_seen'
  const asc = params.sortOrder.toLowerCase() === 'asc'
  const term = params.search.trim().toLowerCase()

  let items = raw as GoogleUser[]
  if (term) {
    items = items.filter(
      (u) =>
        (u.name ?? '').toLowerCase().includes(term)
        || (u.email ?? '').toLowerCase().includes(term),
    )
  }

  items = [...items].sort((a, b) => {
    const av = a[sortBy as keyof GoogleUser]
    const bv = b[sortBy as keyof GoogleUser]
    if (av == null && bv == null) return 0
    if (av == null) return 1
    if (bv == null) return -1
    if (typeof av === 'number' && typeof bv === 'number') {
      return asc ? av - bv : bv - av
    }
    const cmp = String(av).localeCompare(String(bv), undefined, { sensitivity: 'base' })
    return asc ? cmp : -cmp
  })

  const total = items.length
  const totalPages = Math.max(1, Math.ceil(total / params.pageSize))
  const page = Math.min(Math.max(1, params.page), totalPages)
  const start = (page - 1) * params.pageSize

  return {
    data: items.slice(start, start + params.pageSize),
    pagination: {
      page,
      page_size: params.pageSize,
      total_records: total,
      total_pages: totalPages,
      has_next: page < totalPages,
      has_prev: page > 1,
    },
  }
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

export const listGoogleUsers = async (
  token: string,
  params: {
    page?: number
    pageSize?: number
    sortBy?: string
    sortOrder?: string
    search?: string
  } = {},
): Promise<PaginatedGoogleUsers> => {
  const { page = 1, pageSize = 25, sortBy = 'last_seen', sortOrder = 'desc', search = '' } = params
  const q = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
    sort_by: sortBy,
    sort_order: sortOrder,
  })
  if (search.trim()) q.set('search', search.trim())
  const raw = await adminFetch(`/api/admin/users?${q}`, token)
  return normalizePaginatedGoogleUsers(raw, { page, pageSize, sortBy, sortOrder, search })
}

export const updateGoogleUser = (
  token: string,
  userId: string,
  payload: { is_admin?: boolean; is_disabled?: boolean },
): Promise<GoogleUser> =>
  adminMutate(`/api/admin/users/${encodeURIComponent(userId)}`, token, 'PATCH', payload)

export const getGoogleUserSummary = (token: string): Promise<GoogleUserSummary> =>
  adminFetch('/api/admin/users/summary', token)

export const getQueryLogs = (
  token: string,
  params: { page?: number; pageSize?: number; sortBy?: string; sortOrder?: string } = {},
): Promise<PaginatedQueryLogs> => {
  const { page = 1, pageSize = 25, sortBy = 'created_at', sortOrder = 'desc' } = params
  return adminFetch(
    `/api/admin/query-logs?page=${page}&page_size=${pageSize}&sort_by=${sortBy}&sort_order=${sortOrder}`,
    token,
  )
}

export async function exportQueriesExcel(
  token: string,
  dateFrom?: string,
  dateTo?: string,
): Promise<void> {
  const p = new URLSearchParams()
  if (dateFrom) p.set('date_from', dateFrom)
  if (dateTo) p.set('date_to', dateTo)
  const qs = p.toString() ? `?${p}` : ''
  const res = await fetch(`${API_BASE}/api/admin/export/queries/excel${qs}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error(`Export failed: ${res.status}`)
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  const cd = res.headers.get('Content-Disposition') ?? ''
  const m = cd.match(/filename=([^;]+)/)
  a.download = m ? m[1] : `rovr-queries-${new Date().toISOString().slice(0, 10)}.xlsx`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export async function exportUsersExcel(
  token: string,
  search?: string,
): Promise<void> {
  const q = search?.trim() ? `?search=${encodeURIComponent(search.trim())}` : ''
  const res = await fetch(`${API_BASE}/api/admin/export/users/excel${q}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error(`Export failed: ${res.status}`)
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  const cd = res.headers.get('Content-Disposition') ?? ''
  const m = cd.match(/filename=([^;]+)/)
  a.download = m ? m[1] : `rovr-users-${new Date().toISOString().slice(0, 10)}.xlsx`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

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

export const setUserMonthlyLimit = (token: string, userId: string, limit: number): Promise<GoogleUser> =>
  adminMutate(`/api/admin/users/${encodeURIComponent(userId)}/monthly-limit`, token, 'PATCH', { monthly_query_limit: limit })

export const getDefaultMonthlyLimit = (token: string): Promise<{ default_monthly_limit: number }> =>
  adminFetch('/api/admin/settings/default-monthly-limit', token)

export const setDefaultMonthlyLimit = (token: string, limit: number): Promise<{ default_monthly_limit: number }> =>
  adminMutate('/api/admin/settings/default-monthly-limit', token, 'PATCH', { default_monthly_limit: limit })

export async function getUserQuota(): Promise<UserQuota> {
  try {
    const res = await fetch(`${API_BASE}/api/auth/quota`, { headers: authHeaders() })
    if (!res.ok) return { monthly_limit: 999999, monthly_used: 0, monthly_remaining: 999999, reset_date: null, is_new_user: false }
    return res.json()
  } catch {
    return { monthly_limit: 999999, monthly_used: 0, monthly_remaining: 999999, reset_date: null, is_new_user: false }
  }
}

export interface LandingQuestion {
  text: string
  solution: string
  times_asked: number
}

export interface LandingQuestionsResponse {
  questions: LandingQuestion[]
  by_solution: Record<string, LandingQuestion[]>
  total: number
  source: 'postgres' | 'fallback'
  all_tab_per_solution?: number
  max_per_solution?: number
}

export async function fetchLandingQuestions(): Promise<LandingQuestionsResponse> {
  const res = await fetch(`${API_BASE}/api/chat/landing-questions`, {
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error(`Landing questions failed: ${res.status}`)
  return res.json()
}

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

/** Returns true when the kill switch is active (API disabled by admin). */
export async function isApiDisabled(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/ping`, { headers: authHeaders() })
    if (res.status === 503) {
      const body = await res.json().catch(() => ({}))
      return body?.detail === 'API_DISABLED'
    }
    return false
  } catch {
    return false
  }
}

/** Poll backend health — used for knowledge bank maintenance banner. */
export async function getHealth(): Promise<HealthResponse | null> {
  try {
    const res = await fetch(`${API_BASE}/api/health`)
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export interface MaintenanceStatus {
  updating: boolean
  message: string | null
  checkBackAt: string | null
}

/** Detect knowledge-bank maintenance from /api/health or /api/ping 503 payload. */
export async function fetchMaintenanceStatus(): Promise<MaintenanceStatus> {
  const health = await getHealth()
  if (health?.status === 'updating' && health.maintenance) {
    return {
      updating: true,
      message: health.maintenance.message,
      checkBackAt: health.maintenance.check_back_at,
    }
  }
  if (health?.status === 'ok') {
    return { updating: false, message: null, checkBackAt: null }
  }

  try {
    const res = await fetch(`${API_BASE}/api/ping`)
    if (res.status === 503) {
      const body = await res.json().catch(() => ({}))
      if (body.detail === 'KNOWLEDGE_BANK_UPDATING' && body.maintenance) {
        return {
          updating: true,
          message: body.maintenance.message,
          checkBackAt: body.maintenance.check_back_at,
        }
      }
    }
  } catch {
    // Backend unreachable during redeploy — treat as maintenance.
  }

  const fallback = getFallbackMaintenanceMessage()
  return {
    updating: true,
    message: fallback.message,
    checkBackAt: fallback.check_back_at,
  }
}

/** Fallback maintenance message when health is unreachable during redeploy. */
export function getFallbackMaintenanceMessage(etaMinutes = 4): KnowledgeBankMaintenance {
  const { message, checkBackAt } = formatFallbackCheckBack(etaMinutes)
  return {
    active: true,
    message,
    check_back_at: checkBackAt,
    eta_minutes: etaMinutes,
  }
}
