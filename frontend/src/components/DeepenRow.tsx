import type { DeepenAction } from '@/types/educator'
import { cn } from '@/lib/utils'

interface Props {
  actions: DeepenAction[]
  disabled?: boolean
  onAction: (action: DeepenAction) => void
}

export function DeepenRow({ actions, disabled, onAction }: Props) {
  if (actions.length === 0) return null

  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {actions.map((action) => (
        <button
          key={`${action.type}-${action.label}`}
          type="button"
          disabled={disabled}
          onClick={() => onAction(action)}
          className={cn(
            'rounded-full border px-3 py-1.5 text-xs font-medium transition-colors',
            action.type === 'next'
              ? 'border-violet-300 bg-violet-600 text-white hover:bg-violet-700'
              : 'border-slate-200 bg-white text-slate-700 hover:border-violet-300 hover:text-violet-700',
            disabled && 'opacity-50 cursor-not-allowed',
          )}
        >
          {action.label}
        </button>
      ))}
    </div>
  )
}
