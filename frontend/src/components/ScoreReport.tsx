import { X, TrendingUp, AlertTriangle } from 'lucide-react'
import type { ReadinessReport } from '@/types/educator'
import { cn } from '@/lib/utils'

interface Props {
  report: ReadinessReport
  examName?: string
  onClose: () => void
}

const VERDICT_STYLE: Record<string, string> = {
  Ready: 'bg-emerald-50 text-emerald-800 border-emerald-200',
  'Almost ready': 'bg-amber-50 text-amber-800 border-amber-200',
  'Needs more prep': 'bg-red-50 text-red-800 border-red-200',
}

export function ScoreReport({ report, examName, onClose }: Props) {
  const weakDomains = report.domainReports.filter((d) => d.weak)

  return (
    <div className="fixed inset-y-0 right-0 z-40 w-full max-w-md border-l border-slate-200 bg-white shadow-xl flex flex-col">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-800">Readiness report</h2>
          {examName && <p className="text-xs text-slate-500">{examName}</p>}
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          aria-label="Close score report"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        <div className="rounded-xl border border-slate-200 p-4">
          <p className="text-2xl font-bold text-slate-800">
            {report.totalCorrect}/{report.totalAsked}
            <span className="text-base font-normal text-slate-500 ml-2">
              ({report.overallPct}%)
            </span>
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Passing benchmark: {report.passingPct}% ({report.passingPct}% of exam questions)
          </p>
          <div
            className={cn(
              'mt-3 inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold',
              VERDICT_STYLE[report.verdict],
            )}
          >
            <TrendingUp className="h-3.5 w-3.5" />
            {report.verdict}
          </div>
        </div>

        <section>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-3">
            Per-domain progress
          </h3>
          <div className="space-y-3">
            {report.domainReports.map((d) => (
              <div key={d.domainId}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-700 font-medium truncate pr-2">{d.domain}</span>
                  <span className="text-slate-500 shrink-0">
                    {d.correct}/{d.total} · {d.pct}%
                  </span>
                </div>
                <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className={cn(
                      'h-full rounded-full transition-all',
                      d.pct >= report.passingPct ? 'bg-emerald-500' : 'bg-violet-400',
                    )}
                    style={{ width: `${d.total > 0 ? d.pct : 0}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>

        {weakDomains.length > 0 && (
          <section>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-3 flex items-center gap-1">
              <AlertTriangle className="h-3.5 w-3.5" />
              Focus areas
            </h3>
            <div className="space-y-2">
              {weakDomains.map((d) => (
                <div
                  key={d.domainId}
                  className="rounded-lg border border-amber-200 bg-amber-50/50 p-3 text-xs"
                >
                  <p className="font-semibold text-amber-900">{d.domain}</p>
                  <p className="text-amber-800/80 mt-1">
                    Review Experience League docs on: {d.docSearchHint.split(' ').slice(0, 6).join(', ')}…
                  </p>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}
