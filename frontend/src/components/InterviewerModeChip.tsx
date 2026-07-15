import { Briefcase } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Props {
  active: boolean
  available: boolean
  adminOnly: boolean
  onClick: () => void
}

/** Toggle Interviewer Mode — admin beta when admin_only is set on the server. */
export function InterviewerModeChip({ active, available, adminOnly, onClick }: Props) {
  if (!available) return null

  return (
    <button
      type="button"
      onClick={onClick}
      title={adminOnly ? 'Interviewer Mode (admin beta)' : 'Interviewer Mode'}
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-colors',
        active
          ? 'bg-emerald-700 text-white border-emerald-800'
          : 'bg-white text-slate-600 border-slate-200 hover:border-emerald-300 hover:text-emerald-800',
      )}
    >
      <Briefcase className="w-3.5 h-3.5" />
      {active ? 'Interviewer' : 'Interview prep'}
      {adminOnly && !active && (
        <span className="text-[10px] uppercase tracking-wide opacity-70">Beta</span>
      )}
    </button>
  )
}
