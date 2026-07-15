import { Clock, MoreHorizontal } from 'lucide-react'
import { useElapsedTime } from '@/lib/useElapsedTime'
import { InterviewProgressDots } from './InterviewProgressDots'
import type { InterviewPhase } from '@/types/interviewer'

interface Props {
  level: string | null
  profileLabel: string | null
  phase: InterviewPhase
  createdAt: string | null
  questionIndex: number
  totalQuestions: number
}

export function InterviewHeaderBar({
  level,
  profileLabel,
  phase,
  createdAt,
  questionIndex,
  totalQuestions,
}: Props) {
  const elapsed = useElapsedTime(createdAt, phase === 'complete')
  const showProgress = totalQuestions > 0 && phase !== 'review' && phase !== 'evaluating' && phase !== 'complete'
  const levelProduct = [level ? level[0].toUpperCase() + level.slice(1) : null, profileLabel]
    .filter(Boolean)
    .join(' · ')

  return (
    <div className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-2.5">
      <div className="flex items-center gap-2 min-w-0">
        <span className="text-sm font-semibold text-slate-800 whitespace-nowrap">Interviewer mode</span>
        {levelProduct && (
          <span className="text-sm text-slate-500 truncate">{levelProduct}</span>
        )}
      </div>
      <div className="flex items-center gap-3 shrink-0">
        <div className="flex items-center gap-1 text-sm text-slate-500 tabular-nums">
          <Clock className="w-3.5 h-3.5" />
          {elapsed}
        </div>
        {showProgress && <InterviewProgressDots current={questionIndex} total={totalQuestions} />}
        <button
          type="button"
          className="p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-50"
          title="More"
        >
          <MoreHorizontal className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}
