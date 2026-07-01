import { useEffect, useMemo, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { fetchLandingQuestions } from '@/lib/api'
import { mergeTickerQuestions, type TickerQuestion } from '@/config/questions'
import { QuestionTicker } from '@/components/QuestionTicker'

interface Props {
  sessionId: string
  onSelectPrompt: (question: TickerQuestion) => void
  isNewUser: boolean
  monthlyRemaining: number
  monthlyLimit: number
  welcomeDismissed: boolean
  onDismissWelcome: () => void
}

export function LandingPanel({
  sessionId,
  onSelectPrompt,
  isNewUser,
  monthlyRemaining,
  monthlyLimit,
  welcomeDismissed,
  onDismissWelcome,
}: Props) {
  const [source, setSource] = useState<'postgres' | 'fallback' | null>(null)
  const [loading, setLoading] = useState(true)
  const [apiQuestions, setApiQuestions] = useState<{ text: string; solution: string; times_asked: number }[]>([])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetchLandingQuestions()
      .then((data) => {
        if (cancelled) return
        setApiQuestions(data.questions)
        setSource(data.source)
      })
      .catch(() => {
        if (cancelled) return
        setSource('fallback')
        setApiQuestions([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [sessionId])

  const tickerQuestions = useMemo(
    () =>
      mergeTickerQuestions(
        apiQuestions.map((q) => ({
          text: q.text,
          solution: q.solution,
          times_asked: q.times_asked,
        })),
      ),
    [apiQuestions],
  )

  return (
    <div className="min-h-full flex flex-col items-center justify-center px-4 py-6 md:py-8">
      <img
        src={`${import.meta.env.BASE_URL}rovrlogo.png`}
        alt="Rovr"
        className="h-12 w-auto mb-3"
      />
      <h2 className="text-lg font-semibold text-slate-700 dark:text-slate-200 mb-1 text-center">
        Ask about Adobe Experience League docs
      </h2>
      <p className="text-xs text-slate-400 dark:text-slate-500 mb-3 text-center">
        {source === 'postgres'
          ? 'What people ask Rovr — real questions from other users'
          : 'What people ask Rovr — examples to spark your own question'}
      </p>

      {isNewUser && monthlyRemaining > 0 && !welcomeDismissed && monthlyLimit < 9999 && (
        <div className="w-full max-w-md mb-5 px-5 py-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900 text-left">
          <h3 className="text-sm font-semibold text-emerald-800 dark:text-emerald-200 mb-1">Welcome to Rovr</h3>
          <p className="text-xs text-emerald-700 dark:text-emerald-300 leading-relaxed">
            You have {monthlyLimit} free queries this month to explore Adobe Experience Cloud
            documentation. Your quota resets on the 1st of each month. An administrator can adjust
            your limit if you need more.
          </p>
          <button
            onClick={onDismissWelcome}
            className="mt-3 px-3 py-1.5 rounded-lg bg-[#14532D] text-white text-xs font-medium hover:bg-[#10B981] transition-colors"
          >
            Got it
          </button>
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-slate-400 dark:text-slate-500 py-8">
          <Loader2 className="w-4 h-4 animate-spin" />
          Loading questions…
        </div>
      ) : (
        <QuestionTicker questions={tickerQuestions} onSelectPrompt={onSelectPrompt} />
      )}
    </div>
  )
}
