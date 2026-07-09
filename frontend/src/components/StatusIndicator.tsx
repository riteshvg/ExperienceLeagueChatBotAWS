import { useEffect, useState } from 'react'
import { type ChatStage } from '@/lib/api'

const STAGE_COPY: Record<ChatStage, string> = {
  understanding: 'Reading your question',
  searching: 'Checking Adobe documentation',
  writing: 'Synthesizing the answer',
}

// Cosmetic only — the "writing" stage is real and can legitimately run 10+ seconds,
// so this keeps the message feeling alive with a one-way sense of progress. Holds at
// the last entry rather than looping back — repeating "Complete" would be fine, but
// looping back to "Synthesizing the answer" after "Complete" would read as broken.
// Never used for understanding/searching.
const WRITING_PROGRESSION = [
  'Synthesizing the answer',
  'Adding steps',
  'Almost done',
  'Complete',
]

const WRITING_CYCLE_MS = 4500
const STALLED_COPY = 'Still working on it…'

interface Props {
  stage: ChatStage | null
  stalled: boolean
}

export function StatusIndicator({ stage, stalled }: Props) {
  const [writingIndex, setWritingIndex] = useState(0)

  useEffect(() => {
    if (stage !== 'writing') {
      setWritingIndex(0)
      return
    }
    const id = setInterval(() => {
      setWritingIndex((i) => Math.min(i + 1, WRITING_PROGRESSION.length - 1))
    }, WRITING_CYCLE_MS)
    return () => clearInterval(id)
  }, [stage])

  if (!stage) return null

  const text = stalled ? STALLED_COPY : stage === 'writing' ? WRITING_PROGRESSION[writingIndex] : STAGE_COPY[stage]

  return (
    <div className="flex w-full justify-start" role="status" aria-live="polite">
      <div className="max-w-[85%]">
        <div className="flex items-center gap-2 rounded-2xl rounded-bl-sm border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500 shadow-sm dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400">
          <span className="flex gap-1">
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.3s] dark:bg-slate-500" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.15s] dark:bg-slate-500" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 dark:bg-slate-500" />
          </span>
          {text}
        </div>
      </div>
    </div>
  )
}
