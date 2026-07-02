import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { streamChat, clearHistory, getFollowUps, submitFeedback, type Message, type Citation, type RetrievalEvidence, type ChatStage } from '@/lib/api'
import {
  hasAnalyticsSession,
  trackFollowupQuery,
  trackResponseReceived,
  trackSessionStart,
  trackSessionEnd,
  trackFeedbackPositive,
  trackFeedbackNegative,
  trackNoAnswer,
} from '@/analytics'


function makeId() {
  return Math.random().toString(36).slice(2)
}

// Watchdog: if a pipeline stage runs this long with no transition and no tokens,
// the status copy switches to a generic "still working" message.
const STAGE_STALL_MS = 8000

// Minimum time each real pipeline stage stays on screen before the next one can
// replace it. Retrieval can finish in milliseconds locally, but "Checking Adobe
// documentation" needs to actually be readable — that disclosure is what makes
// the pipeline feel trustworthy, so it must never flash by unseen.
const MIN_STAGE_DISPLAY_MS = 800

function deriveTitle(messages: Message[]): string {
  const first = messages.find((m) => m.role === 'user')
  if (!first) return 'New chat'
  return first.content.slice(0, 45) + (first.content.length > 45 ? '…' : '')
}

export interface ChatSession {
  id: string
  title: string
  messages: Message[]
  createdAt: number
}

interface ChatState {
  sessions: Record<string, ChatSession>
  activeSessionId: string
  isStreaming: boolean
  currentStage: ChatStage | null
  stageStalled: boolean
  error: string | null
  accessDenied: boolean
  rateLimited: boolean
  rateLimitMessage: string
  apiDisabled: boolean
  knowledgeBankUpdating: boolean
  knowledgeBankMessage: string | null
  knowledgeBankCheckBackAt: string | null
  monthlyExhausted: boolean
  queriesUsed: number
  queriesRemaining: number | null
  queriesLimit: number

  feedbackToast: boolean
  sendMessage: (query: string) => Promise<void>
  _streamQuery: (query: string) => Promise<void>
  setFeedback: (messageId: string, rating: 1 | -1, query: string, comment?: string) => void
  dismissFeedbackToast: () => void
  startNewChat: () => void
  switchSession: (id: string) => void
  deleteSession: (id: string) => void
  clearError: () => void
  setApiDisabled: (disabled: boolean) => void
  setKnowledgeBankMaintenance: (
    updating: boolean,
    message?: string | null,
    checkBackAt?: string | null,
  ) => void
  setUsage: (used: number, remaining: number, limit: number) => void
}

function createSession(): ChatSession {
  return { id: makeId(), title: 'New chat', messages: [], createdAt: Date.now() }
}

