import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Play, Copy, Check, ThumbsUp, ThumbsDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ModelBadge } from './ModelBadge'
import { CitationCard } from './CitationCard'
import { useChatStore } from '@/store/chatStore'
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

export function ChatMessage({ message, onFollowUpClick, turnNumber = 0 }: Props) {
  const isUser = message.role === 'user'
  const [copied, setCopied] = useState(false)
  const [showFeedbackInput, setShowFeedbackInput] = useState(false)
  const [feedbackComment, setFeedbackComment] = useState('')
  const { setFeedback } = useChatStore()
  const displayedContent = useTypewriter(message.content || '', !!message.streaming, 12)
  const processedContent = stripMdLinks(stripCitationMarkers(sanitizeAdobeMarkup(displayedContent || ' ')))

  const MAX_COMMENT = 500

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleFeedback = (rating: 1 | -1) => {
    if (message.feedback !== undefined) return
    if (rating === -1) {
      setShowFeedbackInput(true)
    } else {
      setFeedback(message.id, rating, '')
    }
  }

  const handleSubmitFeedback = () => {
    setFeedback(message.id, -1, '', feedbackComment.trim())
    setShowFeedbackInput(false)
  }

  const handleSkipFeedback = () => {
    setFeedback(message.id, -1, '', '')
    setShowFeedbackInput(false)
  }

  return (
    <div className={cn('flex w-full', isUser ? 'justify-end' : 'justify-start')}>
      <div className={cn('max-w-[85%] space-y-2', isUser ? 'items-end' : 'items-start')}>

        {/* Bubble */}
        <div className={cn(
          'px-4 py-3 rounded-2xl text-sm leading-relaxed',
          isUser
            ? 'bg-[#14532D] text-white rounded-br-sm'
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

        {/* Citations */}
        {!isUser && !message.streaming && message.citations && message.citations.length > 0 && (
          <div className="w-full space-y-1.5">
            <p className="text-xs text-slate-400 font-medium px-1">Sources</p>
            <div className="flex flex-wrap gap-1.5">
              {message.citations.map((c, i) => (
                <CitationCard key={c.url} citation={c} index={i + 1} turnNumber={turnNumber} />
              ))}
            </div>
          </div>
        )}

        {/* Footer row: model badge + feedback + copy */}
        {!isUser && message.model && message.model !== 'none' && !message.streaming && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 px-1 flex-wrap">
              <ModelBadge model={message.model} />
              <div className="flex-1" />
              {/* Feedback */}
              <button
                onClick={() => handleFeedback(1)}
                title="Helpful"
                disabled={message.feedback !== undefined}
                className={cn(
                  'p-1 rounded-md transition-colors',
                  message.feedback === 1
                    ? 'text-emerald-600 bg-emerald-50'
                    : 'text-slate-300 hover:text-emerald-500 hover:bg-emerald-50 disabled:cursor-default',
                )}
              >
                <ThumbsUp className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => handleFeedback(-1)}
                title="Not helpful"
                disabled={message.feedback !== undefined}
                className={cn(
                  'p-1 rounded-md transition-colors',
                  message.feedback === -1
                    ? 'text-red-500 bg-red-50'
                    : 'text-slate-300 hover:text-red-400 hover:bg-red-50 disabled:cursor-default',
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

            {/* Inline negative feedback input */}
            {showFeedbackInput && (
              <div className="px-1">
                <textarea
                  autoFocus
                  value={feedbackComment}
                  onChange={(e) => setFeedbackComment(e.target.value.slice(0, MAX_COMMENT))}
                  placeholder="What was wrong with this answer? (optional)"
                  rows={2}
                  className="w-full text-xs text-slate-700 placeholder-slate-400 border border-slate-200 rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-1 focus:ring-slate-300 bg-white"
                />
                <div className="flex items-center justify-between mt-1">
                  <span className="text-[10px] text-slate-400">{feedbackComment.length} / {MAX_COMMENT}</span>
                  <div className="flex gap-2">
                    <button
                      onClick={handleSkipFeedback}
                      className="text-xs px-2.5 py-1 rounded-md border border-slate-200 text-slate-500 hover:bg-slate-50 transition-colors"
                    >
                      Skip
                    </button>
                    <button
                      onClick={handleSubmitFeedback}
                      className="text-xs px-2.5 py-1 rounded-md bg-slate-800 text-white hover:bg-slate-700 transition-colors"
                    >
                      Submit
                    </button>
                  </div>
                </div>
              </div>
            )}
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
