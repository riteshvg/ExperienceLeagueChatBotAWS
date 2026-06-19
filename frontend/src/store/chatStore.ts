import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { streamChat, clearHistory, getFollowUps, submitFeedback, type Message, type Citation, type RetrievalEvidence } from '@/lib/api'
import {
  trackQuerySent,
  trackFollowupQuery,
  trackSessionStart,
  trackSessionEnd,
  trackFeedbackPositive,
  trackFeedbackNegative,
  trackNoAnswer,
} from '@/analytics'


function makeId() {
  return Math.random().toString(36).slice(2)
}

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
          trackSessionStart('new_chat_button')
          set((s) => ({
            sessions: { ...s.sessions, [fresh.id]: fresh },
            activeSessionId: fresh.id,
            error: null,
          }))
        },

        sendMessage: async (query: string) => {
          const { activeSessionId, isStreaming, accessDenied, rateLimited, apiDisabled, monthlyExhausted } = get()
          if (!query.trim() || isStreaming || accessDenied || rateLimited || apiDisabled || monthlyExhausted) return
          set({ error: null })

          // Turn number = existing user messages + 1 (this one)
          const existingMsgs = get().sessions[activeSessionId]?.messages ?? []
          const turnNumber = existingMsgs.filter((m) => m.role === 'user').length + 1

          // Fire analytics before the API call
          trackQuerySent(query, turnNumber, 'unknown', 'uncategorised')
          if (turnNumber >= 2) trackFollowupQuery(query, turnNumber)

          const userMsg: Message = { id: makeId(), role: 'user', content: query }
          const assistantId = makeId()
          const assistantMsg: Message = { id: assistantId, role: 'assistant', content: '', streaming: true }

          set((s) => ({
            isStreaming: true,
            sessions: patchActiveMessages(s.sessions, s.activeSessionId, (msgs) => [
              ...msgs,
              userMsg,
              assistantMsg,
            ]),
          }))

          try {
            for await (const event of streamChat(query, activeSessionId, false, assistantId)) {
              if (!get().isStreaming) break

              if (event.type === 'token') {
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
                const updatesFromDone: Partial<ChatState> = {}
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
                }

                set((s) => ({
                  ...updatesFromDone,
                  sessions: patchActiveMessages(s.sessions, s.activeSessionId, (msgs) =>
                    msgs.map((m) => (m.id === assistantId ? { ...m, streaming: false, model: event.model } : m))
                  ),
                }))
              } else if (event.type === 'error') {
                trackNoAnswer(query, turnNumber, 'error')
                set((s) => ({
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
            set((s) => ({
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
            set({ isStreaming: false })
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
