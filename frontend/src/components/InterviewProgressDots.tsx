import { cn } from '@/lib/utils'

interface Props {
  current: number
  total: number
  className?: string
}

export function InterviewProgressDots({ current, total, className }: Props) {
  if (total <= 0) return null

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className="flex items-center gap-1">
        {Array.from({ length: total }, (_, i) => {
          const isCurrent = i === current
          const isPast = i < current
          return (
            <span
              key={i}
              className={cn(
                'h-1.5 rounded-full transition-all',
                isCurrent ? 'w-5 bg-emerald-600' : 'w-1.5',
                !isCurrent && (isPast ? 'bg-emerald-600' : 'bg-slate-200'),
              )}
            />
          )
        })}
      </div>
      <span className="text-xs text-slate-500 tabular-nums whitespace-nowrap">
        {Math.min(current + 1, total)} of {total}
      </span>
    </div>
  )
}
