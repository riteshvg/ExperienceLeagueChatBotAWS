import { cn } from '@/lib/utils'
import { type ClarificationOption, type ClarificationPayload } from '@/lib/api'

interface Props {
  clarification: ClarificationPayload
  onSelect: (option: ClarificationOption) => void
  disabled?: boolean
}

/** Render genesis text with **bold** segments highlighted. */
function GenesisText({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return (
    <>
      {parts.map((part, i) =>
        part.startsWith('**') && part.endsWith('**') ? (
          <strong key={i} className="font-semibold text-violet-950">
            {part.slice(2, -2)}
          </strong>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </>
  )
}

function SimilarityIndicator({ score, strength }: { score: number; strength: string }) {
  const pct = Math.min(100, Math.max(0, Math.round(score * 100)))
  const barColor =
    strength === 'Strong'
      ? 'bg-violet-600'
      : strength === 'Moderate'
        ? 'bg-violet-500/80'
        : strength === 'Low'
          ? 'bg-violet-400/70'
          : 'bg-violet-300/80'

  return (
    <div
      className="flex-shrink-0 flex flex-col items-end gap-0.5 min-w-[5.5rem]"
      title={`${pct}% embedding similarity`}
    >
      <span className="text-[11px] font-medium text-violet-700/80 tabular-nums">{pct}%</span>
      <div className="w-16 h-1.5 rounded-full bg-violet-100 overflow-hidden" aria-hidden>
        <div className={cn('h-full rounded-full transition-all', barColor)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] text-violet-600/70">{strength}</span>
    </div>
  )
}

/** Renders disambiguation options when retrieval cannot match the user's wording. */
export function ClarificationCard({ clarification, onSelect, disabled }: Props) {
  return (
    <div className="rounded-xl border border-violet-200/90 bg-violet-50/80 p-4 shadow-sm">
      <p className="text-sm text-violet-900/85 whitespace-pre-line mb-3">
        <GenesisText text={clarification.genesis} />
      </p>
      {clarification.intent_summary && (
        <p className="text-xs text-violet-700/70 mb-3">{clarification.intent_summary}</p>
      )}
      <div className="flex flex-col gap-2">
        {clarification.options.map((option) => {
          const score = option.similarity_score ?? 0
          const strength = option.match_strength ?? 'Weak'

          return (
            <button
              key={option.id}
              type="button"
              disabled={disabled}
              onClick={() => onSelect(option)}
              className={cn(
                'text-left rounded-lg border border-violet-200 bg-white px-3 py-2.5 text-sm transition-colors',
                'text-violet-950 hover:border-violet-400 hover:bg-violet-50/50',
                'disabled:opacity-50 disabled:cursor-not-allowed',
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <span className="font-medium">{option.label}</span>
                  {option.preview_url && (
                    <span className="block text-xs text-violet-600/70 mt-1 truncate">
                      {option.preview_url}
                    </span>
                  )}
                </div>
                {option.similarity_score !== undefined && (
                  <SimilarityIndicator score={score} strength={strength} />
                )}
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
