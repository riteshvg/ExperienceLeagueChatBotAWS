import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { streamChat, clearHistory, type Message, type Citation } from '@/lib/api'

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

  sendMessage: (query: string) => Promise<void>
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

        clearError: () => set({ error: null }),

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
          const { activeSessionId, isStreaming } = get()
          if (!query.trim() || isStreaming) return
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
            for await (const event of streamChat(query, activeSessionId, false)) {
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
            set((s) => ({
              error: msg,
              sessions: patchActiveMessages(s.sessions, s.activeSessionId, (msgs) =>
                msgs.map((m) =>
                  m.id === assistantId ? { ...m, content: `Error: ${msg}`, streaming: false } : m
                )
              ),
            }))
          } finally {
            set({ isStreaming: false })
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
