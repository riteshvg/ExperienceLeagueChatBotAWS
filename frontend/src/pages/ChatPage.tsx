import { useEffect, useRef, useState } from 'react'
import { Menu, Ban, Clock } from 'lucide-react'
import { useChatStore } from '@/store/chatStore'
import { useAuthStore } from '@/store/authStore'
import { ChatInput, type ChatInputHandle } from '@/components/ChatInput'
import { ChatMessage } from '@/components/ChatMessage'
import { Sidebar } from '@/components/Sidebar'
import { getMe } from '@/lib/api'
import { cn } from '@/lib/utils'

type Category = 'All' | 'Analytics' | 'CJA' | 'AEP' | 'Target' | 'AJO' | 'Cross-Product'

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
  AJO: [
    'What is Adobe Journey Optimizer and how does it differ from Adobe Campaign?',
    'How do I create a journey in Adobe Journey Optimizer?',
    'What is decision management in Adobe Journey Optimizer?',
    'How do I set up frequency capping rules in Adobe Journey Optimizer?',
  ],
  'Cross-Product': [
    'How do I use AEP audiences in Adobe Target for personalisation?',
    'How does data flow from Adobe Analytics to Customer Journey Analytics?',
    'How do I connect an Adobe Analytics report suite to CJA?',
    'What is the difference between Adobe Analytics and Real-Time CDP for audience building?',
    'How do server-side forwarding and the Experience Platform Web SDK compare for sending data to AEP?',
  ],
}

const CATEGORIES: Category[] = ['All', 'Analytics', 'CJA', 'AEP', 'Target', 'AJO', 'Cross-Product']

const CATEGORY_COLORS: Record<Exclude<Category, 'All'>, string> = {
  Analytics:       'bg-orange-50 text-orange-700 border-orange-200',
  CJA:             'bg-violet-50 text-violet-700 border-violet-200',
  AEP:             'bg-blue-50 text-blue-700 border-blue-200',
  Target:          'bg-red-50 text-red-700 border-red-200',
  AJO:             'bg-green-50 text-green-700 border-green-200',
  'Cross-Product': 'bg-teal-50 text-teal-700 border-teal-200',
}

export function ChatPage() {
  const {
    sessions, activeSessionId, isStreaming, sendMessage, error, accessDenied,
    rateLimited, rateLimitMessage, queriesUsed, queriesRemaining, queriesLimit,
    setUsage,
  } = useChatStore()
  const { logout } = useAuthStore()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [activeCategory, setActiveCategory] = useState<Category>('All')
  const messages = sessions[activeSessionId]?.messages ?? []

  const visibleQuestions = activeCategory === 'All'
    ? Object.entries(QUESTION_BANK).flatMap(([cat, qs]) =>
        qs.slice(0, 1).map((q) => ({ q, cat: cat as Exclude<Category, 'All'> }))
      )
    : QUESTION_BANK[activeCategory].map((q) => ({ q, cat: activeCategory as Exclude<Category, 'All'> }))

  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<ChatInputHandle>(null)

  useEffect(() => {
    getMe().then((usage) => setUsage(usage.queries_used, usage.queries_remaining, usage.queries_limit))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

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

  if (accessDenied) {
    return (
      <div className="flex w-full h-screen items-center justify-center bg-slate-50 p-6">
        <div className="flex flex-col items-center gap-4 max-w-sm text-center">
          <div className="w-14 h-14 rounded-full bg-red-100 flex items-center justify-center">
            <Ban className="w-7 h-7 text-red-500" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-800 mb-1">Account Disabled</h2>
            <p className="text-sm text-slate-500">
              Your access to Rovr has been disabled. If you believe this is an error, please contact the administrator.
            </p>
          </div>
          <button
            onClick={() => logout()}
            className="mt-2 px-5 py-2 rounded-lg bg-slate-800 text-white text-sm font-medium hover:bg-slate-900 transition-colors"
          >
            Sign out
          </button>
        </div>
      </div>
    )
  }

  if (rateLimited) {
    return (
      <div className="flex w-full h-screen items-center justify-center bg-slate-50 p-6">
        <div className="flex flex-col items-center gap-4 max-w-sm text-center">
          <div className="w-14 h-14 rounded-full bg-amber-100 flex items-center justify-center">
            <Clock className="w-7 h-7 text-amber-500" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-800 mb-1">Daily Limit Reached</h2>
            <p className="text-sm text-slate-500">
              {rateLimitMessage || 'Your daily query limit has been reached. Resets at midnight UTC.'}
            </p>
          </div>
        </div>
      </div>
    )
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
          <h1 className="text-sm font-semibold text-slate-700">Rovr</h1>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center px-4 py-8">
              <img src="/rovrlogo.png" alt="Rovr" className="h-12 w-auto mb-4" />
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
                        ? 'bg-[#10B981] text-white border-[#10B981]'
                        : 'bg-white text-slate-500 border-slate-200 hover:border-[#10B981] hover:text-[#10B981]'
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
                    <p className="text-sm text-slate-600 group-hover:text-[#14532D] leading-snug">{q}</p>
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
          <ChatInput ref={inputRef} onSend={sendMessage} disabled={isStreaming} />
          <div className="mt-2 flex flex-col items-center gap-0.5">
            <p className="text-center text-xs text-slate-400">
              Answers are grounded in Adobe Experience League documentation
            </p>
            {queriesRemaining !== null && (
              <p className={cn(
                'text-center text-xs mt-0.5',
                queriesRemaining === 0 ? 'text-red-500 font-medium' :
                queriesRemaining <= queriesLimit * 0.25 ? 'text-amber-500' :
                'text-slate-400'
              )}>
                {queriesUsed} / {queriesLimit} queries used today
              </p>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
