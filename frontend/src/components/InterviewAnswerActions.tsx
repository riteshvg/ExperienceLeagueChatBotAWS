import { Pencil, ChevronRight, ClipboardList } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { PendingAnswer } from '@/types/interviewer'

interface Props {
  pending: PendingAnswer
  onEdit: () => void
  onNext: () => void
  disabled?: boolean
  className?: string
}

export function InterviewAnswerActions({
  pending,
  onEdit,
  onNext,
  disabled,
  className,
}: Props) {
  return (
    <div
      className={cn(
        'rounded-xl border border-slate-200 bg-white p-4 not-prose space-y-3 shadow-sm',
        className,
      )}
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        Answer saved · Q{pending.questionIndex}
      </p>
      <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">{pending.answer}</p>
      <div className="flex flex-wrap gap-2 pt-1">
        <button
          type="button"
          onClick={onEdit}
          disabled={disabled}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          <Pencil className="w-3.5 h-3.5" />
          Edit answer
        </button>
        <button
          type="button"
          onClick={onNext}
          disabled={disabled}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-700 text-sm font-medium text-white hover:bg-emerald-800 disabled:opacity-50"
        >
          {pending.isLast ? (
            <>
              <ClipboardList className="w-3.5 h-3.5" />
              Review all answers
            </>
          ) : (
            <>
              Next question
              <ChevronRight className="w-3.5 h-3.5" />
            </>
          )}
        </button>
      </div>
    </div>
  )
}
