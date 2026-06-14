/**
 * Rovr Analytics — event helper functions.
 *
 * Each function maps to exactly one event schema entry.
 * These are the ONLY functions the rest of the app should import from analytics.
 *
 * All query text is sanitised (email-stripped, 60-char truncated) before push.
 */

import {
  pushEvent,
  makeBase,
  sanitizeQuery,
  newAnalyticsSession,
  clearAnalyticsSession,
  getSessionDurationMs,
} from './dataLayer'

// ─── Page view ────────────────────────────────────────────────────────────────

/**
 * Fire a page_view event. Called by usePageView on route change.
 *
 * @example
 *   trackPageView('rovr:chat')
 */
export function trackPageView(pageName: string): void {
  pushEvent({
    ...makeBase(),
    event: 'page_view',
    pageName,
    pageURL: typeof window !== 'undefined' ? window.location.href : '',
    referrer: typeof document !== 'undefined' ? document.referrer : '',
  })
}

// ─── Session ──────────────────────────────────────────────────────────────────

/**
 * Fire chatbot:session_start and generate a new analytics session UUID.
 * Call when the user starts a new chat or arrives on the page for the first time.
 *
 * @example
 *   trackSessionStart('new_chat_button')
 */
export function trackSessionStart(trigger: 'new_chat_button' | 'page_load'): void {
  newAnalyticsSession()
  pushEvent({
    ...makeBase(),
    event: 'chatbot:session_start',
    trigger,
  })
}

/**
 * Fire chatbot:session_end and clear the analytics session from sessionStorage.
 * Call on window beforeunload.
 *
 * @example
 *   trackSessionEnd(5, Date.now() - sessionStartMs)
 */
export function trackSessionEnd(totalTurns: number, sessionDurationMs?: number): void {
  pushEvent({
    ...makeBase(),
    event: 'chatbot:session_end',
    totalTurns,
    sessionDurationMs: sessionDurationMs ?? getSessionDurationMs(),
  })
  clearAnalyticsSession()
}

// ─── Query ────────────────────────────────────────────────────────────────────

/**
 * Fire chatbot:query_sent for every query (turn 1 = first in session, 2+ = follow-up).
 * Model routing may not be known at send time; pass 'unknown' and Adobe Tags
 * can enrich it from the data layer state when the done event arrives.
 *
 * @example
 *   trackQuerySent('How do I create a segment?', 1, 'unknown', 'Analytics')
 */
export function trackQuerySent(
  queryText: string,
  turnNumber: number,
  modelRouting: 'haiku' | 'sonnet' | 'unknown',
  queryCategory: string,
): void {
  pushEvent({
    ...makeBase(),
    event: 'chatbot:query_sent',
    queryText: sanitizeQuery(queryText),
    turnNumber,
    modelRouting,
    queryCategory,
  })
}

/**
 * Fire chatbot:followup_query for turns >= 2 (in addition to chatbot:query_sent).
 * Lets Adobe Tags isolate follow-up engagement separately from opening queries.
 *
 * @example
 *   trackFollowupQuery('What about CJA?', 3)
 */
export function trackFollowupQuery(queryText: string, turnNumber: number): void {
  if (turnNumber < 2) return
  const base = makeBase()
  pushEvent({
    ...base,
    event: 'chatbot:followup_query',
    queryText: sanitizeQuery(queryText),
    turnNumber,
    sessionId: base.sessionId,
  })
}

// ─── Feedback ─────────────────────────────────────────────────────────────────

/**
 * Fire chatbot:feedback_positive (thumbs up).
 *
 * @example
 *   trackFeedbackPositive('How do I create a segment in Adobe Analytics?', 1)
 */
export function trackFeedbackPositive(queryText: string, turnNumber: number): void {
  pushEvent({
    ...makeBase(),
    event: 'chatbot:feedback_positive',
    queryText: sanitizeQuery(queryText),
    turnNumber,
  })
}

/**
 * Fire chatbot:feedback_negative (thumbs down).
 *
 * @example
 *   trackFeedbackNegative('How do I create a segment?', 1, 'Wrong product')
 */
export function trackFeedbackNegative(
  queryText: string,
  turnNumber: number,
  feedbackReason?: string,
): void {
  pushEvent({
    ...makeBase(),
    event: 'chatbot:feedback_negative',
    queryText: sanitizeQuery(queryText),
    turnNumber,
    ...(feedbackReason !== undefined
      ? { feedbackReason: sanitizeQuery(feedbackReason) }
      : {}),
  })
}

// ─── Citation click ───────────────────────────────────────────────────────────

/**
 * Fire chatbot:citation_click when a user clicks a source document link.
 *
 * @example
 *   trackCitationClick('https://experienceleague.adobe.com/...', 'Create segments', 2)
 */
export function trackCitationClick(
  citationUrl: string,
  citationTitle: string,
  turnNumber: number,
): void {
  pushEvent({
    ...makeBase(),
    event: 'chatbot:citation_click',
    citationUrl,
    citationTitle,
    turnNumber,
  })
}

// ─── No answer ────────────────────────────────────────────────────────────────

/**
 * Fire chatbot:no_answer when the RAG pipeline cannot answer the query.
 * This is the gap-analysis dimension — use it to discover documentation coverage gaps.
 *
 * @example
 *   trackNoAnswer('How do I migrate RTCDP to v2?', 3, 'no_retrieval')
 */
export function trackNoAnswer(
  queryText: string,
  turnNumber: number,
  failureReason: 'no_retrieval' | 'low_confidence' | 'error',
): void {
  pushEvent({
    ...makeBase(),
    event: 'chatbot:no_answer',
    queryText: sanitizeQuery(queryText),
    turnNumber,
    failureReason,
  })
}
