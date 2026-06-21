import { create } from 'zustand'
import {
  advanceInterviewerSession,
  editInterviewerAnswer,
  getInterviewerProfiles,
  getInterviewerReview,
  getInterviewerStatus,
  saveInterviewerAnswer,
  streamInterviewerStart,
  streamInterviewerSubmit,
} from '@/lib/api'
import type {
  InterviewLevel,
  InterviewPhase,
  InterviewQuestion,
  InterviewerProfiles,
  PendingAnswer,
  ReviewItem,
  SessionReport,
  EvaluationProgress,
} from '@/types/interviewer'

interface AnsweredItem {
  question: InterviewQuestion
  answer: string
}

interface InterviewerState {
  active: boolean
  featureAvailable: boolean
  adminOnly: boolean
  profiles: InterviewerProfiles | null
  sessionId: string | null
  level: InterviewLevel | null
  profileId: string | null
  profileLabel: string | null
  phase: InterviewPhase
  questionIndex: number
  totalQuestions: number
  completed: boolean
  isStreaming: boolean
  error: string | null
  setupOpen: boolean

  welcomeText: string
  currentQuestion: InterviewQuestion | null
  answerDraft: string
  pendingAnswer: PendingAnswer | null
  editingQuestionId: string | null
  answeredHistory: AnsweredItem[]
  reviewItems: ReviewItem[]
  sessionReport: SessionReport | null
  debriefContent: string
  debriefStreaming: boolean
  evaluationProgress: EvaluationProgress | null

  init: () => Promise<void>
  toggle: () => void
  openSetup: () => void
  closeSetup: () => void
  setAnswerDraft: (text: string) => void
  startSession: (level: InterviewLevel, profileId: string) => Promise<void>
  submitAnswer: (answer: string) => Promise<void>
  startEditAnswer: () => void
  cancelEdit: () => void
  startEditReviewAnswer: (questionId: string) => void
  advanceQuestion: () => Promise<void>
  submitForEvaluation: () => Promise<void>
  exitMode: () => void
}

