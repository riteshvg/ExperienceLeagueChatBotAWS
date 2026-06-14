/**
 * Rovr Adobe Analytics Data Layer
 *
 * Wraps window.adobeDataLayer (Adobe Client Data Layer standard array).
 * All operations are wrapped in try/catch — this module never throws.
 *
 * Adobe Tags integration: define rules that listen for events on
 * window.adobeDataLayer using the "data pushed" trigger type.
 */

// ─── Global window augmentation ───────────────────────────────────────────────

declare global {
  interface Window {
    /** Adobe Client Data Layer — standard push-array interface. */
    adobeDataLayer: RovrEvent[]
  }
}

// ─── Debug flag ───────────────────────────────────────────────────────────────

function isDebug(): boolean {
  try {
    return localStorage.getItem('rovr_dl_debug') === 'true'
  } catch {
    return false
  }
}

// ─── Analytics session ID ─────────────────────────────────────────────────────

/** sessionStorage key used for the analytics session UUID. */
export const ROVR_SESSION_KEY = 'rovr_session_id'

/** Start time key — used to compute sessionDurationMs on session_end. */
const ROVR_SESSION_START_KEY = 'rovr_session_start_ms'

function getSessionId(): string {
  try {
    return sessionStorage.getItem(ROVR_SESSION_KEY) ?? ''
  } catch {
    return ''
  }
}

/**
 * Generate a new UUIDv4, persist it to sessionStorage, and return it.
 * Call this inside trackSessionStart() to begin a new analytics session.
 */
export function newAnalyticsSession(): string {
  const id = crypto.randomUUID()
  try {
    sessionStorage.setItem(ROVR_SESSION_KEY, id)
    sessionStorage.setItem(ROVR_SESSION_START_KEY, String(Date.now()))
  } catch { /* private browsing / SSR */ }
  return id
}

/**
 * Return elapsed milliseconds since the analytics session started.
 * Returns 0 if no start time is found.
 */
export function getSessionDurationMs(): number {
  try {
    const start = sessionStorage.getItem(ROVR_SESSION_START_KEY)
    return start ? Date.now() - Number(start) : 0
  } catch {
    return 0
  }
}

/**
 * Clear the analytics session from sessionStorage.
 * Call this inside trackSessionEnd().
 */
export function clearAnalyticsSession(): void {
  try {
    sessionStorage.removeItem(ROVR_SESSION_KEY)
    sessionStorage.removeItem(ROVR_SESSION_START_KEY)
  } catch { /* ignore */ }
}

// ─── userId hashing ───────────────────────────────────────────────────────────

let _cachedHashedUserId = 'anonymous'

/**
 * Hash a user identifier with SHA-256 and return it as a hex string.
 *
 * @example
 *   const hashed = await hashUserId(session.userId)
 *   setHashedUserId(hashed)
 */
export async function hashUserId(sub: string): Promise<string> {
  try {
    const data = new TextEncoder().encode(sub)
    const buf = await crypto.subtle.digest('SHA-256', data)
    return Array.from(new Uint8Array(buf))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('')
  } catch {
    return 'anonymous'
  }
}

/**
 * Cache a pre-hashed userId so all subsequent pushEvent() calls include it.
 * Call this once after successful authentication.
 */
export function setHashedUserId(hashed: string): void {
  _cachedHashedUserId = hashed
}

// ─── Query sanitisation ───────────────────────────────────────────────────────

const EMAIL_RE = /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi
const MAX_QUERY_LEN = 60

/**
 * Strip email addresses and truncate to 60 chars.
 * Must be applied to all query text before it reaches the data layer.
 *
 * @example
 *   sanitizeQuery('email me at foo@bar.com please') // 'email me at [email] please'
 */
export function sanitizeQuery(text: string): string {
  return text.replace(EMAIL_RE, '[email]').slice(0, MAX_QUERY_LEN)
}

// ─── Event type definitions ───────────────────────────────────────────────────

interface BaseEvent {
  readonly event: string
  readonly timestamp: string
  readonly sessionId: string
  readonly userId: string
  readonly appName: 'rovr'
}

export interface PageViewEvent extends BaseEvent {
  readonly event: 'page_view'
  readonly pageName: string
  readonly pageURL: string
  readonly referrer: string
}

export interface SessionStartEvent extends BaseEvent {
  readonly event: 'chatbot:session_start'
  readonly trigger: 'new_chat_button' | 'page_load'
}

export interface QuerySentEvent extends BaseEvent {
  readonly event: 'chatbot:query_sent'
  readonly queryText: string
  readonly turnNumber: number
  readonly modelRouting: 'haiku' | 'sonnet' | 'unknown'
  readonly queryCategory: string
}

export interface FollowupQueryEvent extends BaseEvent {
  readonly event: 'chatbot:followup_query'
  readonly queryText: string
  readonly turnNumber: number
  readonly sessionId: string
}

export interface SessionEndEvent extends BaseEvent {
  readonly event: 'chatbot:session_end'
  readonly totalTurns: number
  readonly sessionDurationMs: number
}

export interface FeedbackPositiveEvent extends BaseEvent {
  readonly event: 'chatbot:feedback_positive'
  readonly queryText: string
  readonly turnNumber: number
}

export interface FeedbackNegativeEvent extends BaseEvent {
  readonly event: 'chatbot:feedback_negative'
  readonly queryText: string
  readonly turnNumber: number
  readonly feedbackReason?: string
}

export interface CitationClickEvent extends BaseEvent {
  readonly event: 'chatbot:citation_click'
  readonly citationUrl: string
  readonly citationTitle: string
  readonly turnNumber: number
}

export interface NoAnswerEvent extends BaseEvent {
  readonly event: 'chatbot:no_answer'
  readonly queryText: string
  readonly turnNumber: number
  readonly failureReason: 'no_retrieval' | 'low_confidence' | 'error'
}

/** Discriminated union of all Rovr data layer events. */
export type RovrEvent =
  | PageViewEvent
  | SessionStartEvent
  | QuerySentEvent
  | FollowupQueryEvent
  | SessionEndEvent
  | FeedbackPositiveEvent
  | FeedbackNegativeEvent
  | CitationClickEvent
  | NoAnswerEvent

// ─── Internal base constructor ────────────────────────────────────────────────

/** Build the common base fields shared by every event. */
export function makeBase(): Omit<BaseEvent, 'event'> {
  return {
    timestamp: new Date().toISOString(),
    sessionId: getSessionId(),
    userId: _cachedHashedUserId,
    appName: 'rovr',
  }
}

// ─── Push ─────────────────────────────────────────────────────────────────────

/**
 * Push a typed event onto window.adobeDataLayer.
 *
 * - Initialises the array if absent
 * - Logs to console when localStorage.rovr_dl_debug === "true"
 * - Never throws; failures are console.warn'd
 *
 * @example
 *   pushEvent({ ...makeBase(), event: 'page_view', pageName: 'rovr:chat', ... })
 */
export function pushEvent(event: RovrEvent): void {
  try {
    if (typeof window === 'undefined') return
    window.adobeDataLayer = window.adobeDataLayer ?? []
    if (isDebug()) {
      // eslint-disable-next-line no-console
      console.log('[Rovr DL]', event.event, event)
    }
    window.adobeDataLayer.push(event)
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn('[Rovr DL] pushEvent failed:', err)
  }
}
