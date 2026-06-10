import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Play, Copy, Check, ThumbsUp, ThumbsDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { CitationCard } from './CitationCard'
import { ModelBadge } from './ModelBadge'
import { useChatStore } from '@/store/chatStore'
import { type Message } from '@/lib/api'

interface Props {
  message: Message
  onFollowUpClick: (text: string) => void
}

const VIDEO_URL_RE = /video\.tv\.adobe\.com|youtube\.com\/watch|youtu\.be/

/** Typewriter effect — reveals text character by character while streaming. */
function useTypewriter(fullText: string, isStreaming: boolean, speed = 8): string {
  const [displayed, setDisplayed] = useState('')
  const posRef = useRef(0)
  const textRef = useRef(fullText)
  textRef.current = fullText   // always current without re-triggering effects

  useEffect(() => {
    if (!isStreaming) {
      // Streaming finished — show everything immediately
      setDisplayed(textRef.current)
      posRef.current = textRef.current.length
      return
    }
    // Reset and start typewriter
    posRef.current = 0
    setDisplayed('')
    const interval = setInterval(() => {
      if (posRef.current < textRef.current.length) {
        posRef.current += 1
        setDisplayed(textRef.current.slice(0, posRef.current))
      }
    }, speed)
    return () => clearInterval(interval)
  }, [isStreaming, speed])

  return displayed
}

function sanitizeAdobeMarkup(text: string): string {
  return text
    .replace(/\[!UICONTROL\s+([^\]]+)\]/g, '`$1`')
    .replace(/\[!DNL\s+([^\]]+)\]/g, '**$1**')
    .replace(/>\[!(IMPORTANT|NOTE|TIP|WARNING)\]\s*/g, '> **$1:** ')
}

