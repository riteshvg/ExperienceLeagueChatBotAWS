import { useState } from 'react'
import { ChevronDown, ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'
import { type Citation, type RetrievalEvidence } from '@/lib/api'
import { trackCitationClick } from '@/analytics'

interface Props {
  evidence?: RetrievalEvidence
  citations?: Citation[]
  followUps?: string[]
  onFollowUpClick: (text: string) => void
  turnNumber?: number
}

type Expanded = 'sources' | 'followups' | null

function ConfidenceBar({ score }: { score: number }) {
  const pct = Math.min(100, Math.max(0, Math.round(score * 100)))
  return (
    <div
      className="flex-shrink-0 w-16 h-1.5 rounded-full bg-slate-100 overflow-hidden"
      title={`${pct}% match`}
      aria-label={`${pct}% confidence`}
    >
      <div className="h-full rounded-full bg-slate-400 transition-all" style={{ width: `${pct}%` }} />
    </div>
  )
}

export function MessageExtras({
  evidence,
  citations,
  followUps,
  onFollowUpClick,
  turnNumber = 0,
}: Props) {
  const [expanded, setExpanded] = useState<Expanded>(null)

  const evidenceSources = evidence?.sources ?? []
  const citationSources = citations ?? []
  const hasEvidence = !!evidence && (evidenceSources.length > 0 || evidence.banner || evidence.failure_reason)
  const hasCitations = !evidence && citationSources.length > 0
  const hasSources = hasEvidence || hasCitations
  const sourceCount = evidence
    ? evidence.source_count || evidenceSources.length
    : citationSources.length
  const hasFollowUps = (followUps?.length ?? 0) > 0

  if (!hasSources && !hasFollowUps) return null

  const toggle = (section: Expanded) => {
    setExpanded((current) => (current === section ? null : section))
  }

  return (
    <div className="w-full text-xs">
      <div className="flex items-stretch border border-slate-200 rounded-lg bg-white overflow-hidden">
        {hasSources && (
          <button
            type="button"
            onClick={() => toggle('sources')}
            className={cn(
              'flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-slate-500 hover:bg-slate-50 transition-colors',
              expanded === 'sources' && 'bg-slate-50 text-slate-700',
            )}
          >
            <span>Sources{sourceCount > 0 ? ` · ${sourceCount}` : ''}</span>
            <ChevronDown
              className={cn('w-3 h-3 text-slate-400 transition-transform', expanded === 'sources' && 'rotate-180')}
            />
          </button>
        )}
        {hasSources && hasFollowUps && <div className="w-px bg-slate-200 self-stretch" />}
        {hasFollowUps && (
          <button
            type="button"
            onClick={() => toggle('followups')}
            className={cn(
              'flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-slate-500 hover:bg-slate-50 transition-colors',
              expanded === 'followups' && 'bg-slate-50 text-slate-700',
            )}
          >
            <span>Follow-ups · {followUps!.length}</span>
            <ChevronDown
              className={cn('w-3 h-3 text-slate-400 transition-transform', expanded === 'followups' && 'rotate-180')}
            />
          </button>
        )}
      </div>

      {expanded === 'sources' && (
        <div className="mt-1 border border-slate-200 rounded-lg bg-white overflow-hidden">
          {evidence?.banner && (
            <p className="px-3 py-2 text-[11px] leading-relaxed text-slate-500 border-b border-slate-100">
              {evidence.banner}
            </p>
          )}
          {evidenceSources.length > 0 ? (
            <ul className="divide-y divide-slate-100">
              {evidenceSources.map((src, i) => (
                <li key={src.url}>
                  <a
                    href={src.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    title={src.title}
                    onClick={() => trackCitationClick(src.url, src.title || '', turnNumber)}
                    className="flex items-center gap-2 px-3 py-2 hover:bg-slate-50 transition-colors no-underline group"
                  >
                    <span className="flex-shrink-0 w-4 h-4 rounded-full bg-slate-50 border border-slate-200 flex items-center justify-center text-[10px] font-bold text-slate-500">
                      {i + 1}
                    </span>
                    <span className="flex-1 min-w-0">
                      <span className="block text-slate-700 font-medium truncate group-hover:text-slate-900">
                        {src.title || src.product || 'Documentation'}
                      </span>
                      {src.product && (
                        <span className="block text-[10px] text-slate-400 truncate">{src.product}</span>
                      )}
                    </span>
                    {src.score !== undefined && <ConfidenceBar score={src.score} />}
                    <ExternalLink className="w-3 h-3 flex-shrink-0 text-slate-300 group-hover:text-slate-500" />
                  </a>
                </li>
              ))}
            </ul>
          ) : citationSources.length > 0 ? (
            <ul className="divide-y divide-slate-100">
              {citationSources.map((c, i) => (
                <li key={c.url}>
                  <a
                    href={c.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    title={c.title}
                    onClick={() => trackCitationClick(c.url, c.title || '', turnNumber)}
                    className="flex items-center gap-2 px-3 py-2 hover:bg-slate-50 transition-colors no-underline group"
                  >
                    <span className="flex-shrink-0 w-4 h-4 rounded-full bg-slate-50 border border-slate-200 flex items-center justify-center text-[10px] font-bold text-slate-500">
                      {i + 1}
                    </span>
                    <span className="flex-1 min-w-0 text-slate-700 font-medium truncate group-hover:text-slate-900">
                      {c.title || c.product || 'Documentation'}
                    </span>
                    <ExternalLink className="w-3 h-3 flex-shrink-0 text-slate-300 group-hover:text-slate-500" />
                  </a>
                </li>
              ))}
            </ul>
          ) : (
            <p className="px-3 py-2 text-slate-400">No sources available.</p>
          )}
        </div>
      )}

      {expanded === 'followups' && hasFollowUps && (
        <ul className="mt-1 border border-slate-200 rounded-lg bg-white divide-y divide-slate-100 overflow-hidden">
          {followUps!.map((q, idx) => (
            <li key={idx}>
              <button
                type="button"
                onClick={() => onFollowUpClick(q)}
                className="w-full text-left px-3 py-2 text-slate-600 hover:bg-slate-50 hover:text-slate-800 transition-colors"
              >
                {q}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
