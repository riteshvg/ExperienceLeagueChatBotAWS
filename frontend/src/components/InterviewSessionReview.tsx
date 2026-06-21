import { Pencil } from 'lucide-react'
import { cn } from '@/lib/utils'
import { InterviewAnswerPreview } from './InterviewAnswerPreview'
import type { ReviewItem } from '@/types/interviewer'

interface Props {
  items: ReviewItem[]
  onEdit: (questionId: string) => void
  onSubmit: () => void
  disabled?: boolean
  allAnswered?: boolean
  className?: string
}

export function InterviewSessionReview({
  items,
  onEdit,
  onSubmit,
  disabled,
  allAnswered = true,
  className,
}: Props) {
  return (
    <div
      className={cn(
        'rounded-xl border border-emerald-200 bg-emerald-50/40 p-4 not-prose space-y-4',
        className,
      )}
    >
      <div>
        <p className="text-sm font-semibold text-emerald-900">Review before submitting</p>
        <p className="text-xs text-emerald-800/80 mt-1">
          Read each answer below. Click Edit to revise any response, then submit for your full
          evaluation and interview readiness debrief.
        </p>
      </div>

      <div className="space-y-3">
        {items.map((item) => (
          <div
            key={item.question.id}
            className="rounded-lg border border-slate-200 bg-white p-3 space-y-2"
          >
            <div className="flex items-start justify-between gap-2">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                Q{item.question.index} · {item.question.topic.replace(/_/g, ' ')}
              </p>
              <button
                type="button"
                onClick={() => onEdit(item.question.id)}
                disabled={disabled}
                className="inline-flex items-center gap-1 text-xs text-emerald-700 hover:underline disabled:opacity-50 shrink-0"
              >
                <Pencil className="w-3 h-3" />
                Edit
              </button>
            </div>
            <p className="text-sm font-medium text-slate-800">{item.question.question}</p>
            {item.answer.trim() ? (
              <InterviewAnswerPreview answer={item.answer} />
            ) : (
              <p className="text-sm italic text-slate-400">No answer recorded</p>
            )}
          </div>
        ))}
      </div>

      <button
        type="button"
        onClick={onSubmit}
        disabled={disabled || !allAnswered}
        className="w-full px-4 py-2.5 rounded-lg bg-emerald-700 text-white text-sm font-medium hover:bg-emerald-800 disabled:opacity-50"
      >
        Submit for evaluation
      </button>
      {!allAnswered && (
        <p className="text-xs text-amber-700">Every question needs an answer before submitting.</p>
      )}
    </div>
  )
}
