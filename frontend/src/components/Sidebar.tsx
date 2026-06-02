import { useState } from 'react'
import { MessageSquare, Plus, Settings, Trash2, BookOpen, ChevronDown, ChevronRight, LogOut } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { useChatStore, type ChatSession } from '@/store/chatStore'
import { useAuthStore } from '@/store/authStore'
import { PROMPT_LIBRARY } from '@/lib/prompts'

interface Props {
  onSelectPrompt: (text: string) => void
}

function groupByDate(sessions: ChatSession[]): { label: string; items: ChatSession[] }[] {
  const now = Date.now()
  const DAY = 86_400_000
  const today: ChatSession[] = []
  const yesterday: ChatSession[] = []
  const older: ChatSession[] = []

  for (const s of sessions) {
    const age = now - s.createdAt
    if (age < DAY) today.push(s)
    else if (age < 2 * DAY) yesterday.push(s)
    else older.push(s)
  }

  return [
    { label: 'Today', items: today },
    { label: 'Yesterday', items: yesterday },
    { label: 'Earlier', items: older },
  ].filter((g) => g.items.length > 0)
}

export function Sidebar({ onSelectPrompt }: Props) {
  const { sessions, activeSessionId, isStreaming, startNewChat, switchSession, deleteSession } = useChatStore()
  const { logout } = useAuthStore()
  const navigate = useNavigate()
  const [showPrompts, setShowPrompts] = useState(false)
  const [openCategories, setOpenCategories] = useState<Record<string, boolean>>({})

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const sorted = Object.values(sessions).sort((a, b) => b.createdAt - a.createdAt)
  const groups = groupByDate(sorted)

  const toggleCategory = (cat: string) =>
    setOpenCategories((prev) => ({ ...prev, [cat]: !prev[cat] }))

  return (
    <aside className="w-64 flex-shrink-0 bg-slate-900 text-white flex flex-col h-full">
      {/* Logo */}
      <div className="px-4 py-4 border-b border-slate-700">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center">
            <span className="text-white text-xs font-bold">EL</span>
          </div>
          <span className="font-semibold text-sm">Experience League</span>
        </div>
      </div>

      {/* New chat button */}
      <div className="px-3 py-3">
        <button
          onClick={startNewChat}
          disabled={isStreaming}
          className={cn(
            'w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors',
            isStreaming ? 'text-slate-500 cursor-not-allowed' : 'text-slate-300 hover:bg-slate-700 hover:text-white',
          )}
        >
          <Plus className="w-4 h-4" />
          New chat
        </button>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-3 pb-3 space-y-4">

        {/* Session list */}
        {groups.map((group) => (
          <div key={group.label}>
            <p className="text-xs text-slate-500 uppercase tracking-wider px-2 mb-1">{group.label}</p>
            <div className="space-y-0.5">
              {group.items.map((session) => {
                const isActive = session.id === activeSessionId
                return (
                  <div
                    key={session.id}
                    className={cn(
                      'group flex items-center gap-2 px-2 py-2 rounded-lg cursor-pointer transition-colors',
                      isActive ? 'bg-slate-700 text-white' : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200',
                    )}
                    onClick={() => switchSession(session.id)}
                  >
                    <MessageSquare className="w-3.5 h-3.5 flex-shrink-0" />
                    <span className="flex-1 text-xs truncate">{session.title}</span>
                    <button
                      onClick={(e) => { e.stopPropagation(); deleteSession(session.id) }}
                      className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:text-red-400 transition-opacity"
                      title="Delete chat"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                )
              })}
            </div>
          </div>
        ))}

        {/* Prompt Library */}
        <div className="border-t border-slate-700 pt-3">
          <button
            onClick={() => setShowPrompts((v) => !v)}
            className="w-full flex items-center gap-2 px-2 py-2 rounded-lg text-sm text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
          >
            <BookOpen className="w-4 h-4 flex-shrink-0 text-violet-400" />
            <span className="flex-1 text-left font-medium">Prompt Library</span>
            {showPrompts ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
          </button>

          {showPrompts && (
            <div className="mt-1 space-y-1">
              {PROMPT_LIBRARY.map((cat) => (
                <div key={cat.category}>
                  <button
                    onClick={() => toggleCategory(cat.category)}
                    className="w-full flex items-center gap-1.5 px-2 py-1.5 text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors"
                  >
                    {openCategories[cat.category]
                      ? <ChevronDown className="w-3 h-3" />
                      : <ChevronRight className="w-3 h-3" />}
                    {cat.category}
                  </button>

                  {openCategories[cat.category] && (
                    <div className="ml-2 space-y-0.5">
                      {cat.prompts.map((p) => (
                        <button
                          key={p.id}
                          onClick={() => onSelectPrompt(p.text)}
                          className="w-full text-left px-2 py-1.5 rounded-md text-xs text-slate-400 hover:bg-slate-700 hover:text-white transition-colors truncate"
                          title={p.text}
                        >
                          {p.title}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="px-3 py-3 border-t border-slate-700 space-y-0.5">
        <Link
          to="/admin"
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-slate-400 hover:bg-slate-700 hover:text-white transition-colors no-underline"
        >
          <Settings className="w-4 h-4" />
          Admin
        </Link>
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-slate-400 hover:bg-slate-700 hover:text-red-400 transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Sign out
        </button>
      </div>
    </aside>
  )
}
