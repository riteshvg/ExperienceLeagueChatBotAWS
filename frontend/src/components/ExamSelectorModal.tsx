import { GraduationCap, Clock, Target } from 'lucide-react'
import type { Exam } from '@/types/educator'
import { cn } from '@/lib/utils'

interface Props {
  exams: Exam[]
  open: boolean
  onClose: () => void
  onSelect: (examId: string) => void
}

const LEVEL_COLORS: Record<string, string> = {
  Professional: 'bg-blue-50 text-blue-700 border-blue-200',
  Expert: 'bg-violet-50 text-violet-700 border-violet-200',
  Master: 'bg-amber-50 text-amber-700 border-amber-200',
}

export function ExamSelectorModal({ exams, open, onClose, onSelect }: Props) {
  if (!open) return null

  const byProduct = exams.reduce<Record<string, Exam[]>>((acc, exam) => {
    acc[exam.product] = acc[exam.product] ?? []
    acc[exam.product].push(exam)
    return acc
  }, {})

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 bg-black/40"
        aria-label="Close exam selector"
        onClick={onClose}
      />
      <div className="relative z-10 w-full max-w-2xl max-h-[85vh] overflow-hidden rounded-2xl bg-white shadow-xl flex flex-col">
        <div className="flex items-center gap-2 border-b border-slate-200 px-5 py-4">
          <GraduationCap className="h-5 w-5 text-violet-600" />
          <div>
            <h2 className="text-base font-semibold text-slate-800">Choose a certification exam</h2>
            <p className="text-xs text-slate-500">
              Educator mode won't just test you — it'll teach you. Wrong answers open up, not close down.
            </p>
          </div>
        </div>

        <div className="overflow-y-auto px-5 py-4 space-y-6">
          {Object.entries(byProduct).map(([product, productExams]) => (
            <section key={product}>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-2">
                {product}
              </h3>
              <div className="space-y-2">
                {productExams.map((exam) => (
                  <button
                    key={exam.id}
                    type="button"
                    onClick={() => onSelect(exam.id)}
                    className="w-full text-left rounded-xl border border-slate-200 p-4 hover:border-violet-300 hover:bg-violet-50/50 transition-colors"
                  >
                    <div className="flex flex-wrap items-center gap-2 mb-1.5">
                      <span className="rounded-md bg-slate-800 px-2 py-0.5 text-[11px] font-mono font-semibold text-white">
                        {exam.id}
                      </span>
                      <span
                        className={cn(
                          'rounded-full border px-2 py-0.5 text-[10px] font-semibold',
                          LEVEL_COLORS[exam.level] ?? 'bg-slate-50 text-slate-600',
                        )}
                      >
                        {exam.level}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-slate-800">{exam.name}</p>
                    <div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-500">
                      <span className="inline-flex items-center gap-1">
                        <Target className="h-3.5 w-3.5" />
                        {exam.totalQuestions} questions · pass {exam.passingScore}
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <Clock className="h-3.5 w-3.5" />
                        {exam.timeLimitMins} min
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </section>
          ))}
        </div>

        <div className="border-t border-slate-200 px-5 py-3 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-sm text-slate-600 hover:bg-slate-100"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}
