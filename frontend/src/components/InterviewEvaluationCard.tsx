import { ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { InterviewEvaluation } from '@/types/interviewer'

interface Props {
  evaluation: InterviewEvaluation
  className?: string
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.min(100, Math.max(0, (score / 5) * 100))
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
        <div
          className={cn(
            'h-full rounded-full transition-all',
            score >= 4 ? 'bg-emerald-500' : score >= 3 ? 'bg-amber-400' : 'bg-red-400',
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-sm font-semibold tabular-nums text-slate-700">{score}/5</span>
    </div>
  )
}

export function InterviewEvaluationCard({ evaluation, className }: Props) {
  return (
    <div className={cn('rounded-xl border border-slate-200 bg-slate-50/80 p-4 not-prose space-y-3', className)}>
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500 mb-1.5">
          Evaluation · Q{evaluation.question_index}
        </p>
        <ScoreBar score={evaluation.score} />
        <p className="text-xs text-slate-500 mt-1">{evaluation.score_pct}% match for this level</p>
      </div>

      {evaluation.strengths.length > 0 && (
        <div>
          <p className="text-xs font-medium text-emerald-800 mb-1">Strengths</p>
          <ul className="text-xs text-slate-700 list-disc pl-4 space-y-0.5">
            {evaluation.strengths.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}

      {evaluation.gaps.length > 0 && (
        <div>
          <p className="text-xs font-medium text-amber-800 mb-1">Gaps to address</p>
          <ul className="text-xs text-slate-700 list-disc pl-4 space-y-0.5">
            {evaluation.gaps.map((g, i) => (
              <li key={i}>{g}</li>
            ))}
          </ul>
        </div>
      )}

      {evaluation.model_answer_outline && (
        <div>
          <p className="text-xs font-medium text-slate-600 mb-1">Model answer outline</p>
          <p className="text-xs text-slate-700 whitespace-pre-line">{evaluation.model_answer_outline}</p>
        </div>
      )}

      {evaluation.citations.length > 0 && (
        <div>
          <p className="text-xs font-medium text-slate-600 mb-1.5">Suggested reading</p>
          <ul className="space-y-1">
            {evaluation.citations.map((c) => (
              <li key={c.url}>
                <a
                  href={c.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-emerald-700 hover:underline"
                >
                  {c.title}
                  <ExternalLink className="w-3 h-3 shrink-0" />
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
