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
export function trackSessionStart(
  trigger: 'first_query' | 'resume_chat' | 'new_chat_button' | 'page_load',
): void {
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
 * Fire chatbot:question_asked when the user asks a question.
 * This is the business-facing question event; chatbot:query_sent remains the
 * lower-level API dispatch event.
 *
 * @example
 *   trackQuestionAsked('How do I create a segment?', 1, 'Analytics')
 */
export function trackQuestionAsked(
  queryText: string,
  turnNumber: number,
  queryCategory: string,
  promptSource?: 'center_popular_questions' | 'sidebar_prompt_library' | 'followup_question',
): void {
  pushEvent({
    ...makeBase(),
    event: 'chatbot:question_asked',
    queryText: sanitizeQuery(queryText),
    turnNumber,
    queryCategory,
    ...(promptSource !== undefined ? { promptSource } : {}),
  })
}

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
  promptSource?: 'center_popular_questions' | 'sidebar_prompt_library' | 'followup_question',
): void {
  pushEvent({
    ...makeBase(),
    event: 'chatbot:query_sent',
    queryText: sanitizeQuery(queryText),
    turnNumber,
    modelRouting,
    queryCategory,
    ...(promptSource !== undefined ? { promptSource } : {}),
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

/**
 * Fire chatbot:response_received when the backend completes a successful answer.
 * This is the terminal success event for a question.
 *
 * @example
 *   trackResponseReceived('How do I create a segment?', 1, 'sonnet', 4)
 */
export function trackResponseReceived(
  queryText: string,
  turnNumber: number,
  modelRouting: string,
  citationCount: number,
): void {
  pushEvent({
    ...makeBase(),
    event: 'chatbot:response_received',
    queryText: sanitizeQuery(queryText),
    turnNumber,
    modelRouting,
    citationCount,
  })
}

export function trackSuggestedPromptClick({
  promptText,
  promptSource,
  promptTitle,
  promptCategory,
  timesAsked,
}: {
  promptText: string
  promptSource: 'center_popular_questions' | 'sidebar_prompt_library' | 'followup_question'
  promptTitle?: string
  promptCategory?: string
  timesAsked?: number
}): void {
  pushEvent({
    ...makeBase(),
    event: 'chatbot:suggested_prompt_click',
    promptText: sanitizeQuery(promptText),
    promptSource,
    ...(promptTitle !== undefined ? { promptTitle: sanitizeQuery(promptTitle) } : {}),
    ...(promptCategory !== undefined ? { promptCategory } : {}),
    ...(timesAsked !== undefined ? { timesAsked } : {}),
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

// ─── Image gallery ────────────────────────────────────────────────────────────

export function trackImageOpen({
  imageUrl,
  imageAlt,
  imageIndex,
  imageCount,
  turnNumber,
  messageId,
}: {
  imageUrl: string
  imageAlt: string
  imageIndex: number
  imageCount: number
  turnNumber: number
  messageId: string
}): void {
  pushEvent({
    ...makeBase(),
    event: 'chatbot:image_open',
    imageUrl,
    imageAlt: sanitizeQuery(imageAlt),
    imageIndex,
    imageCount,
    turnNumber,
    messageId,
  })
}

export function trackImageCarouselNavigate({
  imageUrl,
  imageAlt,
  imageIndex,
  previousImageIndex,
  imageCount,
  direction,
  turnNumber,
  messageId,
}: {
  imageUrl: string
  imageAlt: string
  imageIndex: number
  previousImageIndex: number
  imageCount: number
  direction: 'previous' | 'next' | 'jump'
  turnNumber: number
  messageId: string
}): void {
  pushEvent({
    ...makeBase(),
    event: 'chatbot:image_carousel_navigate',
    imageUrl,
    imageAlt: sanitizeQuery(imageAlt),
    imageIndex,
    previousImageIndex,
    imageCount,
    direction,
    turnNumber,
    messageId,
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
// ─── Terms acceptance ─────────────────────────────────────────────────────────

/**
 * Fire chatbot:terms_accepted when the user checks the checkbox and clicks
 * "I agree" on the first-sign-in terms modal.
 */
export function trackTermsAccepted(): void {
  pushEvent({
    ...makeBase(),
    event: 'chatbot:terms_accepted',
  })
}

// ─── No answer ────────────────────────────────────────────────────────────────

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
