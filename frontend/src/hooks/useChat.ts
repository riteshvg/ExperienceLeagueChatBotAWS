import { useCallback, useEffect, useRef, useState } from 'react'
import { streamChat, clearHistory, type Message } from '@/lib/api'

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

export interface UseChatReturn {
  messages: Message[]
  sessionId: string
  isStreaming: boolean
  haikuOnly: boolean
  setHaikuOnly: (v: boolean) => void
  sendMessage: (query: string) => Promise<void>
  startNewChat: () => void
  error: string | null
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([])
  const [sessionId, setSessionId] = useState(() => getOrCreateSessionId())
  const [isStreaming, setIsStreaming] = useState(false)
  const [haikuOnly, setHaikuOnly] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<boolean>(false)

  // Persist sessionId
  useEffect(() => {
    localStorage.setItem(SESSION_KEY, sessionId)
  }, [sessionId])

  const sendMessage = useCallback(
    async (query: string) => {
      if (!query.trim() || isStreaming) return
      setError(null)
      abortRef.current = false

      const userMsg: Message = { id: makeId(), role: 'user', content: query }
      const assistantMsg: Message = {
        id: makeId(),
        role: 'assistant',
        content: '',
        streaming: true,
      }

      setMessages((prev) => [...prev, userMsg, assistantMsg])
      setIsStreaming(true)

      try {
        for await (const event of streamChat(query, sessionId, haikuOnly)) {
          if (abortRef.current) break

          if (event.type === 'token') {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsg.id
                  ? { ...m, content: m.content + event.content }
                  : m,
              ),
            )
          } else if (event.type === 'citations') {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsg.id
                  ? { ...m, citations: event.citations }
                  : m,
              ),
            )
          } else if (event.type === 'done') {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsg.id
                  ? { ...m, streaming: false, model: event.model }
                  : m,
              ),
            )
          } else if (event.type === 'error') {
            setError(event.message)
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsg.id
                  ? { ...m, content: `Error: ${event.message}`, streaming: false }
                  : m,
              ),
            )
          }
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err)
        setError(msg)
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsg.id
              ? { ...m, content: `Error: ${msg}`, streaming: false }
              : m,
          ),
        )
      } finally {
        setIsStreaming(false)
      }
    },
    [sessionId, haikuOnly, isStreaming],
  )

  const startNewChat = useCallback(() => {
    abortRef.current = true
    const newId = makeId()
    clearHistory(sessionId).catch(() => {})
    localStorage.setItem(SESSION_KEY, newId)
    setSessionId(newId)
    setMessages([])
    setError(null)
    setIsStreaming(false)
  }, [sessionId])

  return { messages, sessionId, isStreaming, haikuOnly, setHaikuOnly, sendMessage, startNewChat, error }
}
