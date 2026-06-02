/**
 * Typed API client for the FastAPI backend.
 */
// In production, VITE_API_URL points to the Railway backend.
// In development, empty string → Vite proxy handles /api/* → localhost:8000
const API_BASE = import.meta.env.VITE_API_URL ?? ''

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
  | { type: 'done'; model: string; session_id: string }
  | { type: 'error'; message: string }

// ── Chat ─────────────────────────────────────────────────────────────────────

export async function* streamChat(
  query: string,
  sessionId: string,
  haikuOnly = false,
): AsyncGenerator<SSEEvent> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, session_id: sessionId, haiku_only: haikuOnly }),
  })

  if (!res.ok) {
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
      headers: { 'Content-Type': 'application/json' },
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
    headers: { 'Content-Type': 'application/json' },
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