/** Replace [N] citation markers with markdown links the custom `a` renderer can intercept. */
function injectCitationLinks(text: string, citations: Message['citations']): string {
  if (!citations || citations.length === 0) return text
  return text.replace(/\[(\d+)\](?!\()/g, (match, n) => {
    const idx = parseInt(n, 10) - 1
    if (idx >= 0 && idx < citations.length) {
      return `[${n}](#cite-${n})`
    }
    return match
  })
}

function ConfidenceBadge({ citations }: { citations: Message['citations'] }) {
  if (!citations || citations.length === 0) return null
  const scores = citations
    .map((c) => c.score ?? 0)
    .filter((s) => s > 0)
    .sort((a, b) => b - a)
    .slice(0, 3)
  if (scores.length === 0) return null
  const avg = scores.reduce((a, b) => a + b, 0) / scores.length

  const label = avg >= 0.70 ? 'High' : avg >= 0.50 ? 'Medium' : 'Low'
  const cls = avg >= 0.70
    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
    : avg >= 0.50
    ? 'bg-amber-50 text-amber-700 border-amber-200'
    : 'bg-orange-50 text-orange-700 border-orange-200'

  return (
    <span className={cn('inline-flex items-center px-2 py-0.5 rounded-full text-xs border font-medium', cls)}>
      {label} confidence
    </span>
  )
}

export function ChatMessage({ message, onFollowUpClick }: Props) {
  const isUser = message.role === 'user'
  const [copied, setCopied] = useState(false)
  const { setFeedback } = useChatStore()
  const displayedContent = useTypewriter(message.content || '', !!message.streaming, 12)

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleFeedback = (rating: 1 | -1) => {
    if (message.feedback !== undefined) return
    setFeedback(message.id, rating, '')  // query resolved in store from preceding message
  }

  return (
    <div className={cn('flex w-full', isUser ? 'justify-end' : 'justify-start')}>
      <div className={cn('max-w-[85%] space-y-2', isUser ? 'items-end' : 'items-start')}>

        {/* Bubble */}
        <div className={cn(
          'px-4 py-3 rounded-2xl text-sm leading-relaxed',
          isUser
            ? 'bg-blue-600 text-white rounded-br-sm'
            : 'bg-white border border-slate-200 text-slate-800 rounded-bl-sm shadow-sm',
        )}>
          {isUser ? (
            <p>{message.content}</p>
          ) : (
            <div className={cn('prose prose-sm max-w-none', message.streaming && 'streaming-cursor')}>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
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
                  a: ({ href, children }) => {
                    // Inline citation superscript — [N] rendered as a linked superscript
                    if (href?.startsWith('#cite-')) {
                      const n = parseInt(href.slice(6), 10)
                      const citation = message.citations?.[n - 1]
                      if (citation?.url) {
                        return (
                          <sup>
                            <a
                              href={citation.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              title={citation.title}
                              className="text-indigo-500 hover:text-indigo-700 font-semibold no-underline"
                            >
                              [{n}]
                            </a>
                          </sup>
                        )
                      }
                      return <sup className="text-slate-400 font-medium">[{n}]</sup>
                    }
                    if (href && VIDEO_URL_RE.test(href)) {
                      const match = href.match(/video\.tv\.adobe\.com\/v\/([^/?]+)/)
                      if (match) {
                        const videoId = match[1]
                        const label = String(children).replace(/^▶\s*Watch:\s*/i, '').trim()
                        if (message.streaming) {
                          return (
                            <span className="inline-flex items-center gap-2 my-1 px-3 py-1.5 rounded-lg
                              bg-slate-50 border border-slate-200 text-xs font-medium text-slate-500 not-prose">
                              <Play className="w-3 h-3 text-red-400 fill-red-400 flex-shrink-0" />
                              <span>{label || 'Watch video'}</span>
                            </span>
                          )
                        }
                        const embedUrl = `https://video.tv.adobe.com/v/${videoId}?autoplay=0&hidetitle=true`
                        return (
                          <span className="block my-3 rounded-xl overflow-hidden border border-slate-200 not-prose w-1/2">
                            {label && (
                              <span className="flex items-center gap-2 px-3 py-2 bg-slate-50 border-b border-slate-200 text-xs font-medium text-slate-600">
                                <Play className="w-3 h-3 text-red-500 fill-red-500 flex-shrink-0" />
                                {label}
                              </span>
                            )}
                            <span className="block relative w-full" style={{ paddingBottom: '56.25%' }}>
                              <iframe src={embedUrl} className="absolute inset-0 w-full h-full"
                                frameBorder="0" allow="autoplay; fullscreen" allowFullScreen title={label || 'Video'} />
                            </span>
                          </span>
                        )
                      }
                    }
                    return <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>
                  },
                }}
              >
                {injectCitationLinks(sanitizeAdobeMarkup(displayedContent || ' '), message.citations)}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Footer row: model badge + confidence + feedback + copy */}
        {!isUser && message.model && !message.streaming && (
          <div className="flex items-center gap-2 px-1 flex-wrap">
            <ModelBadge model={message.model} />
            <ConfidenceBadge citations={message.citations} />
            <div className="flex-1" />
            {/* Feedback */}
            <button
              onClick={() => handleFeedback(1)}
              title="Helpful"
              className={cn(
                'p-1 rounded-md transition-colors',
                message.feedback === 1
                  ? 'text-emerald-600 bg-emerald-50'
                  : 'text-slate-300 hover:text-emerald-500 hover:bg-emerald-50',
              )}
            >
              <ThumbsUp className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => handleFeedback(-1)}
              title="Not helpful"
              className={cn(
                'p-1 rounded-md transition-colors',
                message.feedback === -1
                  ? 'text-red-500 bg-red-50'
                  : 'text-slate-300 hover:text-red-400 hover:bg-red-50',
              )}
            >
              <ThumbsDown className="w-3.5 h-3.5" />
            </button>
            {/* Copy */}
            <button
              onClick={handleCopy}
              title="Copy answer"
              className="p-1 rounded-md text-slate-300 hover:text-slate-600 hover:bg-slate-100 transition-colors"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
        )}

        {/* Source pills */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="w-full space-y-1.5">
            <p className="text-xs text-slate-400 font-medium px-1">Sources</p>
            <div className="flex flex-wrap gap-1.5">
              {message.citations.slice(0, 8).map((c, idx) => (
                <CitationCard key={c.url + idx} citation={c} index={idx + 1} />
              ))}
            </div>
          </div>
        )}

        {/* Follow-up suggestions */}
        {!isUser && message.follow_ups && message.follow_ups.length > 0 && !message.streaming && (
          <div className="w-full space-y-1.5">
            <p className="text-xs text-slate-400 font-medium px-1">Follow-up questions</p>
            <div className="flex flex-col gap-1.5">
              {message.follow_ups.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => onFollowUpClick(q)}
                  className="text-left px-3 py-2 rounded-xl border border-slate-200 bg-white text-xs
                    text-slate-600 hover:border-blue-300 hover:text-blue-700 hover:bg-blue-50
                    transition-colors w-full"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
