import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { streamChat, clearHistory, getFollowUps, submitFeedback, type Message, type Citation } from '@/lib/api'

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

  sendMessage: (query: string) => Promise<void>
  setFeedback: (messageId: string, rating: 1 | -1, query: string) => void
  startNewChat: () => void
  switchSession: (id: string) => void
  deleteSession: (id: string) => void
  clearError: () => void
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

        clearError: () => set({ error: null }),

        setFeedback: (messageId, rating, _query) => {
          const { activeSessionId, sessions } = get()
          // Find the user message that preceded this assistant message
          const msgs = sessions[activeSessionId]?.messages ?? []
          const idx = msgs.findIndex((m) => m.id === messageId)
          const precedingQuery = idx > 0 ? msgs[idx - 1].content : ''
          submitFeedback(messageId, activeSessionId, rating, precedingQuery).catch(() => {})
          set((s) => ({
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
          clearHistory(activeSessionId).catch(() => {})
          const fresh = createSession()
          set((s) => ({
            sessions: { ...s.sessions, [fresh.id]: fresh },
            activeSessionId: fresh.id,
            error: null,
          }))
        },

        sendMessage: async (query: string) => {
          const { activeSessionId, isStreaming, accessDenied } = get()
          if (!query.trim() || isStreaming || accessDenied) return
          set({ error: null })

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
              } else if (event.type === 'done') {
                set((s) => ({
                  sessions: patchActiveMessages(s.sessions, s.activeSessionId, (msgs) =>
                    msgs.map((m) => (m.id === assistantId ? { ...m, streaming: false, model: event.model } : m))
                  ),
                }))
              } else if (event.type === 'error') {
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
            const isDisabled = (err as Error & { status?: number })?.status === 403
            set((s) => ({
              error: msg,
              accessDenied: isDisabled || s.accessDenied,
              sessions: patchActiveMessages(s.sessions, s.activeSessionId, (msgs) =>
                msgs.map((m) =>
                  m.id === assistantId ? { ...m, content: isDisabled ? '' : `Error: ${msg}`, streaming: false } : m
                )
              ),
            }))
          } finally {
            set({ isStreaming: false })
          }

          // After streaming: generate follow-up questions (non-blocking)
          const finalMsg = get().sessions[get().activeSessionId]?.messages
            .find((m) => m.id === assistantId)
          if (finalMsg && finalMsg.content && !finalMsg.content.startsWith('Error:')) {
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
