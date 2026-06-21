import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { SessionReport } from '@/types/interviewer'

interface Props {
  report: SessionReport
  debriefContent?: string
  debriefStreaming?: boolean
  className?: string
}

const READINESS_LABELS: Record<string, string> = {
  not_ready: 'Not ready',
  needs_work: 'Needs work',
  nearly_ready: 'Nearly ready',
  interview_ready: 'Interview ready',
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.min(100, Math.max(0, (score / 5) * 100))
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2.5 rounded-full bg-slate-100 overflow-hidden">
        <div
          className={cn(
            'h-full rounded-full',
            score >= 4 ? 'bg-emerald-500' : score >= 3 ? 'bg-amber-400' : 'bg-red-400',
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-base font-semibold tabular-nums text-slate-800">{score.toFixed(1)}/5</span>
    </div>
  )
}

export function InterviewSessionReport({ report, debriefContent, debriefStreaming, className }: Props) {
  const readinessLabel = READINESS_LABELS[report.readiness] ?? report.readiness
  const feedbackText = debriefContent?.trim() || report.overall_feedback

  return (
    <div className={cn('rounded-xl border border-emerald-200 bg-white p-5 not-prose space-y-5 shadow-sm', className)}>
      <div className="border-b border-slate-100 pb-4">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-emerald-700 mb-1.5">
          Final summary
        </p>
        <ScoreBar score={report.overall_score} />
        <p className="text-base font-semibold text-slate-900 mt-3">{readinessLabel}</p>
        <p className="text-sm text-slate-600 mt-1">{report.readiness_summary}</p>
      </div>

      {feedbackText && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">
            Coach&apos;s debrief
          </p>
          <div
            className={cn(
              'prose prose-sm max-w-none text-slate-800 rounded-lg bg-slate-50 px-4 py-3',
              debriefStreaming && 'streaming-cursor',
            )}
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{feedbackText}</ReactMarkdown>
          </div>
        </div>
      )}

      {report.strengths.length > 0 && (
        <div>
          <p className="text-xs font-medium text-emerald-800 mb-1">Overall strengths</p>
          <ul className="text-xs text-slate-700 list-disc pl-4 space-y-0.5">
            {report.strengths.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}

      {report.priority_gaps.length > 0 && (
        <div>
          <p className="text-xs font-medium text-amber-800 mb-1">Priority gaps</p>
          <ul className="text-xs text-slate-700 list-disc pl-4 space-y-0.5">
            {report.priority_gaps.map((g, i) => (
              <li key={i}>{g}</li>
            ))}
          </ul>
        </div>
      )}

      {report.mistakes_to_avoid.length > 0 && (
        <div>
          <p className="text-xs font-medium text-red-800 mb-1">Mistakes to avoid</p>
          <ul className="text-xs text-slate-700 list-disc pl-4 space-y-0.5">
            {report.mistakes_to_avoid.map((m, i) => (
              <li key={i}>{m}</li>
            ))}
          </ul>
        </div>
      )}

      {report.topics_to_read.length > 0 && (
        <div>
          <p className="text-xs font-medium text-slate-600 mb-1">Topics to study</p>
          <ul className="text-xs text-slate-700 space-y-1.5">
            {report.topics_to_read.map((t, i) => (
              <li key={i}>
                <span className="font-medium">{t.topic}</span>
                {t.reason && <span className="text-slate-500"> — {t.reason}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {report.per_question.length > 0 && (
        <div>
          <p className="text-xs font-medium text-slate-600 mb-2">Per-question scores</p>
          <div className="space-y-2">
            {report.per_question.map((q) => (
              <div key={q.question_id} className="rounded-lg border border-slate-200 bg-white p-3">
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="text-[11px] font-semibold text-slate-500">Q{q.question_index}</span>
                  <span className="text-xs font-semibold text-slate-700">{q.score}/5</span>
                </div>
                <p className="text-xs text-slate-800 font-medium mb-1">{q.question}</p>
                {q.gaps.length > 0 && (
                  <p className="text-[11px] text-slate-500">Gap: {q.gaps[0]}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {report.citations.length > 0 && (
        <div>
          <p className="text-xs font-medium text-slate-600 mb-1.5">Suggested reading</p>
          <ul className="space-y-1">
            {report.citations.map((c) => (
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
