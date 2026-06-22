import { useState, useMemo, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Play, Copy, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { MessageExtras } from './MessageExtras'
import { ClarificationCard } from './ClarificationCard'
import { ImageCarousel, type CarouselImage } from './ImageCarousel'
import { type Message } from '@/lib/api'
import { useChatStore } from '@/store/chatStore'

interface Props {
  message: Message
  onFollowUpClick: (text: string) => void
  turnNumber?: number
}

const VIDEO_URL_RE = /video\.tv\.adobe\.com|youtube\.com\/watch|youtu\.be/
const MD_IMAGE_RE = /!\[([^\]]*)\]\(([^)\s"']+)(?:\s+["'][^"']*["'])?\)/g

/** Images in document order; code blocks stripped so inline samples are not counted. */
function extractMarkdownImages(text: string): CarouselImage[] {
  const stripped = text.replace(/```[\s\S]*?```/g, (block) => ' '.repeat(block.length))
  const images: CarouselImage[] = []
  let match: RegExpExecArray | null
  MD_IMAGE_RE.lastIndex = 0
  while ((match = MD_IMAGE_RE.exec(stripped)) !== null) {
    images.push({ alt: match[1], src: match[2] })
  }
  return images
}

function resolveImageIndex(
  images: CarouselImage[],
  preferred: number,
  src: string,
  alt: string,
): number {
  if (images[preferred]?.src === src && images[preferred]?.alt === alt) return preferred
  const found = images.findIndex((img) => img.src === src && img.alt === alt)
  return found >= 0 ? found : preferred
}

/** Fixed-aspect video shell — iframe mounts once and is never torn down on parent re-renders. */
function AdobeVideoEmbed({
  videoId,
  label,
  ready,
}: {
  videoId: string
  label: string
  ready: boolean
}) {
  const latched = useRef(false)
  if (ready) latched.current = true
  const showIframe = latched.current

  const embedUrl = `https://video.tv.adobe.com/v/${videoId}?autoplay=0&hidetitle=true`
  return (
    <span
      className="block my-3 rounded-xl overflow-hidden border border-slate-200 dark:border-slate-700 not-prose w-full max-w-md"
      data-video-id={videoId}
    >
      {label && (
        <span className="flex items-center gap-2 px-3 py-2 bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 text-xs font-medium text-slate-600 dark:text-slate-300">
          <Play className="w-3 h-3 text-red-500 fill-red-500 flex-shrink-0" />
          {label}
        </span>
      )}
      <span className="block relative w-full bg-slate-100 dark:bg-slate-800" style={{ paddingBottom: '56.25%' }}>
        {showIframe ? (
          <iframe
            key={videoId}
            src={embedUrl}
            className="absolute inset-0 w-full h-full"
            frameBorder="0"
            allow="autoplay; fullscreen"
            allowFullScreen
            title={label || 'Video'}
          />
        ) : (
          <span className="absolute inset-0 flex items-center justify-center gap-2 text-xs text-slate-400">
            <Play className="w-4 h-4 text-red-400 fill-red-400 flex-shrink-0" />
            Loading video…
          </span>
        )}
      </span>
    </span>
  )
}

/** Doc screenshots vs small UI icons/buttons from EXL — avoid stretching icons to full bubble width. */
function DocImage({
  src,
  alt,
  onOpen,
}: {
  src: string
  alt: string
  onOpen: () => void
}) {
  const [natural, setNatural] = useState<{ w: number; h: number } | null>(null)

  const altHintsUi =
    /\b(button|icon|click|cta|add service|plus|toggle|checkbox|radio|tab)\b/i.test(alt) ||
    /^\s*\+?\s*$/.test(alt)

  const isSquareIcon =
    natural !== null &&
    Math.abs(natural.w - natural.h) / Math.max(natural.w, natural.h) < 0.12

  const isSmallUi =
    altHintsUi ||
    (natural !== null && natural.w <= 180 && natural.h <= 180) ||
    (isSquareIcon && natural !== null && Math.max(natural.w, natural.h) <= 512)

  const isWideScreenshot =
    natural !== null && natural.w > natural.h * 1.4 && natural.w >= 400

  const sizeClass = isSmallUi
    ? 'max-w-[140px] max-h-[140px]'
    : isWideScreenshot
      ? 'max-w-full max-h-72'
      : 'max-w-md max-h-64'

  return (
    // span (not button) — valid inside markdown <p>; nested <button> breaks DOM for 2+ images
    <span
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onOpen()
        }
      }}
      className="inline-block my-3 max-w-full not-prose cursor-zoom-in"
      title="View in gallery"
    >
      <img
        src={src}
        alt={alt}
        draggable={false}
        className={cn(
          'rounded-lg border border-slate-200 dark:border-slate-600 object-contain w-auto h-auto pointer-events-none hover:border-slate-300 dark:hover:border-slate-500 hover:shadow-sm transition-shadow',
          sizeClass,
        )}
        onLoad={(e) => {
          setNatural({
            w: e.currentTarget.naturalWidth,
            h: e.currentTarget.naturalHeight,
          })
        }}
        onError={(e) => {
          (e.currentTarget.closest('[role="button"]') as HTMLElement).style.display = 'none'
        }}
      />
    </span>
  )
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
        'p-1 rounded-md text-slate-300 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100/90 dark:hover:bg-slate-800/90 transition-colors',
        className,
      )}
    >
      {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  )
}

