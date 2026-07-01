import { useState } from 'react'
import { MessageSquare, Plus, Settings, Trash2, BookOpen, ChevronDown, ChevronRight, X, PanelLeftClose, PanelLeftOpen, House, GitBranch, Info } from 'lucide-react'
import { Link } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { useChatStore, type ChatSession } from '@/store/chatStore'
import { useAuthStore } from '@/store/authStore'
import { PROMPT_LIBRARY } from '@/lib/prompts'

interface Props {
  onSelectPrompt: (text: string, meta?: { title?: string; category?: string }) => void
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
  const { session } = useAuthStore()
  const [showPrompts, setShowPrompts] = useState(false)
  const [openCategories, setOpenCategories] = useState<Record<string, boolean>>({})
  const [collapsed, setCollapsed] = useState(false)

  const sorted = Object.values(sessions).sort((a, b) => b.createdAt - a.createdAt)
  const groups = groupByDate(sorted)
  const gitBranch = import.meta.env.VITE_GIT_BRANCH ?? ''
  const showEnhancementsBadge = gitBranch === 'enhancements'
  const enhancementsBranchUrl =
    'https://github.com/riteshvg/ExperienceLeagueChatBotAWS/tree/enhancements'

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
      {/* Logo + collapse toggle */}
      <div className={cn('border-b border-white/10', collapsed ? 'md:py-3 md:px-2' : 'py-4 px-4')}>
        {/* Collapsed rail — desktop only */}
        {collapsed && (
          <div className="hidden md:flex flex-col items-center gap-2 py-3 px-2">
            <img
              src={`${import.meta.env.BASE_URL}rovrlogo.png`}
              alt="Rovr"
              className="h-6 w-auto flex-shrink-0"
            />
            <button
              onClick={() => setCollapsed(false)}
              className="p-1.5 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-colors"
              title="Expand sidebar"
              aria-label="Expand sidebar"
            >
              <PanelLeftOpen className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Expanded header — always on mobile; desktop when sidebar is open */}
        <div className={cn('flex items-center gap-2 justify-between', collapsed && 'md:hidden')}>
          <button onClick={onClose} className="md:hidden p-1 text-white/60 hover:text-white">
            <X className="w-4 h-4" />
          </button>
          <img src={`${import.meta.env.BASE_URL}rovrlogo.png`} alt="Rovr" className="h-8 w-auto flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <span className="font-semibold text-sm truncate">Rovr</span>
          </div>
          <button
            onClick={() => setCollapsed(true)}
            className="hidden md:flex p-1.5 rounded-lg text-white/60 hover:text-white hover:bg-white/10 flex-shrink-0 transition-colors"
            title="Collapse sidebar"
            aria-label="Collapse sidebar"
          >
            <PanelLeftClose className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* New chat button */}
      <div className={cn('py-3 px-3', collapsed && 'md:px-2')}>
        <button
          onClick={startNewChat}
          disabled={isStreaming}
          title="New chat"
          className={cn(
            'w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors',
            collapsed && 'md:justify-center md:p-2 md:gap-0 md:px-2',
            isStreaming ? 'text-slate-500 cursor-not-allowed' : 'text-white/80 hover:bg-white/10 hover:text-white',
          )}
        >
          <Plus className="w-4 h-4 flex-shrink-0" />
          <span className={cn(collapsed && 'md:hidden')}>New chat</span>
        </button>
      </div>


      {/* Scrollable content — hidden when collapsed */}
      <div className={cn('flex-1 overflow-y-auto pb-3 space-y-4 px-3', collapsed && 'md:hidden')}>

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
                          onClick={() => onSelectPrompt(p.text, { title: p.title, category: cat.category })}
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

      {/* Git branch — enhancements builds only (VITE_GIT_BRANCH from vite.config) */}
      {showEnhancementsBadge && !collapsed && (
        <a
          href={enhancementsBranchUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="mx-3 mb-2 flex items-center gap-2 rounded-lg border border-amber-400/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-100/90 no-underline hover:bg-amber-500/20 transition-colors"
          title="Running enhancements branch — not production"
        >
          <GitBranch className="w-3.5 h-3.5 flex-shrink-0 text-amber-300" />
          <span className="font-medium">enhancements</span>
          <span className="text-amber-200/60">· dev preview</span>
        </a>
      )}
      {showEnhancementsBadge && collapsed && (
        <a
          href={enhancementsBranchUrl}
          target="_blank"
          rel="noopener noreferrer"
          title="enhancements branch (dev preview)"
          className="hidden md:flex mx-auto mb-2 h-8 w-8 items-center justify-center rounded-lg border border-amber-400/30 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20"
        >
          <GitBranch className="w-4 h-4" />
        </a>
      )}

      {/* Footer */}
      <div className={cn('py-3 border-t border-white/10 space-y-0.5', collapsed ? 'md:px-2 md:space-y-1' : 'px-3')}>
        <a
          href="https://thelearningproject.in"
          target="_blank"
          rel="noopener noreferrer"
          title="Back to homepage"
          className={cn(
            'flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-white/60 hover:bg-white/10 hover:text-white transition-colors no-underline',
            collapsed && 'md:justify-center md:p-2 md:gap-0 md:px-2',
          )}
        >
          <House className="w-4 h-4 flex-shrink-0" />
          <span className={cn(collapsed && 'md:hidden')}>Back to homepage</span>
        </a>

        <Link
          to="/about"
          title="About Rovr"
          className={cn(
            'flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-white/60 hover:bg-white/10 hover:text-white transition-colors no-underline',
            collapsed && 'md:justify-center md:p-2 md:gap-0 md:px-2',
          )}
        >
          <Info className="w-4 h-4 flex-shrink-0" />
          <span className={cn(collapsed && 'md:hidden')}>About Rovr</span>
        </Link>

        {session?.is_admin && (
          <Link
            to="/admin"
            title="Admin"
            className={cn(
              'flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-white/60 hover:bg-white/10 hover:text-white transition-colors no-underline',
              collapsed && 'md:justify-center md:p-2 md:gap-0 md:px-2',
            )}
          >
            <Settings className="w-4 h-4 flex-shrink-0" />
            <span className={cn(collapsed && 'md:hidden')}>Admin</span>
          </Link>
        )}
      </div>
    </aside>
    </>
  )
}
