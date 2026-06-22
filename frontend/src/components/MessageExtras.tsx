import { useState } from 'react'
import { ChevronDown, ExternalLink, ThumbsDown, ThumbsUp } from 'lucide-react'
import { cn } from '@/lib/utils'
import { type Citation, type RetrievalEvidence } from '@/lib/api'
import { trackCitationClick } from '@/analytics'
import { useChatStore } from '@/store/chatStore'

interface Props {
  evidence?: RetrievalEvidence
  citations?: Citation[]
  followUps?: string[]
  onFollowUpClick: (text: string) => void
  turnNumber?: number
  messageId: string
  feedback?: 1 | -1
}

type Expanded = 'sources' | 'followups' | null

const MAX_COMMENT = 500

function ConfidenceBar({ score }: { score: number }) {
  const pct = Math.min(100, Math.max(0, Math.round(score * 100)))
  return (
    <div
      className="flex-shrink-0 w-16 h-1.5 rounded-full bg-emerald-100 dark:bg-emerald-900/60 overflow-hidden"
      title={`${pct}% match`}
      aria-label={`${pct}% confidence`}
    >
      <div className="h-full rounded-full bg-emerald-500/60 dark:bg-emerald-400/70 transition-all" style={{ width: `${pct}%` }} />
    </div>
  )
}

const tabBtn = (active: boolean) =>
  cn(
    'flex-1 flex items-center justify-center gap-1.5 px-3 py-2 transition-colors',
    'text-emerald-800/70 hover:bg-emerald-100/80',
    'dark:text-emerald-100 dark:hover:bg-slate-800',
    active && 'bg-emerald-100/90 text-emerald-900 dark:bg-slate-800 dark:text-slate-100',
  )

const tabChevron = (active: boolean) =>
  cn(
    'w-3 h-3 transition-transform',
    'text-emerald-600/60 dark:text-emerald-300/80',
    active && 'rotate-180',
  )

