import type { ParsedQuestion } from '@/lib/educator-parse'
import { cn } from '@/lib/utils'

interface Props {
  question: ParsedQuestion
  disabled?: boolean
  answered?: boolean
  onSubmit: (answer: string) => void
  onSkip: () => void
}

export function QuestionCard({ question, disabled, answered, onSubmit, onSkip }: Props) {
  return (
    <div className="mt-3 rounded-xl border border-violet-200 bg-violet-50/40 p-4">
      <div className="mb-2 flex items-center gap-2 text-xs text-violet-700">
        <span className="font-semibold">Question {question.number}</span>
        <span className="text-violet-400">·</span>
        <span className="italic">{question.domain}</span>
      </div>
      <p className="text-sm text-slate-800 whitespace-pre-wrap mb-3">{question.text}</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {question.options.map((opt) => (
          <button
            key={opt.key}
            type="button"
            disabled={disabled || answered}
            onClick={() => onSubmit(opt.key)}
            className={cn(
              'text-left rounded-lg border px-3 py-2 text-sm transition-colors',
              'border-violet-200 bg-white hover:border-violet-400 hover:bg-violet-50',
              'disabled:opacity-50 disabled:cursor-not-allowed',
            )}
          >
            <span className="font-semibold text-violet-700 mr-1.5">{opt.key}.</span>
            {opt.label}
          </button>
        ))}
      </div>
      {!answered && (
        <button
          type="button"
          disabled={disabled}
          onClick={onSkip}
          className="mt-3 text-xs text-slate-500 hover:text-slate-700 underline disabled:opacity-50"
        >
          Skip (counts as incorrect)
        </button>
      )}
    </div>
  )
}
