import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { ChevronDown, ChevronUp, Pause, Play } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  PRODUCT_PILL_STYLES,
  SOLUTION_PILL_STYLE,
  type TickerQuestion,
} from '@/config/questions'

const VISIBLE_COUNT = 4
const CARD_MIN_HEIGHT = 73
const CARD_DIVIDER = 0.5
const CARD_STEP = CARD_MIN_HEIGHT + CARD_DIVIDER
const WINDOW_HEIGHT = CARD_STEP * VISIBLE_COUNT
const AUTO_INTERVAL_MS = 3800
const SCROLL_TRANSITION = 'transform 0.55s cubic-bezier(0.4, 0, 0.2, 1)'

interface Props {
  questions: TickerQuestion[]
  onSelectPrompt: (text: string) => void
}

function Pill({
  label,
  bg,
  color,
}: {
  label: string
  bg: string
  color: string
}) {
  return (
    <span
      className="inline-block font-medium whitespace-nowrap"
      style={{
        fontSize: 10,
        padding: '2px 8px',
        borderRadius: 20,
        backgroundColor: bg,
        color,
      }}
    >
      {label}
    </span>
  )
}

export function QuestionTicker({ questions, onSelectPrompt }: Props) {
  const count = questions.length
  const loopQuestions = count > 0 ? [...questions, ...questions] : []

  const [index, setIndex] = useState(0)
  const [manualPaused, setManualPaused] = useState(false)
  const [hoverPaused, setHoverPaused] = useState(false)
  const [animate, setAnimate] = useState(true)

  const intervalRef = useRef<number | null>(null)
  const resetTimerRef = useRef<number | null>(null)

  const autoPaused = manualPaused || hoverPaused

  const clearAutoTimer = useCallback(() => {
    if (intervalRef.current !== null) {
      window.clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  const scheduleAuto = useCallback(() => {
    clearAutoTimer()
    if (autoPaused || count < 2) return
    intervalRef.current = window.setInterval(() => {
      setIndex((prev) => (prev >= count ? prev : prev + 1))
    }, AUTO_INTERVAL_MS)
  }, [clearAutoTimer, autoPaused, count])

  const goNext = useCallback(() => {
    setAnimate(true)
    setIndex((prev) => (prev >= count ? 0 : prev + 1))
    scheduleAuto()
  }, [count, scheduleAuto])

  const goPrev = useCallback(() => {
    if (count === 0) return
    setAnimate(true)
    setIndex((prev) => (prev <= 0 ? count - 1 : prev - 1))
    scheduleAuto()
  }, [count, scheduleAuto])

  const togglePause = useCallback(() => {
    setManualPaused((p) => !p)
  }, [])

  const handleSelect = useCallback(
    (text: string) => {
      setHoverPaused(true)
      onSelectPrompt(text)
    },
    [onSelectPrompt],
  )

  // Infinite loop reset at midpoint
  useEffect(() => {
    if (count === 0 || index < count) return

    resetTimerRef.current = window.setTimeout(() => {
      setAnimate(false)
      setIndex(0)
      requestAnimationFrame(() => {
        requestAnimationFrame(() => setAnimate(true))
      })
    }, 550)

    return () => {
      if (resetTimerRef.current !== null) {
        window.clearTimeout(resetTimerRef.current)
      }
    }
  }, [index, count])

  useEffect(() => {
    scheduleAuto()
    return clearAutoTimer
  }, [scheduleAuto, clearAutoTimer])

  if (count === 0) {
    return (
      <p className="text-sm text-center" style={{ color: '#94a3b8' }}>
        No questions yet. Type your own below.
      </p>
    )
  }

  const translateY = -index * CARD_STEP

  return (
    <div
      className="w-full max-w-[720px] mx-auto bg-white dark:bg-slate-900 rounded-xl overflow-hidden border border-slate-200 dark:border-slate-700"
      onMouseEnter={() => setHoverPaused(true)}
      onMouseLeave={() => setHoverPaused(false)}
    >
      {/* Scroll window */}
      <div
        className="relative overflow-hidden"
        style={{ height: WINDOW_HEIGHT }}
      >
        <div
          className="absolute inset-x-0 top-0 z-[2] pointer-events-none h-7 bg-gradient-to-b from-white dark:from-slate-900 to-transparent"
        />
        <div
          className="absolute inset-x-0 bottom-0 z-[2] pointer-events-none h-7 bg-gradient-to-t from-white dark:from-slate-900 to-transparent"
        />

        <div
          className="absolute inset-x-0 top-0 will-change-transform"
          style={{
            transform: `translateY(${translateY}px)`,
            transition: animate ? SCROLL_TRANSITION : 'none',
          }}
        >
          {loopQuestions.map((q, i) => (
            <button
              key={`${i}-${q.text}`}
              type="button"
              onClick={() => handleSelect(q.text)}
              className="w-full text-left transition-colors duration-100 hover:bg-slate-50 dark:hover:bg-slate-800 focus-visible:outline-none focus-visible:bg-slate-50 dark:focus-visible:bg-slate-800 border-b border-slate-200 dark:border-slate-700"
              style={{
                minHeight: CARD_MIN_HEIGHT,
                padding: '12px 16px',
              }}
            >
              <div className="flex items-start gap-3 mb-1">
                <p className="flex-1 m-0 text-[13px] leading-snug text-slate-800 dark:text-slate-100">
                  {q.text}
                </p>
                {q.asked > 0 && (
                  <span className="flex-shrink-0 whitespace-nowrap text-[11px] text-slate-400 dark:text-slate-500">
                    {q.asked}×
                  </span>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-[5px]">
                <Pill
                  label={PRODUCT_PILL_STYLES[q.product].label}
                  bg={PRODUCT_PILL_STYLES[q.product].bg}
                  color={PRODUCT_PILL_STYLES[q.product].text}
                />
                {q.solutions.map((s) => (
                  <Pill
                    key={s}
                    label={s}
                    bg={SOLUTION_PILL_STYLE.bg}
                    color={SOLUTION_PILL_STYLE.text}
                  />
                ))}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Controls — bottom of box */}
      <div className="flex items-center justify-end gap-1 px-2 py-1.5 border-t border-slate-200 dark:border-slate-700">
        <TickerControlButton label="Previous question" onClick={goPrev}>
          <ChevronUp className="w-3.5 h-3.5" strokeWidth={2.5} />
        </TickerControlButton>
        <TickerControlButton
          label={manualPaused ? 'Resume' : 'Pause'}
          onClick={togglePause}
          active={manualPaused}
        >
          {manualPaused ? (
            <Play className="w-3.5 h-3.5" strokeWidth={2.5} />
          ) : (
            <Pause className="w-3.5 h-3.5" strokeWidth={2.5} />
          )}
        </TickerControlButton>
        <TickerControlButton label="Next question" onClick={goNext}>
          <ChevronDown className="w-3.5 h-3.5" strokeWidth={2.5} />
        </TickerControlButton>
      </div>
    </div>
  )
}

function TickerControlButton({
  children,
  label,
  onClick,
  active = false,
}: {
  children: ReactNode
  label: string
  onClick: () => void
  active?: boolean
}) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      className={cn(
        'flex items-center justify-center w-[26px] h-[26px] rounded-md text-[13px] transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1D9E75]',
        active
          ? 'border border-emerald-500 bg-emerald-50 dark:bg-emerald-950/50 text-emerald-600 dark:text-emerald-400'
          : 'border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700 hover:border-slate-400 dark:hover:border-slate-500 hover:text-slate-800 dark:hover:text-slate-200',
      )}
    >
      {children}
    </button>
  )
}
