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
  trackQuerySent,
  trackFollowupQuery,
  trackFeedbackPositive,
  trackFeedbackNegative,
  trackCitationClick,
  trackNoAnswer,
} from './events'

// React hook
export { usePageView } from './usePageView'

// Utilities needed outside the analytics module
export { hashUserId, setHashedUserId, sanitizeQuery } from './dataLayer'

// Types — re-exported for components that need to reference them
export type {
  RovrEvent,
  PageViewEvent,
  SessionStartEvent,
  QuerySentEvent,
  FollowupQueryEvent,
  SessionEndEvent,
  FeedbackPositiveEvent,
  FeedbackNegativeEvent,
  CitationClickEvent,
  NoAnswerEvent,
} from './dataLayer'
