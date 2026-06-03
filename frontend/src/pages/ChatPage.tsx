import { useEffect, useRef } from 'react'
import { useChatStore } from '@/store/chatStore'
import { useAuthStore } from '@/store/authStore'
import { ChatInput, type ChatInputHandle } from '@/components/ChatInput'
import { ChatMessage } from '@/components/ChatMessage'
import { Sidebar } from '@/components/Sidebar'

export function ChatPage() {
  const { sessions, activeSessionId, isStreaming, sendMessage, error } = useChatStore()
  const { isDemo, demoStatus, refreshDemoStatus } = useAuthStore()
  const messages = sessions[activeSessionId]?.messages ?? []
  const demoExhausted = isDemo && (demoStatus?.exhausted ?? false)

  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<ChatInputHandle>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (!isStreaming && messages.length > 0) {
      inputRef.current?.focus()
      // Refresh demo counter after each answer
      if (isDemo) refreshDemoStatus()
    }
  }, [isStreaming, messages.length, isDemo, refreshDemoStatus])

  const handleSelectPrompt = (text: string) => {
    inputRef.current?.fill(text)
  }

  return (
    <div className="flex w-full h-screen overflow-hidden">
      <Sidebar onSelectPrompt={handleSelectPrompt} />

      <main className="flex-1 flex flex-col min-w-0 bg-slate-50">
        {/* Header */}
        <header className="flex-shrink-0 h-12 bg-white border-b border-slate-200 flex items-center justify-between px-4">
          <h1 className="text-sm font-semibold text-slate-700">
            Adobe Docs Assistant
            <span className="ml-2 text-xs font-normal text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded-full">unofficial</span>
          </h1>
          {isDemo && demoStatus && (
            <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${
              demoExhausted
                ? 'bg-red-50 text-red-600 border border-red-200'
                : 'bg-amber-50 text-amber-700 border border-amber-200'
            }`}>
              {demoExhausted
                ? 'Demo limit reached'
                : `${demoStatus.questions_remaining} of ${demoStatus.questions_limit} questions remaining`}
            </span>
          )}
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
            <ChatMessage key={msg.id} message={msg} onFollowUpClick={handleSelectPrompt} />
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
          {demoExhausted ? (
            <div className="text-center py-3 px-4 rounded-xl bg-amber-50 border border-amber-200">
              <p className="text-sm font-medium text-amber-800">You've used all 5 demo questions</p>
              <p className="text-xs text-amber-600 mt-1">Contact the administrator to reset your demo access</p>
            </div>
          ) : (
            <ChatInput ref={inputRef} onSend={sendMessage} disabled={isStreaming} />
          )}
          <p className="text-center text-xs text-slate-400 mt-2">
            Answers are grounded in Adobe Experience League documentation
          </p>
        </div>
      </main>
    </div>
  )
}
