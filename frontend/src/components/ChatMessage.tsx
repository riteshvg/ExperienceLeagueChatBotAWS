import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Copy, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { MessageExtras } from './MessageExtras'
import { QuestionCard } from './QuestionCard'
import { DocCitationCard } from './DocCitationCard'
import { TeachingNudge } from './TeachingNudge'
import { DeepenRow } from './DeepenRow'
import {
  parseDeepenActions,
  parseDocCitation,
  parseDomainProgress,
  parseQuestionFromMessage,
  parseTeachingNudge,
  parseTeachingPhase,
} from '@/lib/educator-parse'
import type { DeepenAction, QuestionRecord } from '@/types/educator'
import { type Message } from '@/lib/api'

interface Props {
  message: Message
  onFollowUpClick: (text: string) => void
  turnNumber?: number
  educatorActive?: boolean
  educatorDisabled?: boolean
  questionRecord?: QuestionRecord
  onEducatorAnswer?: (answer: string) => void
  onEducatorHint?: () => void
  onEducatorDoc?: () => void
  onEducatorSkip?: () => void
  onEducatorDeepen?: (action: DeepenAction) => void
}

function useTypewriter(fullText: string, isStreaming: boolean, speed = 8): string {
  const [displayed, setDisplayed] = useState('')
  const posRef = useRef(0)
  const textRef = useRef(fullText)
  textRef.current = fullText

  useEffect(() => {
    if (!isStreaming) {
      setDisplayed(textRef.current)
      posRef.current = textRef.current.length
      return
    }
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

function stripEducatorStructuredBlocks(text: string): string {
  return text
    .replace(/\*\*Question\s+\d+\*\*[\s\S]*?(?=\n\n|\*\*hint\*\*|\*\*Attempt|\*\*Nailed|\*\*Got it|\*\*There we go|$)/i, '')
    .replace(/\*\*doc-preview\*\*[^\n]*/gi, '')
    .replace(/\*\*doc-citation\*\*[^\n]*/gi, '')
    .replace(/\*\*hint\*\*[^\n]*/gi, '')
    .replace(/\*\*think about this\*\*[^\n]*/gi, '')
    .replace(/\*\*let's work through it\*\*[^\n]*/gi, '')
    .replace(/\[Give me a hint\][^\n]*/gi, '')
    .replace(/\[Show me the doc first\][^\n]*/gi, '')
    .replace(/\[([^\]]+?) ↗\]\(#deepen:[^)]+\)/gi, '')
    .replace(/\*\*Domain progress\*\*[^\n]*/gi, '')
}

function stripMdLinks(text: string): string {
  return text
    .replace(/\[([^\]]+)\]\([^)]*\.md[^)]*\)/g, '$1')
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

export function ChatMessage({
  message,
  onFollowUpClick,
  turnNumber = 0,
  educatorActive = false,
  educatorDisabled = false,
  questionRecord,
  onEducatorAnswer,
  onEducatorHint,
  onEducatorDoc,
  onEducatorSkip,
  onEducatorDeepen,
}: Props) {
  const isUser = message.role === 'user'
  const [copied, setCopied] = useState(false)
  const displayedContent = useTypewriter(message.content || '', !!message.streaming, 12)
  const rawContent = displayedContent || ' '
  const processedContent = stripMdLinks(
    stripCitationMarkers(sanitizeAdobeMarkup(stripEducatorStructuredBlocks(rawContent))),
  )

  const parsedQuestion =
    educatorActive && !isUser && !message.streaming ? parseQuestionFromMessage(message.content) : null

  const attemptCount = questionRecord?.attempts.length ?? 0
  const phase = educatorActive && !isUser ? parseTeachingPhase(message.content, attemptCount) : 'posed'
  const nudge = !isUser ? parseTeachingNudge(message.content) : null
  const docPreview = !isUser ? parseDocCitation(message.content, 'preview') : null
  const docCitation = !isUser ? parseDocCitation(message.content, 'citation') : null
  const deepenActions = !isUser && phase === 'correct' ? parseDeepenActions(message.content) : []
  const domainProgress = !isUser ? parseDomainProgress(message.content) : null

  const wrongSelections =
    questionRecord?.attempts.filter((a) => !a.correct).map((a) => a.answer) ?? []

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={cn('flex w-full', isUser ? 'justify-end' : 'justify-start')}>
      <div className={cn('max-w-[85%] space-y-2', isUser ? 'items-end' : 'items-start')}>
        <div
          className={cn(
            'relative px-4 py-3 rounded-2xl text-sm leading-relaxed',
            isUser
              ? 'bg-[#14532D] text-white rounded-br-sm'
              : 'bg-white border border-slate-200 text-slate-800 rounded-bl-sm shadow-sm',
            !isUser && !message.streaming && message.content.trim() && 'pr-10',
          )}
        >
          {!isUser && !message.streaming && message.content.trim() && (
            <CopyAnswerButton copied={copied} onCopy={handleCopy} className="absolute right-2 top-2" />
          )}
          {isUser ? (
            <p>{message.content}</p>
          ) : (
            <div className={cn('prose prose-sm max-w-none', message.streaming && 'streaming-cursor')}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{processedContent}</ReactMarkdown>
            </div>
          )}

          {docPreview && <DocCitationCard citation={docPreview} variant="preview" />}
          {nudge && <TeachingNudge type={nudge.type} text={nudge.text} />}
          {docCitation && (phase === 'correct' || phase === 'revealed') && (
            <DocCitationCard citation={docCitation} variant="citation" />
          )}

          {parsedQuestion &&
            onEducatorAnswer &&
            onEducatorHint &&
            onEducatorDoc &&
            onEducatorSkip && (
              <QuestionCard
                question={parsedQuestion}
                phase={phase}
                attemptCount={attemptCount}
                wrongSelections={wrongSelections}
                resolved={questionRecord?.resolved ?? false}
                disabled={educatorDisabled}
                onAnswer={onEducatorAnswer}
                onHint={onEducatorHint}
                onShowDoc={onEducatorDoc}
                onSkip={onEducatorSkip}
                domainProgress={domainProgress ?? undefined}
              />
            )}

          {deepenActions.length > 0 && onEducatorDeepen && (
            <DeepenRow
              actions={deepenActions}
              disabled={educatorDisabled}
              onAction={onEducatorDeepen}
            />
          )}
        </div>

        {!isUser && !message.streaming && message.content.trim() && message.model !== 'educator' && (
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
