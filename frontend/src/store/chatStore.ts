import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface SourceLink {
  title: string
  url: string
  video_url?: string
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  metadata?: {
    model_used?: string
    documents?: any[]
    source_links?: SourceLink[]
    from_cache?: boolean
  }
}

interface ChatState {
  messages: Message[]
  sessionId: string | null
  addMessage: (message: Message) => void
  clearMessages: () => void
  setSessionId: (sessionId: string | null) => void
}

// Generate a session ID
const generateSessionId = () => {
  return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      messages: [],
      sessionId: null,
      addMessage: (message) =>
        set((state) => {
          const newMessages = [...state.messages, message]
          return { messages: newMessages }
        }),
      clearMessages: () => {
        const newSessionId = generateSessionId()
        set({ messages: [], sessionId: newSessionId })
      },
      setSessionId: (sessionId) => set({ sessionId }),
    }),
    {
      name: 'chat-storage', // localStorage key
      // Only persist messages and sessionId
      partialize: (state) => ({
        messages: state.messages,
        sessionId: state.sessionId || generateSessionId(),
      }),
    }
  )
)

