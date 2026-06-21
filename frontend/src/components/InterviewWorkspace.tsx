import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ChevronDown, ChevronRight, Pencil, ChevronRight as NextIcon, ClipboardList } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useInterviewerStore } from '@/store/interviewerStore'
import { InterviewQuestionCard } from './InterviewQuestionCard'
import { InterviewAnswerEditor } from './InterviewAnswerEditor'
import { InterviewAnswerPreview } from './InterviewAnswerPreview'
import { InterviewSessionReview } from './InterviewSessionReview'
import { InterviewSessionReport } from './InterviewSessionReport'
import { InterviewEvaluationProgress } from './InterviewEvaluationProgress'

export function InterviewWorkspace() {
  const {
    welcomeText,
    currentQuestion,
    answerDraft,
    setAnswerDraft,
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
    submitAnswer,
    startEditAnswer,
    cancelEdit,
    advanceQuestion,
    startEditReviewAnswer,
    submitForEvaluation,
  } = useInterviewerStore()

  const [historyOpen, setHistoryOpen] = useState(false)
  const isEditingPending =
    phase === 'answer_pending' && editingQuestionId === pendingAnswer?.questionId

  const handleSave = () => {
    void submitAnswer(answerDraft)
  }

  const showEditor =
    phase === 'questioning' ||
    isEditingPending ||
    (phase === 'review' && !!editingQuestionId)

  return (
    <div className="space-y-4 max-w-3xl mx-auto w-full">
      {welcomeText && (
        <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
          <div className="prose prose-sm max-w-none text-slate-800">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{welcomeText}</ReactMarkdown>
          </div>
        </div>
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
          <div className="flex justify-end">
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
                  Next question
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
          <InterviewAnswerEditor
            value={answerDraft}
            onChange={setAnswerDraft}
            disabled={isStreaming}
          />
          <div className="flex flex-wrap gap-2 justify-end">
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
      )}

      {phase === 'review' && reviewItems.length > 0 && !editingQuestionId && (
        <InterviewSessionReview
          items={reviewItems}
          onEdit={startEditReviewAnswer}
          onSubmit={() => void submitForEvaluation()}
          disabled={isStreaming}
          allAnswered={reviewItems.every((i) => i.answer.trim())}
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
        />
      )}
    </div>
  )
}
