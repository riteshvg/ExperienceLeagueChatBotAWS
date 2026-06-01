import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Play } from 'lucide-react'
import { cn } from '@/lib/utils'
import { CitationCard } from './CitationCard'
import { ModelBadge } from './ModelBadge'
import { type Message } from '@/lib/api'

interface Props {
  message: Message
}

const VIDEO_URL_RE = /video\.tv\.adobe\.com|youtube\.com\/watch|youtu\.be/

// Transform Adobe doc markup into renderable markdown before passing to ReactMarkdown
function sanitizeAdobeMarkup(text: string): string {
  return text
    // [!UICONTROL label] → `label` (inline code renders as a UI badge in prose)
    .replace(/\[!UICONTROL\s+([^\]]+)\]/g, '`$1`')
    // [!DNL product name] → **product name** (bold)
    .replace(/\[!DNL\s+([^\]]+)\]/g, '**$1**')
    // [!IMPORTANT], [!NOTE], [!TIP], [!WARNING] callout blocks → blockquote
    .replace(/>\[!(IMPORTANT|NOTE|TIP|WARNING)\]\s*/g, '> **$1:** ')
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
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  // Render images inline with error fallback
                  img: ({ src, alt }) => {
                    if (!src) return null
                    return (
                      <a href={src} target="_blank" rel="noopener noreferrer" className="block my-3">
                        <img
                          src={src}
                          alt={alt ?? ''}
                          className="rounded-lg border border-slate-200 max-h-64 object-contain w-full"
                          onError={(e) => {
                            (e.currentTarget.closest('a') as HTMLElement).style.display = 'none'
                          }}
                        />
                      </a>
                    )
                  },
                  // Render Adobe video links as inline iframe embeds
                  a: ({ href, children }) => {
                    if (href && VIDEO_URL_RE.test(href)) {
                      const match = href.match(/video\.tv\.adobe\.com\/v\/([^/?]+)/)
                      if (match) {
                        const videoId = match[1]
                        const embedUrl = `https://video.tv.adobe.com/v/${videoId}?autoplay=0&hidetitle=true`
                        const label = String(children).replace(/^▶\s*Watch:\s*/i, '').trim()
                        return (
                          <span className="block my-3 rounded-xl overflow-hidden border border-slate-200 not-prose">
                            {label && (
                              <span className="flex items-center gap-2 px-3 py-2 bg-slate-50 border-b border-slate-200 text-xs font-medium text-slate-600">
                                <Play className="w-3 h-3 text-red-500 fill-red-500 flex-shrink-0" />
                                {label}
                              </span>
                            )}
                            <span className="block relative w-full" style={{ paddingBottom: '56.25%' }}>
                              <iframe
                                src={embedUrl}
                                className="absolute inset-0 w-full h-full"
                                frameBorder="0"
                                allow="autoplay; fullscreen"
                                allowFullScreen
                                title={label || 'Video'}
                              />
                            </span>
                          </span>
                        )
                      }
                    }
                    return (
                      <a href={href} target="_blank" rel="noopener noreferrer">
                        {children}
                      </a>
                    )
                  },
                }}
              >
                {sanitizeAdobeMarkup(message.content || ' ')}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Model badge */}
        {!isUser && message.model && !message.streaming && (
          <div className="flex items-center gap-2 px-1">
            <ModelBadge model={message.model} />
          </div>
        )}

        {/* Source pills */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="w-full space-y-1.5">
            <p className="text-xs text-slate-400 font-medium px-1">Sources</p>
            <div className="flex flex-wrap gap-1.5">
              {message.citations.slice(0, 8).map((c, idx) => (
                <CitationCard key={c.url + idx} citation={c} />
              ))}
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
