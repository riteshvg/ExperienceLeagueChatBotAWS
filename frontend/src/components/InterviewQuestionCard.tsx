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
          Practice question
          {question.index != null && question.total != null && (
            <span className="font-normal normal-case ml-1">
              · {question.index} of {question.total}
            </span>
          )}
        </span>
        <span className="text-[10px] text-emerald-700/70 capitalize">{question.topic.replace(/_/g, ' ')}</span>
      </div>
      <p className="text-sm font-medium text-slate-800 leading-relaxed">{question.question}</p>
      {question.expected_themes.length > 0 && (
        <p className="text-[11px] text-slate-500 mt-2">
          Themes: {question.expected_themes.join(' · ')}
        </p>
      )}
    </div>
  )
}