export function ChatMessage({ message, onFollowUpClick, turnNumber = 0 }: Props) {
  const selectClarification = useChatStore((s) => s.selectClarification)
  const isStreaming = useChatStore((s) => s.isStreaming)
  const isUser = message.role === 'user'
  const isClarificationOnly =
    !isUser && message.model === 'clarification' && !!message.clarification
  const [copied, setCopied] = useState(false)
  const [carousel, setCarousel] = useState<{ images: CarouselImage[]; index: number } | null>(null)
  // Show SSE content as it arrives — typewriter lag caused layout thrash with embedded media.
  const processedContent = stripMdLinks(
    stripCitationMarkers(sanitizeAdobeMarkup(message.content || (isClarificationOnly ? '' : ' '))),
  )

  const embedReady = !message.streaming

  const { markdownComponents } = useMemo(() => {
    const messageImages = extractMarkdownImages(processedContent)
    // React Strict Mode renders markdown twice; reset counter when the second pass starts.
    let nextIndex = 0

    const markdownComponents = {
      img: ({ src, alt }: { src?: string; alt?: string }) => {
        if (!src) return null
        if (nextIndex >= messageImages.length) nextIndex = 0
        const index = nextIndex++
        const altText = alt ?? ''
        return (
          <DocImage
            src={src}
            alt={altText}
            onOpen={() =>
              setCarousel({
                images: messageImages,
                index: resolveImageIndex(messageImages, index, src, altText),
              })
            }
          />
        )
      },
      a: ({ href, children }: { href?: string; children?: React.ReactNode }) => {
        if (href && VIDEO_URL_RE.test(href)) {
          const match = href.match(/video\.tv\.adobe\.com\/v\/([^/?]+)/)
          if (match) {
            const videoId = match[1]
            const label = String(children).replace(/^▶\s*Watch:\s*/i, '').trim()
            return (
              <AdobeVideoEmbed
                videoId={videoId}
                label={label || 'Watch video'}
                ready={embedReady}
              />
            )
          }
        }
        return (
          <a href={href} target="_blank" rel="noopener noreferrer">
            {children}
          </a>
        )
      },
    }

    return { markdownComponents, messageImages }
  }, [embedReady, processedContent])

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={cn('flex w-full', isUser ? 'justify-end' : 'justify-start')}>
      <div className={cn('max-w-[85%] space-y-2', isUser ? 'items-end' : 'items-start')}>

        {/* Bubble — omitted when the response is clarification-only (no answer text yet) */}
        {!isClarificationOnly && (
        <div className={cn(
          'relative px-4 py-3 rounded-2xl text-sm leading-relaxed',
          isUser
            ? 'bg-[#14532D] text-white rounded-br-sm'
            : 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-100 rounded-bl-sm shadow-sm',
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
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                {processedContent}
              </ReactMarkdown>
            </div>
          )}
        </div>
        )}

        {!isUser && message.clarification && message.model === 'clarification' && (
          <ClarificationCard
            clarification={message.clarification}
            disabled={isStreaming}
            onSelect={(option) =>
              selectClarification(option, message.clarification!.original_query)
            }
          />
        )}

        {/* Sources + follow-ups (compact expandable row) */}
        {!isUser && !message.streaming && message.content.trim() && message.model !== 'clarification' && (
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

      {carousel && carousel.images.length > 0 && (
        <ImageCarousel
          images={carousel.images}
          index={carousel.index}
          onClose={() => setCarousel(null)}
          onIndexChange={(index) => setCarousel((prev) => (prev ? { ...prev, index } : null))}
        />
      )}
    </div>
  )
}
