import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { streamChat, clearHistory, type Message, type Citation } from '@/lib/api'

const SESSION_KEY = 'el_session_id'

function makeId() {
  return Math.random().toString(36).slice(2)
}

function getOrCreateSessionId(): string {
  let id = localStorage.getItem(SESSION_KEY)
  if (!id) {
    id = makeId()
    localStorage.setItem(SESSION_KEY, id)
  }
  return id
}

interface ChatState {
  messages: Message[]
  sessionId: string
  isStreaming: boolean
  haikuOnly: boolean
  error: string | null

  // Actions
  setHaikuOnly: (v: boolean) => void
  sendMessage: (query: string) => Promise<void>
  startNewChat: () => void
  clearError: () => void
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      messages: [],
      sessionId: getOrCreateSessionId(),
      isStreaming: false,
      haikuOnly: false,
      error: null,

      setHaikuOnly: (v) => set({ haikuOnly: v }),
      clearError: () => set({ error: null }),

      sendMessage: async (query: string) => {
        const { sessionId, haikuOnly, isStreaming } = get()
        if (!query.trim() || isStreaming) return

        set({ error: null })

        const userMsg: Message = { id: makeId(), role: 'user', content: query }
        const assistantId = makeId()
        const assistantMsg: Message = { id: assistantId, role: 'assistant', content: '', streaming: true }

        set((s) => ({ messages: [...s.messages, userMsg, assistantMsg], isStreaming: true }))

        try {
          for await (const event of streamChat(query, sessionId, haikuOnly)) {
            if (!get().isStreaming) break

            if (event.type === 'token') {
              set((s) => ({
                messages: s.messages.map((m) =>
                  m.id === assistantId ? { ...m, content: m.content + event.content } : m
                ),
              }))
            } else if (event.type === 'citations') {
              set((s) => ({
                messages: s.messages.map((m) =>
                  m.id === assistantId ? { ...m, citations: event.citations as Citation[] } : m
                ),
              }))
            } else if (event.type === 'done') {
              set((s) => ({
                messages: s.messages.map((m) =>
                  m.id === assistantId ? { ...m, streaming: false, model: event.model } : m
                ),
              }))
            } else if (event.type === 'error') {
              set((s) => ({
                error: event.message,
                messages: s.messages.map((m) =>
                  m.id === assistantId ? { ...m, content: `Error: ${event.message}`, streaming: false } : m
                ),
              }))
            }
          }
        } catch (err) {
          const msg = err instanceof Error ? err.message : String(err)
          set((s) => ({
            error: msg,
            messages: s.messages.map((m) =>
              m.id === assistantId ? { ...m, content: `Error: ${msg}`, streaming: false } : m
            ),
          }))
        } finally {
          set({ isStreaming: false })
        }
      },

      startNewChat: () => {
        const { sessionId } = get()
        clearHistory(sessionId).catch(() => {})
        const newId = makeId()
        localStorage.setItem(SESSION_KEY, newId)
        set({ sessionId: newId, messages: [], error: null, isStreaming: false })
      },
    }),
    {
      name: 'el-chat-store',
      // Only persist haikuOnly preference across sessions, not messages
      partialize: (s) => ({ haikuOnly: s.haikuOnly }),
    }
  )
)
