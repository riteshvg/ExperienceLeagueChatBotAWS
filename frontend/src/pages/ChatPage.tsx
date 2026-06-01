import { useEffect, useRef } from 'react'
import { Zap } from 'lucide-react'
import { useChatStore } from '@/store/chatStore'
import { ChatInput, type ChatInputHandle } from '@/components/ChatInput'
import { ChatMessage } from '@/components/ChatMessage'
import { Sidebar } from '@/components/Sidebar'
import { cn } from '@/lib/utils'

export function ChatPage() {
  const { sessions, activeSessionId, isStreaming, haikuOnly, setHaikuOnly, sendMessage, error } = useChatStore()
  const messages = sessions[activeSessionId]?.messages ?? []

  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<ChatInputHandle>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (!isStreaming && messages.length > 0) {
      inputRef.current?.focus()
    }
  }, [isStreaming, messages.length])

  const handleSelectPrompt = (text: string) => {
    inputRef.current?.fill(text)
  }

  return (
    <div className="flex w-full h-screen overflow-hidden">
      <Sidebar onSelectPrompt={handleSelectPrompt} />

      <main className="flex-1 flex flex-col min-w-0 bg-slate-50">
        {/* Header */}
        <header className="flex-shrink-0 h-12 bg-white border-b border-slate-200 flex items-center justify-between px-4">
          <h1 className="text-sm font-semibold text-slate-700">Adobe Docs Assistant</h1>
          <label className="flex items-center gap-2 cursor-pointer select-none text-xs text-slate-500">
            <Zap className={cn('w-3.5 h-3.5', haikuOnly ? 'text-emerald-500' : 'text-slate-300')} />
            <span>Fast (Haiku)</span>
            <button
              role="switch"
              aria-checked={haikuOnly}
              onClick={() => setHaikuOnly(!haikuOnly)}
              className={cn(
                'relative w-8 h-4 rounded-full transition-colors',
                haikuOnly ? 'bg-emerald-500' : 'bg-slate-200',
              )}
            >
              <span
                className={cn(
                  'absolute top-0.5 w-3 h-3 rounded-full bg-white shadow transition-transform',
                  haikuOnly ? 'translate-x-4.5' : 'translate-x-0.5',
                )}
              />
            </button>
          </label>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center px-8">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center mb-4">
                <span className="text-white font-bold">EL</span>
              </div>
              <h2 className="text-lg font-semibold text-slate-700 mb-2">
                Ask about Adobe Experience League docs
              </h2>
              <p className="text-sm text-slate-400 max-w-sm">
                Get answers about Adobe Analytics, Customer Journey Analytics, and Adobe Experience Platform from the official documentation.
              </p>
              <div className="grid grid-cols-1 gap-2 mt-6 w-full max-w-sm">
                {[
                  'How do I create a segment in Adobe Analytics?',
                  'What is a Data View in CJA?',
                  'How does XDM schema composition work?',
                ].map((q) => (
                  <button
                    key={q}
                    onClick={() => sendMessage(q)}
                    className="text-left px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-sm text-slate-600 hover:border-blue-300 hover:text-blue-700 transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}

          {error && (
            <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2">
              {error}
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="flex-shrink-0 px-4 py-3 bg-slate-50 border-t border-slate-200">
          <ChatInput ref={inputRef} onSend={sendMessage} disabled={isStreaming} />
          <p className="text-center text-xs text-slate-400 mt-2">
            Answers are grounded in Adobe Experience League documentation
          </p>
        </div>
      </main>
    </div>
  )
}
