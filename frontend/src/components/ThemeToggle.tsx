import { Moon, Sun } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useTheme } from '@/hooks/useTheme'

type Variant = 'header' | 'sidebar' | 'admin' | 'brand'

interface Props {
  variant?: Variant
  showLabel?: boolean
  className?: string
}

export function ThemeToggle({ variant = 'header', showLabel, className }: Props) {
  const { isDark, toggleTheme } = useTheme()
  const label = isDark ? 'Light' : 'Dark'

  if (variant === 'brand') {
    return (
      <button
        type="button"
        onClick={toggleTheme}
        title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
        className={cn(
          'flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-xs font-medium transition-colors',
          'text-white/80 hover:text-white hover:bg-white/10',
          className,
        )}
      >
        {isDark ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
        {showLabel !== false && label}
      </button>
    )
  }

  if (variant === 'sidebar') {
    return (
      <button
        type="button"
        onClick={toggleTheme}
        title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
        className={cn(
          'w-full flex items-center rounded-lg text-sm text-white/60 hover:bg-white/10 hover:text-white transition-colors',
          showLabel ? 'gap-2 px-3 py-2' : 'justify-center p-2',
          className,
        )}
      >
        {isDark ? <Sun className="w-4 h-4 flex-shrink-0" /> : <Moon className="w-4 h-4 flex-shrink-0" />}
        {showLabel && label}
      </button>
    )
  }

  if (variant === 'admin') {
    return (
      <button
        type="button"
        onClick={toggleTheme}
        title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
        className={cn('flex items-center gap-1.5', className)}
      >
        {isDark ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
        {label}
      </button>
    )
  }

  return (
    <button
      type="button"
      onClick={toggleTheme}
      title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      className={cn(
        'flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors',
        'text-slate-500 hover:text-slate-700 hover:bg-slate-100',
        'dark:text-slate-400 dark:hover:text-slate-200 dark:hover:bg-slate-800',
        className,
      )}
    >
      {isDark ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
      {showLabel !== false && label}
    </button>
  )
}