// Helper: update only the active session's messages
function patchActiveMessages(
  sessions: Record<string, ChatSession>,
  activeId: string,
  updater: (msgs: Message[]) => Message[],
): Record<string, ChatSession> {
  const session = sessions[activeId]
  if (!session) return sessions
  const messages = updater(session.messages)
  return {
    ...sessions,
    [activeId]: { ...session, messages, title: deriveTitle(messages) },
  }
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => {
      const initial = createSession()
      return {
        sessions: { [initial.id]: initial },
        activeSessionId: initial.id,
        isStreaming: false,
        currentStage: null,
        stageStalled: false,
        error: null,
        accessDenied: false,
        rateLimited: false,
        rateLimitMessage: '',
        apiDisabled: false,
        knowledgeBankUpdating: false,
        knowledgeBankMessage: null,
        knowledgeBankCheckBackAt: null,
        monthlyExhausted: false,
        queriesUsed: 0,
        queriesRemaining: null,
        queriesLimit: 20,
        feedbackToast: false,

        clearError: () => set({ error: null }),
        dismissFeedbackToast: () => set({ feedbackToast: false }),

        setApiDisabled: (disabled) => set({ apiDisabled: disabled }),

        setKnowledgeBankMaintenance: (updating, message = null, checkBackAt = null) =>
          set({
            knowledgeBankUpdating: updating,
            knowledgeBankMessage: message,
            knowledgeBankCheckBackAt: checkBackAt,
          }),

        setUsage: (used, remaining, limit) => set({ queriesUsed: used, queriesRemaining: remaining, queriesLimit: limit }),

        setFeedback: (messageId, rating, _query, comment = '') => {
          const { activeSessionId, sessions } = get()
          // Find the user message that preceded this assistant message
          const msgs = sessions[activeSessionId]?.messages ?? []
          const idx = msgs.findIndex((m) => m.id === messageId)
          const precedingQuery = idx > 0 ? msgs[idx - 1].content : ''
          const turnNumber = msgs.slice(0, idx + 1).filter((m) => m.role === 'user').length
          submitFeedback(messageId, activeSessionId, rating, precedingQuery, comment).catch(() => {})
          if (rating === 1) {
            trackFeedbackPositive(precedingQuery, turnNumber)
          } else {
            trackFeedbackNegative(precedingQuery, turnNumber)
          }
          set((s) => ({
            feedbackToast: true,
            sessions: patchActiveMessages(s.sessions, s.activeSessionId, (msgs) =>
              msgs.map((m) => (m.id === messageId ? { ...m, feedback: rating } : m))
            ),
          }))
        },

        switchSession: (id) => {
          if (get().isStreaming) return
          const targetMessages = get().sessions[id]?.messages ?? []
          const hasTurns = targetMessages.some((m) => m.role === 'user')
          if (hasTurns && !hasAnalyticsSession()) trackSessionStart('resume_chat')
          set({ activeSessionId: id, error: null })
        },

        deleteSession: (id) => {
          const { sessions, activeSessionId } = get()
          const remaining = Object.fromEntries(Object.entries(sessions).filter(([k]) => k !== id))
          clearHistory(id).catch(() => {})

          if (id === activeSessionId) {
            const others = Object.values(remaining).sort((a, b) => b.createdAt - a.createdAt)
            if (others.length > 0) {
              set({ sessions: remaining, activeSessionId: others[0].id })
            } else {
              const fresh = createSession()
              set({ sessions: { [fresh.id]: fresh }, activeSessionId: fresh.id })
            }
          } else {
            set({ sessions: remaining })
          }
        },

        startNewChat: () => {
          const { sessions, activeSessionId, isStreaming } = get()
          if (isStreaming) return
          // Don't create a blank session if current one is already empty
          if ((sessions[activeSessionId]?.messages.length ?? 0) === 0) return
          // End the current analytics session before starting a new one
          const totalTurns = sessions[activeSessionId]?.messages.filter((m) => m.role === 'user').length ?? 0
          trackSessionEnd(totalTurns)
          clearHistory(activeSessionId).catch(() => {})
          const fresh = createSession()
          set((s) => ({
            sessions: { ...s.sessions, [fresh.id]: fresh },
            activeSessionId: fresh.id,
            error: null,
          }))
        },

        sendMessage: async (query: string) => {
          await get()._streamQuery(query)
        },

        _streamQuery: async (query: string) => {
          const { activeSessionId, isStreaming, accessDenied, rateLimited, apiDisabled, monthlyExhausted } = get()
          if (!query.trim() || isStreaming || accessDenied || rateLimited || apiDisabled || monthlyExhausted) return
          set({ error: null })

          // Turn number = existing user messages + 1 (this one)
          const existingMsgs = get().sessions[activeSessionId]?.messages ?? []
          const turnNumber = existingMsgs.filter((m) => m.role === 'user').length + 1

          // Fire analytics before the API call
          if (turnNumber >= 2) trackFollowupQuery(query, turnNumber)

          const userMsg: Message = { id: makeId(), role: 'user', content: query }
          const assistantId = makeId()
          const assistantMsg: Message = { id: assistantId, role: 'assistant', content: '', streaming: true }

          set((s) => ({
            isStreaming: true,
            stageStalled: false,
            sessions: patchActiveMessages(s.sessions, s.activeSessionId, (msgs) => [
              ...msgs,
              userMsg,
              assistantMsg,
            ]),
          }))

          // Watchdog: flips stageStalled if the currently *displayed* stage sits
          // this long with no transition and no tokens.
          let staleTimer: ReturnType<typeof setTimeout> | null = null
          const armStaleTimer = () => {
            if (staleTimer) clearTimeout(staleTimer)
            staleTimer = setTimeout(() => set({ stageStalled: true }), STAGE_STALL_MS)
          }
          const disarmStaleTimer = () => {
            if (staleTimer) clearTimeout(staleTimer)
            staleTimer = null
          }

          // Stage display queue: each real stage the backend reports is guaranteed
          // at least MIN_STAGE_DISPLAY_MS on screen before the next one can replace
          // it, so a fast retrieval can never skip past "Checking Adobe
          // documentation" before a user has a chance to read it. Tokens always
          // preempt this immediately (see statusCleared below) — the queue only
          // paces transitions *between* status stages, never delays real content.
          let stageQueue: ChatStage[] = []
          let dwellTimer: ReturnType<typeof setTimeout> | null = null
          const clearDwellTimer = () => {
            if (dwellTimer) clearTimeout(dwellTimer)
            dwellTimer = null
          }
          const showNextQueuedStage = () => {
            const next = stageQueue.shift()
            if (next === undefined) {
              dwellTimer = null
              return
            }
            set({ currentStage: next, stageStalled: false })
            armStaleTimer()
            dwellTimer = setTimeout(showNextQueuedStage, MIN_STAGE_DISPLAY_MS)
          }
          const enqueueStage = (stage: ChatStage) => {
            const last = stageQueue.length > 0 ? stageQueue[stageQueue.length - 1] : get().currentStage
            if (last === stage) return
            stageQueue.push(stage)
            if (!dwellTimer) showNextQueuedStage()
          }
          const resetStageMachinery = () => {
            stageQueue = []
            clearDwellTimer()
            disarmStaleTimer()
          }

          enqueueStage('understanding')
          let statusCleared = false

          try {
            for await (const event of streamChat(query, activeSessionId, false, assistantId)) {
              if (!get().isStreaming) break

              if (event.type === 'status') {
                enqueueStage(event.stage)
              } else if (event.type === 'token') {
                if (!statusCleared) {
                  statusCleared = true
                  resetStageMachinery()
                  set({ currentStage: null, stageStalled: false })
                }
                set((s) => ({
                  sessions: patchActiveMessages(s.sessions, s.activeSessionId, (msgs) =>
                    msgs.map((m) => (m.id === assistantId ? { ...m, content: m.content + event.content } : m))
                  ),
                }))
              } else if (event.type === 'citations') {
                set((s) => ({
                  sessions: patchActiveMessages(s.sessions, s.activeSessionId, (msgs) =>
                    msgs.map((m) => (m.id === assistantId ? { ...m, citations: event.citations as Citation[] } : m))
                  ),
                }))
              } else if (event.type === 'evidence') {
                const { type: _t, ...evidence } = event
                set((s) => ({
                  sessions: patchActiveMessages(s.sessions, s.activeSessionId, (msgs) =>
                    msgs.map((m) => (m.id === assistantId ? { ...m, evidence: evidence as RetrievalEvidence } : m))
                  ),
                }))
              } else if (event.type === 'done') {
                resetStageMachinery()
                const updatesFromDone: Partial<ChatState> = { currentStage: null, stageStalled: false }
                if (event.queries_used !== undefined) updatesFromDone.queriesUsed = event.queries_used
                if (event.queries_remaining !== undefined) updatesFromDone.queriesRemaining = event.queries_remaining
                if (event.queries_limit !== undefined) updatesFromDone.queriesLimit = event.queries_limit

                const currentMsg = get().sessions[get().activeSessionId]?.messages
                  .find((m) => m.id === assistantId)
                const failureReason = currentMsg?.evidence?.failure_reason

                if (event.model === 'none') {
                  if (failureReason === 'off_topic' || failureReason === 'no_direct_match') {
                    trackNoAnswer(query, turnNumber, 'low_confidence')
                  } else {
                    trackNoAnswer(query, turnNumber, 'no_retrieval')
                  }
                } else {
                  trackResponseReceived(query, turnNumber, event.model, currentMsg?.citations?.length ?? 0)
                }

                set((s) => ({
                  ...updatesFromDone,
                  sessions: patchActiveMessages(s.sessions, s.activeSessionId, (msgs) =>
                    msgs.map((m) => (m.id === assistantId ? { ...m, streaming: false, model: event.model } : m))
                  ),
                }))
              } else if (event.type === 'error') {
                resetStageMachinery()
                trackNoAnswer(query, turnNumber, 'error')
                set((s) => ({
                  currentStage: null,
                  stageStalled: false,
                  error: event.message,
                  sessions: patchActiveMessages(s.sessions, s.activeSessionId, (msgs) =>
                    msgs.map((m) =>
                      m.id === assistantId ? { ...m, content: `Error: ${event.message}`, streaming: false } : m
                    )
                  ),
                }))
              }
            }
          } catch (err) {
            const msg = err instanceof Error ? err.message : String(err)
            const errStatus = (err as any)?.status
            const isDisabled = errStatus === 403
            const isApiDisabled = errStatus === 503 && msg === 'API_DISABLED'
            const isKnowledgeBankUpdating = errStatus === 503 && msg === 'KNOWLEDGE_BANK_UPDATING'
            const maintenance = (err as any)?.maintenance as
              | { message?: string; check_back_at?: string }
              | undefined
            const isMonthlyExhausted = errStatus === 429 && msg === 'MONTHLY_QUOTA_EXCEEDED'
            const isRateLimited = errStatus === 429 && !isMonthlyExhausted
            const rateLimitMsg = isRateLimited ? ((err as any)?.detail?.message ?? msg) : ''
            const suppressContent =
              isDisabled || isApiDisabled || isKnowledgeBankUpdating || isRateLimited || isMonthlyExhausted
            resetStageMachinery()
            set((s) => ({
              currentStage: null,
              stageStalled: false,
              error: suppressContent ? null : msg,
              accessDenied: isDisabled || s.accessDenied,
              rateLimited: isRateLimited || s.rateLimited,
              rateLimitMessage: isRateLimited ? rateLimitMsg : s.rateLimitMessage,
              apiDisabled: isApiDisabled || s.apiDisabled,
              knowledgeBankUpdating: isKnowledgeBankUpdating || s.knowledgeBankUpdating,
              knowledgeBankMessage: isKnowledgeBankUpdating
                ? (maintenance?.message ?? s.knowledgeBankMessage)
                : s.knowledgeBankMessage,
              knowledgeBankCheckBackAt: isKnowledgeBankUpdating
                ? (maintenance?.check_back_at ?? s.knowledgeBankCheckBackAt)
                : s.knowledgeBankCheckBackAt,
              monthlyExhausted: isMonthlyExhausted || s.monthlyExhausted,
              sessions: patchActiveMessages(s.sessions, s.activeSessionId, (msgs) =>
                msgs.map((m) =>
                  m.id === assistantId
                    ? { ...m, content: suppressContent ? '' : `Error: ${msg}`, streaming: false }
                    : m
                )
              ),
            }))
          } finally {
            resetStageMachinery()
            set({ isStreaming: false, currentStage: null, stageStalled: false })
          }

          // After streaming: generate follow-up questions (non-blocking)
          const finalMsg = get().sessions[get().activeSessionId]?.messages
            .find((m) => m.id === assistantId)
          if (finalMsg && finalMsg.content && !finalMsg.content.startsWith('Error:') && finalMsg.model !== 'none') {
            getFollowUps(query, finalMsg.content).then((follow_ups) => {
              if (follow_ups.length > 0) {
                set((s) => ({
                  sessions: patchActiveMessages(s.sessions, s.activeSessionId, (msgs) =>
                    msgs.map((m) => (m.id === assistantId ? { ...m, follow_ups } : m))
                  ),
                }))
              }
            })
          }
        },
      }
    },
    {
      name: 'el-chat-store',
      partialize: (s) => ({
        sessions: s.sessions,
        activeSessionId: s.activeSessionId,
      }),
      migrate: (persisted: any) => {
        if (persisted && !persisted.sessions) {
          const session = createSession()
          return { sessions: { [session.id]: session }, activeSessionId: session.id }
        }
        return persisted
      },
      version: 2,
    }
  )
)
