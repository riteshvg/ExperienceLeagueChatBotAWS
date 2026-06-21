import { CheckCircle2, Circle, Loader2, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { EvaluationProgress } from '@/types/interviewer'

interface Props {
  progress: EvaluationProgress
  className?: string
}

export function InterviewEvaluationProgress({ progress, className }: Props) {
  const pct =
    progress.total > 0
      ? Math.round(
          ((progress.completed + (progress.step === 'synthesis' ? 0.5 : 0)) / (progress.total + 1)) *
            100,
        )
      : 0

  return (
    <div
      className={cn(
        'rounded-xl border border-emerald-200 bg-emerald-50/50 p-4 not-prose space-y-4',
        className,
      )}
    >
      <div className="flex items-start gap-3">
        {progress.step === 'complete' ? (
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
        ) : (
          <Loader2 className="w-5 h-5 text-emerald-600 animate-spin shrink-0 mt-0.5" />
        )}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-emerald-900">
            {progress.step === 'synthesis'
              ? 'Preparing your final summary…'
              : progress.step === 'complete'
                ? 'Evaluation complete'
                : 'Evaluating your answers…'}
          </p>
          <p className="text-xs text-emerald-800/80 mt-0.5">
            {progress.step === 'synthesis'
              ? 'Synthesizing scores, readiness, and study recommendations.'
              : `Checking answers against Experience League documentation (${progress.completed} of ${progress.total} done).`}
          </p>
        </div>
      </div>

      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-[11px] text-emerald-800/70">
          <span>Progress</span>
          <span>{Math.min(pct, 100)}%</span>
        </div>
        <div className="h-2 rounded-full bg-emerald-100 overflow-hidden">
          <div
            className="h-full rounded-full bg-emerald-600 transition-all duration-500 ease-out"
            style={{ width: `${Math.min(pct, 100)}%` }}
          />
        </div>
      </div>

      <ul className="space-y-1.5">
        {progress.questionResults.map((q) => (
          <li
            key={q.question_id}
            className="flex items-center gap-2 text-xs text-slate-700 bg-white/70 rounded-lg px-3 py-2"
          >
            {q.status === 'done' ? (
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
            ) : q.status === 'evaluating' ? (
              <Loader2 className="w-3.5 h-3.5 text-emerald-500 animate-spin shrink-0" />
            ) : (
              <Circle className="w-3.5 h-3.5 text-slate-300 shrink-0" />
            )}
            <span className="flex-1 truncate">Question {q.question_index}</span>
            {q.status === 'done' && q.score != null && (
              <span className="font-semibold tabular-nums text-slate-800">{q.score}/5</span>
            )}
          </li>
        ))}
        {progress.step === 'synthesis' && (
          <li className="flex items-center gap-2 text-xs text-slate-700 bg-white/70 rounded-lg px-3 py-2">
            <Sparkles className="w-3.5 h-3.5 text-emerald-500 animate-pulse shrink-0" />
            <span className="flex-1">Final summary &amp; recommendations</span>
          </li>
        )}
      </ul>
    </div>
  )
}
