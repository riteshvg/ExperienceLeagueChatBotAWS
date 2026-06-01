import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { cn } from '@/lib/utils'
import { CitationCard } from './CitationCard'
import { ModelBadge } from './ModelBadge'
import { type Message } from '@/lib/api'

interface Props {
  message: Message
}

export function ChatMessage({ message }: Props) {
  const isUser = message.role === 'user'

  return (
    <div className={cn('flex w-full', isUser ? 'justify-end' : 'justify-start')}>
      <div className={cn('max-w-[85%] space-y-2', isUser ? 'items-end' : 'items-start')}>
        {/* Bubble */}
        <div
          className={cn(
            'px-4 py-3 rounded-2xl text-sm leading-relaxed',
            isUser
              ? 'bg-blue-600 text-white rounded-br-sm'
              : 'bg-white border border-slate-200 text-slate-800 rounded-bl-sm shadow-sm',
          )}
        >
          {isUser ? (
            <p>{message.content}</p>
          ) : (
            <div className={cn('prose prose-sm max-w-none', message.streaming && 'streaming-cursor')}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content || ' '}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Footer: model badge */}
        {!isUser && message.model && !message.streaming && (
          <div className="flex items-center gap-2 px-1">
            <ModelBadge model={message.model} />
          </div>
        )}

        {/* Citations */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="w-full space-y-1">
            <p className="text-xs text-slate-400 font-medium px-1">Sources</p>
            <div className="grid grid-cols-1 gap-1.5">
              {message.citations.slice(0, 5).map((c, i) => (
                <CitationCard key={c.url + i} citation={c} index={i} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
