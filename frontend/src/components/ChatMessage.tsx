import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { cn } from '@/lib/utils'
import { CitationCard } from './CitationCard'
import { VideoCard } from './VideoCard'
import { ModelBadge } from './ModelBadge'
import { type Message } from '@/lib/api'

interface Props {
  message: Message
}

export function ChatMessage({ message }: Props) {
  const isUser = message.role === 'user'

  const docCitations = message.citations?.filter((c) => !c.video_url) ?? []
  const videoCitations = message.citations?.filter((c) => !!c.video_url) ?? []

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
            <>
              {/* Answer text */}
              <div className={cn('prose prose-sm max-w-none', message.streaming && 'streaming-cursor')}>
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    img: ({ alt }) => alt
                      ? <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-slate-100 text-slate-500 font-medium">{alt}</span>
                      : null,
                  }}
                >
                  {message.content || ' '}
                </ReactMarkdown>
              </div>

              {/* Related Videos — inside the bubble, below the text */}
              {videoCitations.length > 0 && !message.streaming && (
                <div className="mt-4 pt-3 border-t border-slate-100 space-y-2">
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Related Videos</p>
                  <div className="flex gap-3 overflow-x-auto pb-1 -mx-1 px-1">
                    {videoCitations.slice(0, 4).map((c, idx) => (
                      <VideoCard key={c.url + idx} citation={c} />
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Model badge */}
        {!isUser && message.model && !message.streaming && (
          <div className="flex items-center gap-2 px-1">
            <ModelBadge model={message.model} />
          </div>
        )}

        {/* Source pills */}
        {!isUser && docCitations.length > 0 && (
          <div className="w-full space-y-1.5">
            <p className="text-xs text-slate-400 font-medium px-1">Sources</p>
            <div className="flex flex-wrap gap-1.5">
              {docCitations.slice(0, 8).map((c, idx) => (
                <CitationCard key={c.url + idx} citation={c} />
              ))}
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
