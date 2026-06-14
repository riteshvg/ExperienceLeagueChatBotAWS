import { useState } from 'react'
import { MessageSquare, Plus, Settings, Trash2, BookOpen, ChevronDown, ChevronRight, LogOut, X, PanelLeftClose, PanelLeftOpen } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { useChatStore, type ChatSession } from '@/store/chatStore'
import { useAuthStore } from '@/store/authStore'
import { useQuotaStore } from '@/store/quotaStore'
import { PROMPT_LIBRARY } from '@/lib/prompts'

function formatResetDate(isoDate: string | null): string {
  if (!isoDate) return ''
  try {
    const d = new Date(isoDate + 'T00:00:00Z')
    return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' })
  } catch { return isoDate }
}

interface Props {
  onSelectPrompt: (text: string) => void
  isOpen: boolean
  onClose: () => void
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

export function Sidebar({ onSelectPrompt, isOpen, onClose }: Props) {
  const { sessions, activeSessionId, isStreaming, startNewChat, switchSession, deleteSession } = useChatStore()
  const { logout, session } = useAuthStore()
  const { monthlyLimit, monthlyUsed, monthlyRemaining, resetDate, isExhausted } = useQuotaStore()
  const navigate = useNavigate()
  const [showPrompts, setShowPrompts] = useState(false)
  const [openCategories, setOpenCategories] = useState<Record<string, boolean>>({})
  const [collapsed, setCollapsed] = useState(false)

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  const sorted = Object.values(sessions).sort((a, b) => b.createdAt - a.createdAt)
  const groups = groupByDate(sorted)

  const toggleCategory = (cat: string) =>
    setOpenCategories((prev) => ({ ...prev, [cat]: !prev[cat] }))

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-20 md:hidden"
          onClick={onClose}
        />
      )}
    <aside className={cn(
      'flex-shrink-0 bg-[#14532D] text-white flex flex-col h-full z-30 transition-all duration-200',
      // Desktop: always visible, collapsible
      'md:relative md:translate-x-0',
      collapsed ? 'md:w-14' : 'md:w-64',
      // Mobile: overlay, slides in/out (always full width)
      'w-72 fixed inset-y-0 left-0',
      isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
    )}>
      {/* Logo */}
      <div className={cn('py-4 border-b border-white/10', collapsed ? 'px-3' : 'px-4')}>
        <div className="flex items-center gap-2 justify-between">
          <button onClick={onClose} className="md:hidden p-1 text-white/60 hover:text-white">
            <X className="w-4 h-4" />
          </button>
          <img src={`${import.meta.env.BASE_URL}rovrlogo.png`} alt="Rovr" className={cn('flex-shrink-0', collapsed ? 'h-7 w-auto' : 'h-8 w-auto')} />
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <span className="font-semibold text-sm truncate">Rovr</span>
            </div>
          )}
          {/* Collapse toggle — desktop only */}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="hidden md:flex p-1 text-white/60 hover:text-white flex-shrink-0"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed
              ? <PanelLeftOpen className="w-4 h-4" />
              : <PanelLeftClose className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* New chat button */}
      <div className={cn('py-3', collapsed ? 'px-2' : 'px-3')}>
        <button
          onClick={startNewChat}
          disabled={isStreaming}
          title="New chat"
          className={cn(
            'w-full flex items-center rounded-lg text-sm transition-colors',
            collapsed ? 'justify-center p-2' : 'gap-2 px-3 py-2',
            isStreaming ? 'text-slate-500 cursor-not-allowed' : 'text-white/80 hover:bg-white/10 hover:text-white',
          )}
        >
          <Plus className="w-4 h-4 flex-shrink-0" />
          {!collapsed && 'New chat'}
        </button>
      </div>

      {/* Monthly quota bar — only for users with a real limit (< 9999) */}
      {!collapsed && monthlyLimit < 9999 && (
        <div className="px-4 pb-3">
          <div className="w-full h-1.5 bg-white/20 rounded-full overflow-hidden">
            <div
              className={cn(
                'h-1.5 rounded-full transition-all',
                isExhausted ? 'bg-red-400' :
                monthlyRemaining <= 5 ? 'bg-amber-400' :
                'bg-[#10B981]'
              )}
              style={{ width: `${Math.min(100, Math.round((monthlyUsed / monthlyLimit) * 100))}%` }}
            />
          </div>
          <p className={cn(
            'text-xs mt-1',
            isExhausted ? 'text-red-300' :
            monthlyRemaining <= 5 ? 'text-amber-300' :
            'text-white/60'
          )}>
            {isExhausted
              ? 'Monthly quota exhausted'
              : `${monthlyRemaining} of ${monthlyLimit} queries remaining`}
          </p>
          {resetDate && (
            <p className="text-xs text-white/40 mt-0.5">Resets {formatResetDate(resetDate)}</p>
          )}
        </div>
      )}

      {/* Scrollable content — hidden when collapsed */}
      <div className={cn('flex-1 overflow-y-auto pb-3 space-y-4', collapsed ? 'hidden md:hidden' : 'px-3')}>

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
                      isActive ? 'bg-white/20 text-white' : 'text-white/60 hover:bg-white/10 hover:text-white',
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
        <div className="border-t border-white/10 pt-3">
          <button
            onClick={() => setShowPrompts((v) => !v)}
            className="w-full flex items-center gap-2 px-2 py-2 rounded-lg text-sm text-white/80 hover:bg-white/10 hover:text-white transition-colors"
          >
            <BookOpen className="w-4 h-4 flex-shrink-0 text-[#A7F3D0]" />
            <span className="flex-1 text-left font-medium">Prompt Library</span>
            {showPrompts ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
          </button>

          {showPrompts && (
            <div className="mt-1 space-y-1">
              {PROMPT_LIBRARY.map((cat) => (
                <div key={cat.category}>
                  <button
                    onClick={() => toggleCategory(cat.category)}
                    className="w-full flex items-center gap-1.5 px-2 py-1.5 text-xs font-semibold text-white/60 hover:text-slate-200 transition-colors"
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
                          className="w-full text-left px-2 py-1.5 rounded-md text-xs text-white/60 hover:bg-white/10 hover:text-white transition-colors truncate"
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

      {/* Disclaimer — hidden when collapsed */}
      {!collapsed && (
        <div className="px-4 py-3 mx-3 mb-2 rounded-lg bg-black/20 border border-white/10">
          <p className="text-xs text-white/50 leading-relaxed">
            Built for learning purposes only. Not affiliated with or endorsed by Adobe. All documentation belongs to Adobe.
          </p>
        </div>
      )}

      {/* Footer */}
      <div className={cn('py-3 border-t border-white/10 space-y-0.5', collapsed ? 'px-2' : 'px-3')}>
        {/* User avatar + name */}
        {session && !collapsed && (
          <div className="flex items-center gap-2 px-3 py-2 mb-1">
            {session.picture ? (
              <img
                src={session.picture}
                alt={session.name}
                className="w-7 h-7 rounded-full flex-shrink-0"
                referrerPolicy="no-referrer"
              />
            ) : (
              <div className="w-7 h-7 rounded-full bg-white/20 flex items-center justify-center flex-shrink-0">
                <span className="text-xs font-medium text-white/80">
                  {session.name.charAt(0).toUpperCase()}
                </span>
              </div>
            )}
            <span className="text-xs text-white/80 truncate">{session.name || session.email}</span>
          </div>
        )}
        {session && collapsed && session.picture && (
          <div className="flex justify-center mb-1">
            <img
              src={session.picture}
              alt={session.name}
              className="w-7 h-7 rounded-full"
              referrerPolicy="no-referrer"
            />
          </div>
        )}

        {session?.is_admin && (
          <Link
            to="/admin"
            title="Admin"
            className={cn(
              'flex items-center rounded-lg text-sm text-white/60 hover:bg-white/10 hover:text-white transition-colors no-underline',
              collapsed ? 'justify-center p-2' : 'gap-2 px-3 py-2'
            )}
          >
            <Settings className="w-4 h-4 flex-shrink-0" />
            {!collapsed && 'Admin'}
          </Link>
        )}
        <button
          onClick={handleLogout}
          title="Sign out"
          className={cn(
            'w-full flex items-center rounded-lg text-sm text-white/60 hover:bg-white/10 hover:text-red-400 transition-colors',
            collapsed ? 'justify-center p-2' : 'gap-2 px-3 py-2'
          )}
        >
          <LogOut className="w-4 h-4 flex-shrink-0" />
          {!collapsed && 'Sign out'}
        </button>
      </div>
    </aside>
    </>
  )
}