export function MessageExtras({
  evidence,
  citations,
  followUps,
  onFollowUpClick,
  turnNumber = 0,
  messageId,
  feedback,
}: Props) {
  const [expanded, setExpanded] = useState<Expanded>(null)
  const [showFeedbackInput, setShowFeedbackInput] = useState(false)
  const [feedbackComment, setFeedbackComment] = useState('')
  const { setFeedback } = useChatStore()

  const evidenceSources = evidence?.sources ?? []
  const citationSources = citations ?? []
  const hasEvidence = !!evidence && (evidenceSources.length > 0 || evidence.banner || evidence.failure_reason)
  const hasCitations = !evidence && citationSources.length > 0
  const hasSources = hasEvidence || hasCitations
  const sourceCount = evidence ? evidenceSources.length : citationSources.length
  const hasFollowUps = (followUps?.length ?? 0) > 0
  const feedbackLocked = feedback !== undefined

  const toggle = (section: Expanded) => {
    setExpanded((current) => (current === section ? null : section))
  }

  const handleFeedback = (rating: 1 | -1) => {
    if (feedbackLocked) return
    if (rating === -1) {
      setShowFeedbackInput(true)
    } else {
      setFeedback(messageId, rating, '')
    }
  }

  const handleSubmitFeedback = () => {
    setFeedback(messageId, -1, '', feedbackComment.trim())
    setShowFeedbackInput(false)
  }

  const handleSkipFeedback = () => {
    setFeedback(messageId, -1, '', '')
    setShowFeedbackInput(false)
  }

  return (
    <div className="w-full text-xs">
      <div className="rounded-lg border border-emerald-200/80 dark:border-emerald-700/80 bg-emerald-50/90 dark:bg-slate-900 overflow-hidden shadow-sm">
        <div className="flex items-stretch">
          {hasSources && (
            <button
              type="button"
              onClick={() => toggle('sources')}
              className={tabBtn(expanded === 'sources')}
            >
              <span>Sources{sourceCount > 0 ? ` · ${sourceCount}` : ''}</span>
              <ChevronDown className={tabChevron(expanded === 'sources')} />
            </button>
          )}
          {hasSources && hasFollowUps && <div className="w-px bg-emerald-200/80 dark:bg-emerald-700/60 self-stretch" />}
          {hasFollowUps && (
            <button
              type="button"
              onClick={() => toggle('followups')}
              className={tabBtn(expanded === 'followups')}
            >
              <span>Follow-ups · {followUps!.length}</span>
              <ChevronDown className={tabChevron(expanded === 'followups')} />
            </button>
          )}
          {(hasSources || hasFollowUps) && (
            <div className="w-px bg-emerald-200/80 dark:bg-emerald-700/60 self-stretch" />
          )}
          <div className="flex items-center gap-0.5 px-2 py-1.5 flex-shrink-0">
            <button
              type="button"
              onClick={() => handleFeedback(1)}
              title="Helpful"
              disabled={feedbackLocked}
              className={cn(
                'p-1.5 rounded-md transition-colors',
                feedback === 1
                  ? 'text-emerald-700 bg-emerald-100 dark:text-emerald-200 dark:bg-emerald-900/70'
                  : 'text-emerald-600/50 hover:text-emerald-700 hover:bg-emerald-100/80 dark:text-emerald-300/70 dark:hover:text-emerald-100 dark:hover:bg-emerald-900/50 disabled:cursor-default',
              )}
            >
              <ThumbsUp className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => handleFeedback(-1)}
              title="Not helpful"
              disabled={feedbackLocked}
              className={cn(
                'p-1.5 rounded-md transition-colors',
                feedback === -1
                  ? 'text-red-600 bg-red-50 dark:text-red-300 dark:bg-red-950/50'
                  : 'text-emerald-600/50 hover:text-red-500 hover:bg-red-50/80 dark:text-emerald-300/70 dark:hover:text-red-300 dark:hover:bg-red-950/40 disabled:cursor-default',
              )}
            >
              <ThumbsDown className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {showFeedbackInput && !feedbackLocked && (
          <div className="px-3 py-2 border-t border-emerald-200/80 dark:border-emerald-800 bg-white/70 dark:bg-slate-900/80">
            <textarea
              autoFocus
              value={feedbackComment}
              onChange={(e) => setFeedbackComment(e.target.value.slice(0, MAX_COMMENT))}
              placeholder="What was wrong with this answer? (optional)"
              rows={2}
              className="w-full text-xs text-slate-700 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 border border-emerald-200/80 dark:border-emerald-800 rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-1 focus:ring-emerald-300 bg-white dark:bg-slate-800"
            />
            <div className="flex items-center justify-between mt-1.5">
              <span className="text-[10px] text-emerald-700/60 dark:text-emerald-300/70">{feedbackComment.length} / {MAX_COMMENT}</span>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handleSkipFeedback}
                  className="text-xs px-2.5 py-1 rounded-md border border-emerald-200/80 dark:border-emerald-700 text-emerald-800/70 dark:text-emerald-200 hover:bg-emerald-50 dark:hover:bg-emerald-900/50 transition-colors"
                >
                  Skip
                </button>
                <button
                  type="button"
                  onClick={handleSubmitFeedback}
                  className="text-xs px-2.5 py-1 rounded-md bg-emerald-800 text-white hover:bg-emerald-700 transition-colors"
                >
                  Submit
                </button>
              </div>
            </div>
          </div>
        )}

        {expanded === 'sources' && (
          <div className="border-t border-emerald-200/80 dark:border-emerald-700/80 bg-white/80 dark:bg-slate-900 overflow-hidden">
            {evidence?.banner && (
              <p className="px-3 py-2 text-[11px] leading-relaxed text-emerald-900/60 dark:text-emerald-200/80 border-b border-emerald-100 dark:border-emerald-800">
                {evidence.banner}
              </p>
            )}
            {evidenceSources.length > 0 ? (
              <ul className="divide-y divide-emerald-100/80 dark:divide-emerald-800/80">
                {evidenceSources.map((src, i) => (
                  <li key={src.url}>
                    <a
                      href={src.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      title={src.title}
                      onClick={() => trackCitationClick(src.url, src.title || '', turnNumber)}
                      className="flex items-center gap-2 px-3 py-2 hover:bg-emerald-50/80 dark:hover:bg-slate-800 transition-colors no-underline group"
                    >
                      <span className="flex-shrink-0 w-4 h-4 rounded-full bg-emerald-50 dark:bg-emerald-900/60 border border-emerald-200 dark:border-emerald-700 flex items-center justify-center text-[10px] font-bold text-emerald-700/70 dark:text-emerald-200">
                        {i + 1}
                      </span>
                      <span className="flex-1 min-w-0">
                        <span className="block text-slate-700 dark:text-slate-200 font-medium truncate group-hover:text-slate-900 dark:group-hover:text-white">
                          {src.title || src.product || 'Documentation'}
                        </span>
                        {src.product && (
                          <span className="block text-[10px] text-slate-400 dark:text-slate-500 truncate">{src.product}</span>
                        )}
                      </span>
                      {src.score !== undefined && <ConfidenceBar score={src.score} />}
                      <ExternalLink className="w-3 h-3 flex-shrink-0 text-emerald-400/60 dark:text-emerald-400/80 group-hover:text-emerald-600 dark:group-hover:text-emerald-300" />
                    </a>
                  </li>
                ))}
              </ul>
            ) : citationSources.length > 0 ? (
              <ul className="divide-y divide-emerald-100/80 dark:divide-emerald-800/80">
                {citationSources.map((c, i) => (
                  <li key={c.url}>
                    <a
                      href={c.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      title={c.title}
                      onClick={() => trackCitationClick(c.url, c.title || '', turnNumber)}
                      className="flex items-center gap-2 px-3 py-2 hover:bg-emerald-50/80 dark:hover:bg-slate-800 transition-colors no-underline group"
                    >
                      <span className="flex-shrink-0 w-4 h-4 rounded-full bg-emerald-50 dark:bg-emerald-900/60 border border-emerald-200 dark:border-emerald-700 flex items-center justify-center text-[10px] font-bold text-emerald-700/70 dark:text-emerald-200">
                        {i + 1}
                      </span>
                      <span className="flex-1 min-w-0 text-slate-700 dark:text-slate-200 font-medium truncate group-hover:text-slate-900 dark:group-hover:text-white">
                        {c.title || c.product || 'Documentation'}
                      </span>
                      <ExternalLink className="w-3 h-3 flex-shrink-0 text-emerald-400/60 dark:text-emerald-400/80 group-hover:text-emerald-600 dark:group-hover:text-emerald-300" />
                    </a>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="px-3 py-2 text-emerald-800/50 dark:text-emerald-200/70">No sources available.</p>
            )}
          </div>
        )}

        {expanded === 'followups' && hasFollowUps && (
          <ul className="border-t border-emerald-200/80 dark:border-emerald-700/80 bg-white/80 dark:bg-slate-900 divide-y divide-emerald-100/80 dark:divide-emerald-800/80 overflow-hidden">
            {followUps!.map((q, idx) => (
              <li key={idx}>
                <button
                  type="button"
                  onClick={() => onFollowUpClick(q)}
                  className="w-full text-left px-3 py-2 text-emerald-900/80 dark:text-slate-200 hover:bg-emerald-50/80 dark:hover:bg-slate-800 hover:text-emerald-950 dark:hover:text-white transition-colors"
                >
                  {q}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
