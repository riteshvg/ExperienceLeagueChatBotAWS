import { useState } from 'react'
import { CheckCircle2, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useInterviewerStore } from '@/store/interviewerStore'

const QUESTION_MATCH_OPTIONS = [
  { value: 1, label: 'Not at all' },
  { value: 2, label: 'Somewhat off' },
  { value: 3, label: 'Mostly right' },
  { value: 4, label: 'Good match' },
  { value: 5, label: 'Spot on' },
]

function ScalePicker({
  value,
  onChange,
  labels,
}: {
  value: number | null
  onChange: (v: number) => void
  labels?: { value: number; label: string }[]
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {[1, 2, 3, 4, 5].map((n) => {
        const label = labels?.find((l) => l.value === n)?.label
        return (
          <button
            key={n}
            type="button"
            onClick={() => onChange(n)}
            className={cn(
              'flex-1 min-w-[52px] rounded-lg border px-2 py-1.5 text-xs font-medium transition-colors',
              value === n
                ? 'border-emerald-500 bg-emerald-50 text-emerald-800'
                : 'border-slate-200 bg-white text-slate-600 hover:border-emerald-300',
            )}
          >
            {n}
            {label && <span className="block text-[10px] font-normal text-slate-500">{label}</span>}
          </button>
        )
      })}
    </div>
  )
}

/**
 * Optional, dismissible beta-feedback card shown below the debrief once a
 * session's final report is rendered. Plain form + storage — no LLM call.
 */
export function InterviewFeedbackForm() {
  const { debriefFeedbackStatus, submitDebriefFeedback, dismissDebriefFeedback } = useInterviewerStore()

  const [questionsMatch, setQuestionsMatch] = useState<number | null>(null)
  const [feedbackQuality, setFeedbackQuality] = useState<number | null>(null)
  const [suggestions, setSuggestions] = useState('')
  const [wouldRecommend, setWouldRecommend] = useState<boolean | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (debriefFeedbackStatus === 'dismissed') return null

  if (debriefFeedbackStatus === 'submitted') {
    return (
      <div className="rounded-xl border border-emerald-200 bg-emerald-50/40 p-4 flex items-center gap-2 text-sm text-emerald-800">
        <CheckCircle2 className="w-4 h-4 shrink-0" />
        Thanks for the feedback — it helps us improve Interviewer Mode.
      </div>
    )
  }

  const handleSubmit = async () => {
    setSubmitting(true)
    try {
      await submitDebriefFeedback({
        questions_match_level: questionsMatch,
        feedback_quality: feedbackQuality,
        suggestions: suggestions.trim() || null,
        would_recommend: wouldRecommend,
      })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 space-y-4 relative">
      <button
        type="button"
        onClick={() => dismissDebriefFeedback()}
        aria-label="Dismiss feedback form"
        className="absolute top-3 right-3 text-slate-400 hover:text-slate-600"
      >
        <X className="w-4 h-4" />
      </button>

      <div>
        <p className="text-sm font-semibold text-slate-900">Help us improve Interviewer Mode</p>
        <p className="text-xs text-slate-500 mt-0.5">
          You&apos;re one of our beta testers — a couple of quick questions, totally optional.
        </p>
      </div>

      <div>
        <p className="text-xs font-medium text-slate-700 mb-1.5">
          Were the questions what you expected for this level/profile?
        </p>
        <ScalePicker value={questionsMatch} onChange={setQuestionsMatch} labels={QUESTION_MATCH_OPTIONS} />
      </div>

      <div>
        <p className="text-xs font-medium text-slate-700 mb-1.5">
          How useful was the interviewer&apos;s feedback (per-question + overall debrief)?
        </p>
        <ScalePicker value={feedbackQuality} onChange={setFeedbackQuality} />
      </div>

      <div>
        <p className="text-xs font-medium text-slate-700 mb-1.5">
          Any suggestions for improving question quality or the overall experience?
          <span className="font-normal text-slate-400"> (optional)</span>
        </p>
        <textarea
          value={suggestions}
          onChange={(e) => setSuggestions(e.target.value)}
          rows={3}
          placeholder="What would make this better?"
          className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-300"
        />
      </div>

      <div>
        <p className="text-xs font-medium text-slate-700 mb-1.5">
          Would you use this again or recommend it to a colleague?
        </p>
        <div className="flex gap-2">
          {[
            { value: true, label: 'Yes' },
            { value: false, label: 'No' },
          ].map((opt) => (
            <button
              key={String(opt.value)}
              type="button"
              onClick={() => setWouldRecommend(opt.value)}
              className={cn(
                'rounded-lg border px-4 py-1.5 text-xs font-medium transition-colors',
                wouldRecommend === opt.value
                  ? 'border-emerald-500 bg-emerald-50 text-emerald-800'
                  : 'border-slate-200 bg-white text-slate-600 hover:border-emerald-300',
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-3 pt-1">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={submitting}
          className="rounded-lg bg-emerald-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-60"
        >
          {submitting ? 'Submitting…' : 'Submit feedback'}
        </button>
        <button
          type="button"
          onClick={() => dismissDebriefFeedback()}
          className="text-xs font-medium text-slate-500 hover:text-slate-700"
        >
          Skip
        </button>
      </div>
    </div>
  )
}
