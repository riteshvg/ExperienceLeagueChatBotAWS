/**
 * Rovr Analytics — public API.
 *
 * Import everything the app needs from here:
 *
 *   import { trackQuerySent, trackSessionStart, usePageView } from '@/analytics'
 *
 * Internal helpers (pushEvent, makeBase, etc.) live in dataLayer.ts and are
 * not part of the public surface — import them directly only from within
 * the analytics/ directory itself.
 */

// Event helpers
export {
  trackPageView,
  trackSessionStart,
  trackSessionEnd,
  trackQuestionAsked,
  trackQuerySent,
  trackFollowupQuery,
  trackResponseReceived,
  trackSuggestedPromptClick,
  trackFeedbackPositive,
  trackFeedbackNegative,
  trackCitationClick,
  trackImageOpen,
  trackImageCarouselNavigate,
  trackNoAnswer,
  trackTermsAccepted,
} from './events'

// React hook
export { usePageView } from './usePageView'

// Utilities needed outside the analytics module
export { hashUserId, hasAnalyticsSession, setHashedUserId, sanitizeQuery } from './dataLayer'

// Types — re-exported for components that need to reference them
export type {
  RovrEvent,
  PageViewEvent,
  SessionStartEvent,
  QuestionAskedEvent,
  QuerySentEvent,
  FollowupQueryEvent,
  ResponseReceivedEvent,
  SuggestedPromptClickEvent,
  SessionEndEvent,
  FeedbackPositiveEvent,
  FeedbackNegativeEvent,
  CitationClickEvent,
  ImageOpenEvent,
  ImageCarouselNavigateEvent,
  NoAnswerEvent,
} from './dataLayer'
