import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ChevronDown, ChevronRight, Pencil, ChevronRight as NextIcon, ClipboardList, XCircle, Info } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useInterviewerStore } from '@/store/interviewerStore'
import { InterviewHeaderBar } from './InterviewHeaderBar'
import { InterviewQuestionCard } from './InterviewQuestionCard'
import { InterviewAnswerEditor } from './InterviewAnswerEditor'
import { InterviewAnswerPreview } from './InterviewAnswerPreview'
import { InterviewSessionReview } from './InterviewSessionReview'
import { InterviewSessionReport } from './InterviewSessionReport'
import { InterviewEvaluationProgress } from './InterviewEvaluationProgress'
import { InterviewFeedbackForm } from './InterviewFeedbackForm'

export function InterviewWorkspace() {
  const {
    welcomeText,
    currentQuestion,
    answerDraft,
    setAnswerDraft,
    markVoiceInputUsed,
    sessionId,
    phase,
    pendingAnswer,
    answeredHistory,
    isStreaming,
    editingQuestionId,
    reviewItems,
    sessionReport,
    debriefContent,
    debriefStreaming,
    evaluationProgress,
    endedEarly,
    level,
    profileLabel,
    createdAt,
    questionIndex,
    totalQuestions,
    submitAnswer,
    startEditAnswer,
    cancelEdit,
    advanceQuestion,
    endInterview,
    startEditReviewAnswer,
    submitForEvaluation,
  } = useInterviewerStore()

  const [historyOpen, setHistoryOpen] = useState(false)
  // Expanded by default only on first view of a session (question 1); collapsed
  // by default afterward. Once mounted, the user's own toggling takes over —
  // this only decides the *initial* state.
  const [introOpen, setIntroOpen] = useState(() => questionIndex === 0)
  // Auto-minimize the instant the candidate answers question 1 (pendingAnswer
  // appears while still on question 1) — fires once, then leaves any later
  // manual toggling alone.
  const hasAutoCollapsedIntro = useRef(false)
  useEffect(() => {
    const answeredFirstQuestion = questionIndex === 0 && pendingAnswer !== null
    if (!hasAutoCollapsedIntro.current && (answeredFirstQuestion || questionIndex > 0)) {
      hasAutoCollapsedIntro.current = true
      setIntroOpen(false)
    }
  }, [questionIndex, pendingAnswer])
  const isEditingPending =
    phase === 'answer_pending' && editingQuestionId === pendingAnswer?.questionId

  const originalAnswer = editingQuestionId
    ? phase === 'review'
      ? reviewItems.find((i) => i.question.id === editingQuestionId)?.answer ?? null
      : pendingAnswer?.answer ?? null
    : null

  const handleSave = () => {
    void submitAnswer(answerDraft)
  }

  const handleEndInterview = () => {
    const hasAnyAnswer = answeredHistory.length > 0 || (pendingAnswer?.answer.trim() ?? '')
    const confirmMessage = hasAnyAnswer
      ? "End the interview now? You'll be graded only on the questions you've already answered."
      : 'End the interview now? You need at least one answered question to get a report.'
    if (window.confirm(confirmMessage)) {
      void endInterview()
    }
  }

  const showEditor =
    phase === 'questioning' ||
    isEditingPending ||
    (phase === 'review' && !!editingQuestionId)

  const canEndInterview = phase === 'questioning' || phase === 'answer_pending'

  const showHowThisWorks = Boolean(welcomeText) && phase !== 'complete'

  return (
    <div className="max-w-5xl mx-auto w-full grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_260px] gap-4 items-start">
      <div className="space-y-4 min-w-0">
      <InterviewHeaderBar
        level={level}
        profileLabel={profileLabel}
        phase={phase}
        createdAt={createdAt}
        questionIndex={questionIndex}
        totalQuestions={totalQuestions}
      />

      {showHowThisWorks && (
        <details
          open={introOpen}
          onToggle={(e) => setIntroOpen(e.currentTarget.open)}
          className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 lg:hidden"
        >
          <summary className="flex items-center gap-1.5 text-sm font-medium text-slate-600 cursor-pointer select-none [&::-webkit-details-marker]:hidden">
            <Info className="w-3.5 h-3.5 text-slate-400" />
            How this works
          </summary>
          <div className="prose prose-sm max-w-none text-slate-700 mt-3">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{welcomeText}</ReactMarkdown>
          </div>
        </details>
      )}

      {answeredHistory.length > 0 && phase !== 'review' && phase !== 'complete' && (
        <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
          <button
            type="button"
            onClick={() => setHistoryOpen((o) => !o)}
            className="w-full flex items-center gap-2 px-4 py-2.5 text-left text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            {historyOpen ? (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronRight className="w-4 h-4 text-slate-400" />
            )}
            Previous answers ({answeredHistory.length})
          </button>
          {historyOpen && (
            <div className="border-t border-slate-100 divide-y divide-slate-100">
              {answeredHistory.map((item) => (
                <div key={item.question.id} className="px-4 py-3 space-y-2">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                    Q{item.question.index} · {item.question.topic.replace(/_/g, ' ')}
                  </p>
                  <p className="text-sm font-medium text-slate-800">{item.question.question}</p>
                  <InterviewAnswerPreview answer={item.answer} />
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {(phase === 'questioning' || phase === 'answer_pending') && currentQuestion && (
        <InterviewQuestionCard question={currentQuestion} />
      )}

      {phase === 'answer_pending' && pendingAnswer && !isEditingPending && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-wide text-emerald-800">
              Your answer · Q{pendingAnswer.questionIndex}
            </p>
            <button
              type="button"
              onClick={startEditAnswer}
              disabled={isStreaming}
              className="inline-flex items-center gap-1 text-xs text-emerald-700 hover:underline disabled:opacity-50"
            >
              <Pencil className="w-3 h-3" />
              Edit
            </button>
          </div>
          <InterviewAnswerPreview answer={pendingAnswer.answer} />
          {pendingAnswer.followUp && (
            <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              This answer could use more depth — a follow-up question is next.
            </p>
          )}
          <div className="flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={handleEndInterview}
              disabled={isStreaming}
              className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-red-600 disabled:opacity-50"
            >
              <XCircle className="w-3.5 h-3.5" />
              End interview
            </button>
            <button
              type="button"
              onClick={() => void advanceQuestion()}
              disabled={isStreaming}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-700 text-sm font-medium text-white hover:bg-emerald-800 disabled:opacity-50"
            >
              {pendingAnswer.isLast ? (
                <>
                  <ClipboardList className="w-4 h-4" />
                  Review all answers
                </>
              ) : (
                <>
                  {pendingAnswer.followUp ? 'Next: follow-up question' : 'Next question'}
                  <NextIcon className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {showEditor && (
        <div className="space-y-3">
          {phase === 'review' && editingQuestionId && (
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Editing answer
            </p>
          )}
          {editingQuestionId && originalAnswer !== null && (
            <div className="space-y-1.5">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                Your original answer (read-only, for reference)
              </p>
              <div className="opacity-70 pointer-events-none">
                <InterviewAnswerPreview answer={originalAnswer} />
              </div>
            </div>
          )}
          <InterviewAnswerEditor
            value={answerDraft}
            onChange={setAnswerDraft}
            disabled={isStreaming}
            sessionId={sessionId}
            onVoiceInputUsed={markVoiceInputUsed}
          />
          <div className="flex flex-wrap items-center justify-between gap-2">
            {canEndInterview ? (
              <button
                type="button"
                onClick={handleEndInterview}
                disabled={isStreaming}
                className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-red-600 disabled:opacity-50"
              >
                <XCircle className="w-3.5 h-3.5" />
                End interview
              </button>
            ) : (
              <span />
            )}
            <div className="flex gap-2">
              {(isEditingPending || (phase === 'review' && editingQuestionId)) && (
                <button
                  type="button"
                  onClick={cancelEdit}
                  className="px-4 py-2 text-sm text-slate-600 hover:text-slate-800"
                >
                  Cancel
                </button>
              )}
              <button
                type="button"
                onClick={handleSave}
                disabled={isStreaming || !answerDraft.trim()}
                className={cn(
                  'px-4 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-50',
                  phase === 'review' ? 'bg-slate-700 hover:bg-slate-800' : 'bg-emerald-700 hover:bg-emerald-800',
                )}
              >
                {phase === 'review'
                  ? 'Update answer'
                  : isEditingPending
                    ? 'Save changes'
                    : 'Save answer'}
              </button>
            </div>
          </div>
        </div>
      )}

      {phase === 'review' && reviewItems.length > 0 && !editingQuestionId && (
        <InterviewSessionReview
          items={reviewItems}
          onEdit={startEditReviewAnswer}
          onSubmit={() => void submitForEvaluation()}
          disabled={isStreaming}
          allAnswered={reviewItems.every((i) => i.answer.trim())}
          endedEarly={endedEarly}
        />
      )}

      {phase === 'evaluating' && evaluationProgress && (
        <InterviewEvaluationProgress progress={evaluationProgress} />
      )}

      {sessionReport && (
        <InterviewSessionReport
          report={sessionReport}
          debriefContent={debriefContent}
          debriefStreaming={debriefStreaming}
          level={level}
          profileLabel={profileLabel}
        />
      )}

      {sessionReport && !debriefStreaming && <InterviewFeedbackForm />}
      </div>

      {showHowThisWorks && (
        <div className="hidden lg:flex lg:flex-col lg:gap-2 sticky top-4">
          <details className="rounded-xl border border-slate-200 bg-white px-4 py-3">
            <summary className="flex items-center gap-1.5 text-sm font-medium text-slate-600 cursor-pointer select-none [&::-webkit-details-marker]:hidden">
              <Info className="w-3.5 h-3.5 text-slate-400" />
              How this works
            </summary>
            <div className="prose prose-sm max-w-none text-slate-700 mt-3">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{welcomeText}</ReactMarkdown>
            </div>
          </details>
          <details className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-[11px] text-slate-400">
            <summary className="cursor-pointer select-none hover:text-slate-500 [&::-webkit-details-marker]:hidden">
              Disclaimer
            </summary>
            <p className="mt-1 leading-snug">
              This is AI-generated interview guidance for practice purposes only — questions, feedback, and
              scoring may be imperfect and should not be taken as a literal or authoritative assessment.
            </p>
          </details>
        </div>
      )}
    </div>
  )
}
