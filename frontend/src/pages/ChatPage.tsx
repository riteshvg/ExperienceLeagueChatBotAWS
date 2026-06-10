import { useEffect, useRef, useState } from 'react'
import { Menu } from 'lucide-react'
import { useChatStore } from '@/store/chatStore'
import { useAuthStore } from '@/store/authStore'
import { ChatInput, type ChatInputHandle } from '@/components/ChatInput'
import { ChatMessage } from '@/components/ChatMessage'
import { Sidebar } from '@/components/Sidebar'

type Category = 'All' | 'Analytics' | 'CJA' | 'AEP' | 'Target' | 'Cross-Product'

const QUESTION_BANK: Record<Exclude<Category, 'All'>, string[]> = {
  Analytics: [
    'How do I create a segment in Adobe Analytics?',
    'What is the difference between eVars and props in Adobe Analytics?',
    'How do I set up processing rules in Adobe Analytics?',
    'How do I configure marketing channel rules in Adobe Analytics?',
  ],
  CJA: [
    'What is a Data View in Customer Journey Analytics?',
    'How do I create a calculated metric in CJA?',
    'What is the difference between Adobe Analytics and Customer Journey Analytics?',
    'How does stitching work in Customer Journey Analytics?',
  ],
  AEP: [
    'What are the different ways to ingest data into Adobe Experience Platform?',
    'How do I create an XDM schema in Adobe Experience Platform?',
    'What is Real-Time CDP and how does it work with AEP profiles?',
    'How do I set up identity resolution in Adobe Experience Platform?',
  ],
  Target: [
    'How do I create an A/B test in Adobe Target?',
    'What is the difference between A/B testing and multivariate testing in Target?',
    'How do I set up Experience Targeting activities in Adobe Target?',
    'How do I use Recommendations in Adobe Target?',
  ],
  'Cross-Product': [
    'How do I use AEP audiences in Adobe Target for personalisation?',
    'How does data flow from Adobe Analytics to Customer Journey Analytics?',
    'How do I connect an Adobe Analytics report suite to CJA?',
    'What is the difference between Adobe Analytics and Real-Time CDP for audience building?',
    'How do server-side forwarding and the Experience Platform Web SDK compare for sending data to AEP?',
  ],
}

const CATEGORIES: Category[] = ['All', 'Analytics', 'CJA', 'AEP', 'Target', 'Cross-Product']

const CATEGORY_COLORS: Record<Exclude<Category, 'All'>, string> = {
  Analytics:       'bg-orange-50 text-orange-700 border-orange-200',
  CJA:             'bg-violet-50 text-violet-700 border-violet-200',
  AEP:             'bg-blue-50 text-blue-700 border-blue-200',
  Target:          'bg-red-50 text-red-700 border-red-200',
  'Cross-Product': 'bg-teal-50 text-teal-700 border-teal-200',
}

export function ChatPage() {
  const { sessions, activeSessionId, isStreaming, sendMessage, error } = useChatStore()
  const { isDemo, demoStatus, refreshDemoStatus } = useAuthStore()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [activeCategory, setActiveCategory] = useState<Category>('All')
  const messages = sessions[activeSessionId]?.messages ?? []
  const demoExhausted = isDemo && (demoStatus?.exhausted ?? false)

  const visibleQuestions = activeCategory === 'All'
    ? Object.entries(QUESTION_BANK).flatMap(([cat, qs]) =>
        qs.slice(0, 1).map((q) => ({ q, cat: cat as Exclude<Category, 'All'> }))
      )
    : QUESTION_BANK[activeCategory].map((q) => ({ q, cat: activeCategory as Exclude<Category, 'All'> }))

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
      <Sidebar onSelectPrompt={handleSelectPrompt} isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <main className="flex-1 flex flex-col min-w-0 bg-slate-50">
        {/* Header */}
        <header className="flex-shrink-0 h-12 bg-white border-b border-slate-200 flex items-center justify-between px-4">
          {/* Hamburger — mobile only */}
          <button
            onClick={() => setSidebarOpen(true)}
            className="md:hidden p-1.5 rounded-lg text-slate-500 hover:bg-slate-100 mr-2"
          >
            <Menu className="w-4 h-4" />
          </button>
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
            <div className="h-full flex flex-col items-center justify-center px-4 py-8">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center mb-4">
                <span className="text-white font-bold text-sm">EL</span>
              </div>
              <h2 className="text-lg font-semibold text-slate-700 mb-1 text-center">
                Ask about Adobe Experience League docs
              </h2>
              <p className="text-sm text-slate-400 max-w-md text-center mb-5">
                Analytics · CJA · Experience Platform · Target
              </p>

              {/* Category filter chips */}
              <div className="flex flex-wrap justify-center gap-1.5 mb-4 max-w-lg">
                {CATEGORIES.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setActiveCategory(cat)}
                    className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                      activeCategory === cat
                        ? 'bg-indigo-600 text-white border-indigo-600'
                        : 'bg-white text-slate-500 border-slate-200 hover:border-indigo-300 hover:text-indigo-600'
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>

              {/* Question cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-2xl">
                {visibleQuestions.map(({ q, cat }) => (
                  <button
                    key={q}
                    onClick={() => sendMessage(q)}
                    className="group text-left px-4 py-3 rounded-xl border border-slate-200 bg-white
                      hover:border-indigo-300 hover:shadow-sm transition-all"
                  >
                    <span className={`inline-block text-[10px] font-semibold px-1.5 py-0.5 rounded border mb-1.5 ${CATEGORY_COLORS[cat]}`}>
                      {cat}
                    </span>
                    <p className="text-sm text-slate-600 group-hover:text-indigo-700 leading-snug">{q}</p>
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
