import type { ParsedQuestion } from '@/lib/educator-parse'
import type { QuestionCardPhase } from '@/types/educator'
import { cn } from '@/lib/utils'

interface Props {
  question: ParsedQuestion
  phase: QuestionCardPhase
  attemptCount: number
  wrongSelections: string[]
  resolved: boolean
  disabled?: boolean
  onAnswer: (answer: string) => void
  onHint: () => void
  onShowDoc: () => void
  onSkip: () => void
  domainProgress?: { correct: number; total: number; domainName: string }
}

function attemptBadge(phase: QuestionCardPhase, attemptCount: number): string | null {
  if (phase === 'correct') {
    if (attemptCount <= 1) return 'Nailed it'
    if (attemptCount === 2) return 'Got it'
    return 'There we go'
  }
  if (phase === 'wrong') return `Attempt ${attemptCount} — not quite`
  if (phase === 'revealed') return "Let's look at this together"
  if (phase === 'skipped') return 'Added to revisit list'
  return null
}

export function QuestionCard({
  question,
  phase,
  attemptCount,
  wrongSelections,
  resolved,
  disabled,
  onAnswer,
  onHint,
  onShowDoc,
  onSkip,
  domainProgress,
}: Props) {
  const badge = attemptBadge(phase, attemptCount)
  const showPreAttempt = !resolved && phase !== 'skipped' && attemptCount === 0
  const optionsLocked = resolved || phase === 'skipped'

  return (
    <div
      className={cn(
        'mt-3 rounded-xl border p-4 transition-colors',
        phase === 'skipped' && 'opacity-60 border-slate-200 bg-slate-50',
        phase === 'correct' && 'border-emerald-200 bg-emerald-50/30',
        phase === 'wrong' && 'border-amber-200 bg-amber-50/20',
        !resolved && phase !== 'skipped' && 'border-violet-200 bg-violet-50/40',
      )}
    >
      {badge && (
        <p
          className={cn(
            'text-xs font-semibold mb-2',
            phase === 'correct' && 'text-emerald-700',
            phase === 'wrong' && 'text-amber-700',
            phase === 'revealed' && 'text-violet-700',
            phase === 'skipped' && 'text-slate-500',
          )}
        >
          {badge}
        </p>
      )}

      <div className="mb-2 flex items-center gap-2 text-xs text-violet-700">
        <span className="font-semibold">Question {question.number}</span>
        <span className="text-violet-400">·</span>
        <span className="italic">{question.domain}</span>
      </div>

      <p className="text-sm text-slate-800 whitespace-pre-wrap mb-3">{question.text}</p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {question.options.map((opt) => {
          const isWrong = wrongSelections.includes(opt.key)
          const isLocked = optionsLocked
          return (
            <button
              key={opt.key}
              type="button"
              disabled={disabled || isLocked}
              onClick={() => onAnswer(opt.key)}
              className={cn(
                'text-left rounded-lg border px-3 py-2 text-sm transition-colors',
                isWrong && 'border-red-300 bg-red-50 text-red-900',
                !isWrong && !isLocked && 'border-violet-200 bg-white hover:border-violet-400 hover:bg-violet-50',
                isLocked && !isWrong && 'border-slate-200 bg-slate-50 opacity-80',
                disabled && 'opacity-50 cursor-not-allowed',
              )}
            >
              <span className="font-semibold text-violet-700 mr-1.5">{opt.key}.</span>
              {opt.label}
            </button>
          )
        })}
      </div>

      {showPreAttempt && (
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            disabled={disabled}
            onClick={onHint}
            className="rounded-lg border border-violet-200 bg-white px-3 py-1.5 text-xs font-medium text-violet-700 hover:bg-violet-50 disabled:opacity-50"
          >
            Give me a hint
          </button>
          <button
            type="button"
            disabled={disabled}
            onClick={onShowDoc}
            className="rounded-lg border border-blue-200 bg-white px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-50 disabled:opacity-50"
          >
            Show me the doc first
          </button>
        </div>
      )}

      {!resolved && phase !== 'skipped' && (
        <button
          type="button"
          disabled={disabled}
          onClick={onSkip}
          className="mt-3 text-xs text-slate-500 hover:text-slate-700 underline disabled:opacity-50"
        >
          Skip (I'll come back to this)
        </button>
      )}

      {domainProgress && phase === 'correct' && (
        <div className="mt-4 pt-3 border-t border-emerald-200">
          <div className="flex justify-between text-xs text-emerald-800 mb-1">
            <span>{domainProgress.domainName}</span>
            <span>
              {domainProgress.correct}/{domainProgress.total} in this domain
            </span>
          </div>
          <div className="h-1.5 rounded-full bg-emerald-100 overflow-hidden">
            <div
              className="h-full bg-emerald-500 rounded-full"
              style={{
                width: `${domainProgress.total > 0 ? (domainProgress.correct / domainProgress.total) * 100 : 0}%`,
              }}
            />
          </div>
        </div>
      )}
    </div>
  )
}
