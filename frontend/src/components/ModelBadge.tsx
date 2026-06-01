import { cn } from '@/lib/utils'

interface Props {
  model: string
  className?: string
}

export function ModelBadge({ model, className }: Props) {
  const isHaiku = model === 'haiku'
  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
        isHaiku
          ? 'bg-emerald-100 text-emerald-700'
          : 'bg-violet-100 text-violet-700',
        className,
      )}
    >
      {isHaiku ? 'Haiku' : 'Sonnet'}
    </span>
  )
}
