import { useEffect, useMemo, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { fetchLandingQuestions, type LandingQuestion } from '@/lib/api'

export type SolutionCategory =
  | 'All'
  | 'Analytics'
  | 'CJA'
  | 'AEP'
  | 'Target'
  | 'AJO'
  | 'Data Collection'
  | 'Cross-Product'
  | 'General'

export const LANDING_CATEGORIES: SolutionCategory[] = [
  'All',
  'Analytics',
  'CJA',
  'AEP',
  'Target',
  'AJO',
  'Data Collection',
  'Cross-Product',
  'General',
]

export const CATEGORY_COLORS: Record<Exclude<SolutionCategory, 'All'>, string> = {
  Analytics: 'bg-orange-50 text-orange-700 border-orange-200',
  CJA: 'bg-violet-50 text-violet-700 border-violet-200',
  AEP: 'bg-blue-50 text-blue-700 border-blue-200',
  Target: 'bg-red-50 text-red-700 border-red-200',
  AJO: 'bg-green-50 text-green-700 border-green-200',
  'Data Collection': 'bg-amber-50 text-amber-700 border-amber-200',
  'Cross-Product': 'bg-teal-50 text-teal-700 border-teal-200',
  General: 'bg-slate-50 text-slate-600 border-slate-200',
}

interface Props {
  sessionId: string
  onSelectPrompt: (text: string) => void
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
  const [activeCategory, setActiveCategory] = useState<SolutionCategory>('All')
  const [bySolution, setBySolution] = useState<Record<string, LandingQuestion[]>>({})
  const [source, setSource] = useState<'postgres' | 'fallback' | null>(null)
  const [allTabLimit, setAllTabLimit] = useState(4)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetchLandingQuestions()
      .then((data) => {
        if (cancelled) return
        setBySolution(data.by_solution)
        setSource(data.source)
        setAllTabLimit(data.all_tab_per_solution ?? 4)
      })
      .catch(() => {
        if (cancelled) return
        setSource('fallback')
        setBySolution({})
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [sessionId])

  const visibleQuestions = useMemo(() => {
    if (activeCategory === 'All') {
      return LANDING_CATEGORIES.filter((c) => c !== 'All').flatMap((cat) =>
        (bySolution[cat] ?? []).slice(0, allTabLimit).map((q) => ({ ...q, solution: cat })),
      )
    }
    return (bySolution[activeCategory] ?? []).map((q) => ({
      ...q,
      solution: activeCategory,
    }))
  }, [activeCategory, bySolution, allTabLimit])

  return (
    <div className="min-h-full flex flex-col items-center justify-center px-4 py-8 md:py-12">
      <img
        src={`${import.meta.env.BASE_URL}rovrlogo.png`}
        alt="Rovr"
        className="h-12 w-auto mb-4"
      />
      <h2 className="text-lg font-semibold text-slate-700 mb-1 text-center">
        Ask about Adobe Experience League docs
      </h2>
      {source === 'postgres' && (
        <p className="text-xs text-slate-400 mb-5 text-center">
          Popular questions from other Rovr users — pick one to get started
        </p>
      )}
      {source !== 'postgres' && <div className="mb-5" />}

      {isNewUser && monthlyRemaining > 0 && !welcomeDismissed && monthlyLimit < 9999 && (
        <div className="w-full max-w-md mb-5 px-5 py-4 rounded-xl bg-emerald-50 border border-emerald-200 text-left">
          <h3 className="text-sm font-semibold text-emerald-800 mb-1">Welcome to Rovr</h3>
          <p className="text-xs text-emerald-700 leading-relaxed">
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

      <div className="flex flex-wrap justify-center gap-1.5 mb-4 max-w-2xl">
        {LANDING_CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
              activeCategory === cat
                ? 'bg-[#10B981] text-white border-[#10B981]'
                : 'bg-white text-slate-500 border-slate-200 hover:border-[#10B981] hover:text-[#10B981]'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-slate-400 py-8">
          <Loader2 className="w-4 h-4 animate-spin" />
          Loading questions…
        </div>
      ) : visibleQuestions.length === 0 ? (
        <p className="text-sm text-slate-400 py-8 text-center max-w-md">
          No questions for this solution yet. Type your own question below.
        </p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 w-full max-w-4xl">
          {visibleQuestions.map((item) => (
            <button
              key={`${item.solution}-${item.text}`}
              onClick={() => onSelectPrompt(item.text)}
              className="group text-left px-4 py-3 rounded-xl border border-slate-200 bg-white hover:border-indigo-300 hover:shadow-sm transition-all"
            >
              <span
                className={`inline-block text-[10px] font-semibold px-1.5 py-0.5 rounded border mb-1.5 ${
                  CATEGORY_COLORS[item.solution as Exclude<SolutionCategory, 'All'>]
                }`}
              >
                {item.solution}
              </span>
              <p className="text-sm text-slate-600 group-hover:text-[#14532D] leading-snug">
                {item.text}
              </p>
              {item.times_asked > 1 && (
                <p className="text-[10px] text-slate-400 mt-1.5">
                  Asked {item.times_asked} times
                </p>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
