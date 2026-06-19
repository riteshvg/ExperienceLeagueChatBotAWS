import { cn } from '@/lib/utils'
import type { RovrMode } from '@/types/educator'

interface Props {
  mode: RovrMode
  onModeChange: (mode: RovrMode) => void
}

export function EducatorModeChip({ mode, onModeChange }: Props) {
  return (
    <div className="flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 p-0.5 text-xs">
      <button
        type="button"
        onClick={() => onModeChange('standard')}
        className={cn(
          'rounded-full px-2.5 py-1 font-medium transition-colors',
          mode === 'standard'
            ? 'bg-white text-slate-800 shadow-sm'
            : 'text-slate-500 hover:text-slate-700',
        )}
      >
        Standard
      </button>
      <button
        type="button"
        onClick={() => onModeChange('educator')}
        className={cn(
          'rounded-full px-2.5 py-1 font-medium transition-colors flex items-center gap-1',
          mode === 'educator'
            ? 'bg-violet-600 text-white shadow-sm'
            : 'text-slate-500 hover:text-violet-700',
        )}
      >
        Educator
        <span className="rounded bg-violet-500/30 px-1 py-px text-[10px] font-semibold leading-none">
          β
        </span>
      </button>
    </div>
  )
}
