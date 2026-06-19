import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Play, Copy, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { MessageExtras } from './MessageExtras'
import { type Message } from '@/lib/api'

interface Props {
  message: Message
  onFollowUpClick: (text: string) => void
  turnNumber?: number
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

function stripCitationMarkers(text: string): string {
  return text.replace(/\[\d+\](?!\()/g, '')
}

function stripMdLinks(text: string): string {
  return text
    .replace(/\[([^\]]+)\]\([^)]*\.md[^)]*\)/g, '$1')
    // Strip inline EXL/developer.adobe.com doc links — 404-prone; citations panel handles sources
    .replace(/\[([^\]]+)\]\(https?:\/\/(?:experienceleague|developer)\.adobe\.com[^)]+\)/g, '$1')
}

function CopyAnswerButton({
  copied,
  onCopy,
  className,
}: {
  copied: boolean
  onCopy: () => void
  className?: string
}) {
  return (
    <button
      type="button"
      onClick={onCopy}
      title="Copy answer"
      className={cn(
        'p-1 rounded-md text-slate-300 hover:text-slate-600 hover:bg-slate-100/90 transition-colors',
        className,
      )}
    >
      {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  )
}

export function ChatMessage({ message, onFollowUpClick, turnNumber = 0 }: Props) {
  const isUser = message.role === 'user'
  const [copied, setCopied] = useState(false)
  const displayedContent = useTypewriter(message.content || '', !!message.streaming, 12)
  const processedContent = stripMdLinks(stripCitationMarkers(sanitizeAdobeMarkup(displayedContent || ' ')))

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={cn('flex w-full', isUser ? 'justify-end' : 'justify-start')}>
      <div className={cn('max-w-[85%] space-y-2', isUser ? 'items-end' : 'items-start')}>

        {/* Bubble */}
        <div className={cn(
          'relative px-4 py-3 rounded-2xl text-sm leading-relaxed',
          isUser
            ? 'bg-[#14532D] text-white rounded-br-sm'
            : 'bg-white border border-slate-200 text-slate-800 rounded-bl-sm shadow-sm',
          !isUser && !message.streaming && message.content.trim() && 'pr-10',
        )}>
          {!isUser && !message.streaming && message.content.trim() && (
            <CopyAnswerButton
              copied={copied}
              onCopy={handleCopy}
              className="absolute right-2 top-2"
            />
          )}
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
                {processedContent}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Sources + follow-ups (compact expandable row) */}
        {!isUser && !message.streaming && message.content.trim() && (
          <MessageExtras
            evidence={message.evidence}
            citations={message.citations}
            followUps={message.follow_ups}
            onFollowUpClick={onFollowUpClick}
            turnNumber={turnNumber}
            messageId={message.id}
            feedback={message.feedback}
          />
        )}

      </div>
    </div>
  )
}
