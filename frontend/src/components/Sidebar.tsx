import { MessageSquare, Plus, Settings } from 'lucide-react'
import { Link } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { type Message } from '@/lib/api'

interface Props {
  messages: Message[]
  onNewChat: () => void
}

function previewText(messages: Message[]): string {
  const first = messages.find((m) => m.role === 'user')
  if (!first) return 'New chat'
  return first.content.slice(0, 40) + (first.content.length > 40 ? '…' : '')
}

export function Sidebar({ messages, onNewChat }: Props) {
  const hasMessages = messages.length > 0

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
          onClick={onNewChat}
          className={cn(
            'w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm',
            'text-slate-300 hover:bg-slate-700 hover:text-white transition-colors',
          )}
        >
          <Plus className="w-4 h-4" />
          New chat
        </button>
      </div>

      {/* Current conversation preview */}
      {hasMessages && (
        <div className="px-3 pb-2">
          <p className="text-xs text-slate-500 uppercase tracking-wider px-3 mb-1">Current</p>
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-700/50 text-sm text-slate-200">
            <MessageSquare className="w-4 h-4 flex-shrink-0 text-slate-400" />
            <span className="truncate">{previewText(messages)}</span>
          </div>
        </div>
      )}

      <div className="flex-1" />

      {/* Footer */}
      <div className="px-3 py-3 border-t border-slate-700">
        <Link
          to="/admin"
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-slate-400 hover:bg-slate-700 hover:text-white transition-colors no-underline"
        >
          <Settings className="w-4 h-4" />
          Admin
        </Link>
      </div>
    </aside>
  )
}
