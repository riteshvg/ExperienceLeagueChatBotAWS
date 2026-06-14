# Rovr Analytics — `@/analytics`

Rovr uses the **Adobe Client Data Layer** pattern (`window.adobeDataLayer`) to publish typed events that Adobe Tags (Launch) can consume via data layer rules.

---

## Architecture

```
components / stores
        │
        ▼
  @/analytics          ← public API (import everything from here)
  ├── index.ts         (re-exports)
  ├── events.ts        (named helper functions: trackXxx)
  ├── dataLayer.ts     (primitives: pushEvent, session helpers, hashing, types)
  └── usePageView.ts   (React hook: fires page_view on route change)
```

**Rule:** components and stores always import from `@/analytics`, never from internal submodules.

---

## Event Reference

| Event name | Helper | Fired when |
|---|---|---|
| `page_view` | `trackPageView(pageName)` | Route changes (`usePageView` hook) |
| `chatbot:session_start` | `trackSessionStart(trigger)` | New chat started or page first loaded |
| `chatbot:session_end` | `trackSessionEnd(totalTurns)` | Tab closed (`beforeunload`) or "New chat" clicked |
| `chatbot:query_sent` | `trackQuerySent(query, turn, routing, category)` | User sends any message |
| `chatbot:followup_query` | `trackFollowupQuery(query, turn)` | Turn ≥ 2 within a session |
| `chatbot:feedback_positive` | `trackFeedbackPositive(query, turn)` | Thumbs-up clicked |
| `chatbot:feedback_negative` | `trackFeedbackNegative(query, turn, reason?)` | Thumbs-down clicked |
| `chatbot:citation_click` | `trackCitationClick(url, title, turn)` | Citation card clicked |
| `chatbot:no_answer` | `trackNoAnswer(query, turn, reason)` | `model: 'none'` or SSE error |

---

## Shared Payload (`BaseEvent`)

Every event includes:

```ts
{
  event: string          // event name
  timestamp: string      // ISO-8601 UTC
  sessionId: string      // sessionStorage — new UUID per tab session
  userId: string         // SHA-256 hex of the Google sub; "anonymous" if not logged in
  appVersion: string     // import.meta.env.VITE_APP_VERSION ?? 'dev'
}
```

`query` fields are run through `sanitizeQuery()` which strips email addresses and truncates to 60 chars.

---

## Adobe Tags Setup

1. Create a **Data Layer Rule** triggered on `chatbot:query_sent` (and each other event you care about).
2. In the condition, set **Data Layer Event** = the event name.
3. Map `event.sessionId`, `event.userId`, `event.queryText`, etc. to Analytics variables via data elements.
4. Use **"Push Event" / "Computed State"** actions to read `window.adobeDataLayer` state.

---

## Debug Mode

Open the browser console and run:

```js
localStorage.setItem('rovr_dl_debug', 'true')
```

Then reload — every `pushEvent()` call will `console.log` the full payload.  
To disable: `localStorage.removeItem('rovr_dl_debug')`.

---

## Adding a New Event

1. Add the event type to the discriminated union in `dataLayer.ts`:
   ```ts
   export interface MyNewEvent extends BaseEvent {
     event: 'chatbot:my_new_event'
     someField: string
   }
   export type RovrEvent = ... | MyNewEvent
   ```

2. Add a helper function in `events.ts`:
   ```ts
   export function trackMyNewEvent(someField: string): void {
     pushEvent({ ...makeBase(), event: 'chatbot:my_new_event', someField })
   }
   ```

3. Re-export it from `index.ts`.

4. Call it from the relevant component/store: `import { trackMyNewEvent } from '@/analytics'`.