export const useInterviewerStore = create<InterviewerState>()((set, get) => ({
  active: false,
  featureAvailable: false,
  adminOnly: true,
  profiles: null,
  sessionId: null,
  level: null,
  profileId: null,
  profileLabel: null,
  phase: 'questioning',
  questionIndex: 0,
  totalQuestions: 0,
  completed: false,
  isStreaming: false,
  error: null,
  setupOpen: false,

  welcomeText: '',
  currentQuestion: null,
  answerDraft: '',
  pendingAnswer: null,
  editingQuestionId: null,
  answeredHistory: [],
  reviewItems: [],
  sessionReport: null,
  debriefContent: '',
  debriefStreaming: false,
  evaluationProgress: null,

  async init() {
    try {
      const status = await getInterviewerStatus()
      set({ featureAvailable: status.available, adminOnly: status.admin_only })
      if (status.available) {
        const profiles = await getInterviewerProfiles()
        set({ profiles })
      }
    } catch {
      set({ featureAvailable: false })
    }
  },

  toggle() {
    const { active, featureAvailable } = get()
    if (!featureAvailable) return
    if (active) get().exitMode()
    else set({ active: true, setupOpen: true })
  },

  openSetup() {
    set({ setupOpen: true })
  },

  closeSetup() {
    set({ setupOpen: false })
  },

  setAnswerDraft(text) {
    set({ answerDraft: text })
  },

  exitMode() {
    set({
      active: false,
      sessionId: null,
      level: null,
      profileId: null,
      profileLabel: null,
      phase: 'questioning',
      questionIndex: 0,
      totalQuestions: 0,
      completed: false,
      isStreaming: false,
      error: null,
      setupOpen: false,
      welcomeText: '',
      currentQuestion: null,
      answerDraft: '',
      pendingAnswer: null,
      editingQuestionId: null,
      answeredHistory: [],
      reviewItems: [],
      sessionReport: null,
      debriefContent: '',
      debriefStreaming: false,
      evaluationProgress: null,
    })
  },

  async startSession(level, profileId) {
    set({
      isStreaming: true,
      error: null,
      setupOpen: false,
      level,
      profileId,
      phase: 'questioning',
      completed: false,
      welcomeText: '',
      currentQuestion: null,
      answerDraft: '',
      pendingAnswer: null,
      editingQuestionId: null,
      answeredHistory: [],
      reviewItems: [],
      sessionReport: null,
      debriefContent: '',
      debriefStreaming: false,
      evaluationProgress: null,
    })

    let welcome = ''

    try {
      for await (const event of streamInterviewerStart(level, profileId)) {
        if (event.type === 'token') {
          welcome += event.content
          set({ welcomeText: welcome })
        } else if (event.type === 'question') {
          set({ currentQuestion: event.question })
        } else if (event.type === 'done') {
          set({
            sessionId: event.session_id,
            profileLabel: event.profile_label ?? null,
            questionIndex: event.current_index ?? 0,
            totalQuestions: event.total_questions ?? 0,
            currentQuestion: event.current_question ?? get().currentQuestion,
          })
        } else if (event.type === 'error') {
          set({ error: event.message })
        }
      }
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to start interview' })
    } finally {
      set({ isStreaming: false })
    }
  },

  async submitAnswer(answer) {
    const {
      sessionId,
      isStreaming,
      phase,
      completed,
      editingQuestionId,
      pendingAnswer,
      reviewItems,
      currentQuestion,
      answeredHistory,
    } = get()
    if (!sessionId || isStreaming || completed) return

    const text = answer.trim()
    if (!text) return

    set({ isStreaming: true, error: null })

    try {
      if (phase === 'review' && editingQuestionId) {
        const result = await editInterviewerAnswer(sessionId, editingQuestionId, text)
        set({
          reviewItems: reviewItems.map((item) =>
            item.question.id === editingQuestionId ? { ...item, answer: result.answer } : item,
          ),
          editingQuestionId: null,
          answerDraft: '',
        })
        return
      }

      if (phase === 'answer_pending' && editingQuestionId && pendingAnswer) {
        const result = await editInterviewerAnswer(sessionId, editingQuestionId, text)
        set({
          pendingAnswer: { ...pendingAnswer, answer: result.answer },
          answeredHistory: answeredHistory.map((item) =>
            item.question.id === editingQuestionId ? { ...item, answer: result.answer } : item,
          ),
          editingQuestionId: null,
          answerDraft: '',
        })
        return
      }

      const result = await saveInterviewerAnswer(sessionId, text)
      const question = currentQuestion
      set({
        phase: 'answer_pending',
        pendingAnswer: {
          questionId: result.question_id,
          questionIndex: result.question_index,
          answer: result.answer,
          isLast: result.is_last,
        },
        answerDraft: '',
        answeredHistory:
          question
            ? [...answeredHistory, { question, answer: result.answer }]
            : answeredHistory,
      })
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to save answer' })
    } finally {
      set({ isStreaming: false })
    }
  },

  startEditAnswer() {
    const { pendingAnswer } = get()
    if (!pendingAnswer) return
    set({
      editingQuestionId: pendingAnswer.questionId,
      answerDraft: pendingAnswer.answer,
    })
  },

  cancelEdit() {
    set({ editingQuestionId: null, answerDraft: '' })
  },

  startEditReviewAnswer(questionId) {
    const item = get().reviewItems.find((i) => i.question.id === questionId)
    set({
      editingQuestionId: questionId,
      answerDraft: item?.answer ?? '',
    })
  },

  async advanceQuestion() {
    const { sessionId, isStreaming, pendingAnswer } = get()
    if (!sessionId || isStreaming || !pendingAnswer) return

    set({ isStreaming: true, error: null })

    try {
      const result = await advanceInterviewerSession(sessionId)

      if (result.phase === 'review' || result.review_ready) {
        const review = await getInterviewerReview(sessionId)
        set({
          phase: 'review',
          pendingAnswer: null,
          editingQuestionId: null,
          answerDraft: '',
          currentQuestion: null,
          reviewItems: review.items,
          questionIndex: review.current_index,
        })
        return
      }

      if (result.current_question) {
        set({
          phase: 'questioning',
          pendingAnswer: null,
          editingQuestionId: null,
          answerDraft: '',
          currentQuestion: result.current_question,
          questionIndex: result.current_index ?? get().questionIndex,
        })
      }
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to advance' })
    } finally {
      set({ isStreaming: false })
    }
  },

  async submitForEvaluation() {
    const { sessionId, isStreaming, reviewItems } = get()
    if (!sessionId || isStreaming) return

    const initialProgress: EvaluationProgress = {
      total: reviewItems.length,
      completed: 0,
      step: 'grading',
      questionResults: reviewItems.map((item) => ({
        question_id: item.question.id,
        question_index: item.question.index ?? 0,
        status: 'pending' as const,
      })),
    }

    set({
      isStreaming: true,
      error: null,
      phase: 'evaluating',
      debriefContent: '',
      debriefStreaming: true,
      sessionReport: null,
      evaluationProgress: initialProgress,
    })

    let report: SessionReport | null = null

    try {
      for await (const event of streamInterviewerSubmit(sessionId)) {
        if (event.type === 'evaluating') {
          set((s) => ({
            debriefContent: event.message,
            evaluationProgress: s.evaluationProgress
              ? {
                  ...s.evaluationProgress,
                  total: event.total ?? s.evaluationProgress.total,
                }
              : s.evaluationProgress,
          }))
        } else if (event.type === 'evaluation_progress') {
          if ('step' in event && event.step === 'synthesis') {
            set((s) => ({
              evaluationProgress: s.evaluationProgress
                ? { ...s.evaluationProgress, step: 'synthesis', completed: s.evaluationProgress.total }
                : s.evaluationProgress,
            }))
          } else if ('status' in event) {
            set((s) => {
              const prog = s.evaluationProgress
              if (!prog) return {}
              const results = prog.questionResults.map((q) => {
                if (q.question_index !== event.question_index) return q
                if (event.status === 'evaluating') {
                  return { ...q, status: 'evaluating' as const }
                }
                return {
                  ...q,
                  status: 'done' as const,
                  score: 'score' in event ? event.score : q.score,
                }
              })
              const completed = results.filter((q) => q.status === 'done').length
              return {
                evaluationProgress: {
                  ...prog,
                  completed,
                  questionResults: results,
                },
              }
            })
          }
        } else if (event.type === 'token') {
          set((s) => ({ debriefContent: s.debriefContent + event.content }))
        } else if (event.type === 'session_report') {
          report = event
          set({
            sessionReport: event,
            evaluationProgress: get().evaluationProgress
              ? { ...get().evaluationProgress!, step: 'complete', completed: get().evaluationProgress!.total }
              : null,
          })
        } else if (event.type === 'session_complete') {
          set({ completed: true, phase: 'complete' })
        } else if (event.type === 'error') {
          set({ error: event.message, phase: 'review', evaluationProgress: null })
        }
      }
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Evaluation failed', phase: 'review', evaluationProgress: null })
    } finally {
      set({
        isStreaming: false,
        debriefStreaming: false,
        sessionReport: report ?? get().sessionReport,
      })
    }
  },
}))
