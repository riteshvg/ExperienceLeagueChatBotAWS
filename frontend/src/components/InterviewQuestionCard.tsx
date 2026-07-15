import { cn } from '@/lib/utils'
import type { InterviewQuestion } from '@/types/interviewer'

interface Props {
  question: InterviewQuestion
  className?: string
}

export function InterviewQuestionCard({ question, className }: Props) {
  return (
    <div
      className={cn(
        'rounded-xl border border-emerald-200 bg-emerald-50/60 p-4 not-prose',
        className,
      )}
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-[11px] font-semibold uppercase tracking-wide text-emerald-800/80">
          {question.is_followup ? (
            <span className="inline-flex items-center rounded-full bg-amber-100 text-amber-800 px-1.5 py-0.5 normal-case font-medium">
              Follow-up
            </span>
          ) : (
            'Question'
          )}
        </span>
        <span className="text-[10px] text-emerald-700/70 capitalize text-right">
          {[question.topic.replace(/_/g, ' '), ...question.expected_themes].join(' · ')}
        </span>
      </div>
      <p className="text-sm font-medium text-slate-800 leading-relaxed">{question.question}</p>
    </div>
  )
}
