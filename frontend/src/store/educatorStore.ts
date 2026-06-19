import { create } from 'zustand'
import {
  fetchEducatorExams,
  getEducatorStatus,
  logEducatorSession,
  streamEducatorChat,
  type Message,
} from '@/lib/api'
import {
  emptyDomainScores,
  generateReadinessReport,
  syncDomainScoresFromQuestions,
} from '@/lib/readiness-report'
import {
  isCorrectResponse,
  isRevealedResponse,
  isSkipAcknowledged,
  parseDocCitation,
  parseQuestionFromMessage,
} from '@/lib/educator-parse'
import type {
  DeepenAction,
  DomainScores,
  Exam,
  QuestionRecord,
  ReadinessReport,
  RovrMode,
} from '@/types/educator'

const EDUCATOR_SESSION_KEY = 'rovr_educator_session'

function makeId() {
  return Math.random().toString(36).slice(2)
}

type PatchFn = (updater: (msgs: Message[]) => Message[]) => void
type GetMsgsFn = () => Message[]

interface EducatorState {
  mode: RovrMode
  featureAvailable: boolean
  examId: string | null
  exam: Exam | null
  exams: Exam[]
  questions: QuestionRecord[]
  domainScores: DomainScores
  revisitQueue: string[]
  activeDomainId: string | null
  currentQuestionId: string | null
  sessionStarted: number | null
  questionNumber: number
  scoreReport: ReadinessReport | null
  showScorePanel: boolean
  isStreaming: boolean
  error: string | null

  init: () => Promise<void>
  loadExams: () => Promise<void>
  startExam: (examId: string) => Promise<void>
  exitEducatorMode: () => void
  sendMessage: (query: string, chatSessionId: string, patch: PatchFn, getMsgs: GetMsgsFn) => Promise<void>
  requestHint: (chatSessionId: string, patch: PatchFn, getMsgs: GetMsgsFn) => Promise<void>
  requestDoc: (chatSessionId: string, patch: PatchFn, getMsgs: GetMsgsFn) => Promise<void>
  submitAnswer: (answer: string, chatSessionId: string, patch: PatchFn, getMsgs: GetMsgsFn) => Promise<void>
  skipQuestion: (chatSessionId: string, patch: PatchFn, getMsgs: GetMsgsFn) => Promise<void>
  deepen: (action: DeepenAction, chatSessionId: string, patch: PatchFn, getMsgs: GetMsgsFn) => Promise<void>
  getQuestionForMessage: (messageId: string) => QuestionRecord | undefined
  dismissScorePanel: () => void
  getStartupMessage: () => string
}

function persistSession(state: Pick<EducatorState, 'examId' | 'domainScores' | 'sessionStarted' | 'questions'>) {
  if (!state.examId) {
    sessionStorage.removeItem(EDUCATOR_SESSION_KEY)
    return
  }
  sessionStorage.setItem(
    EDUCATOR_SESSION_KEY,
    JSON.stringify({
      examId: state.examId,
      domainScores: state.domainScores,
      sessionStarted: state.sessionStarted,
      questions: state.questions,
    }),
  )
}

export const useEducatorStore = create<EducatorState>()((set, get) => ({
  mode: 'standard',
  featureAvailable: false,
  examId: null,
  exam: null,
  exams: [],
  questions: [],
  domainScores: {},
  revisitQueue: [],
  activeDomainId: null,
  currentQuestionId: null,
  sessionStarted: null,
  questionNumber: 1,
  scoreReport: null,
  showScorePanel: false,
  isStreaming: false,
  error: null,

  async init() {
    const status = await getEducatorStatus()
    set({ featureAvailable: !!(status?.enabled && status.is_admin) })
    if (status?.enabled && status.is_admin) await get().loadExams()
  },

  async loadExams() {
    try {
      set({ exams: await fetchEducatorExams() })
    } catch {
      set({ exams: [] })
    }
  },

  async startExam(examId: string) {
    const exam = get().exams.find((e) => e.id === examId) ?? null
    if (!exam) throw new Error('Unknown exam')

    const started = Date.now()
    const domainScores = emptyDomainScores(exam)
    set({
      mode: 'educator',
      examId,
      exam,
      questions: [],
      domainScores,
      revisitQueue: [],
      activeDomainId: null,
      currentQuestionId: null,
      sessionStarted: started,
      questionNumber: 1,
      scoreReport: null,
      showScorePanel: false,
    })
    persistSession(get())
  },

  exitEducatorMode() {
    const { examId, questions, sessionStarted, questionNumber } = get()
    if (examId && sessionStarted) {
      logEducatorSession({
        examId,
        domainScores: syncDomainScoresFromQuestions(get().exam!, questions),
        questionsAsked: questionNumber - 1,
        sessionStarted,
        durationSecs: Math.round((Date.now() - sessionStarted) / 1000),
      })
    }
    sessionStorage.removeItem(EDUCATOR_SESSION_KEY)
    set({
      mode: 'standard',
      examId: null,
      exam: null,
      questions: [],
      domainScores: {},
      revisitQueue: [],
      activeDomainId: null,
      currentQuestionId: null,
      sessionStarted: null,
      questionNumber: 1,
      scoreReport: null,
      showScorePanel: false,
    })
  },

  getStartupMessage() {
    const { exam } = get()
    if (!exam) return ''
    return (
      `Start my educator session for ${exam.id} — ${exam.name}. ` +
      `You are my teacher, not an examiner. Open with why the first domain concept matters in practice, ` +
      `then pose Question 1 with [Give me a hint] and [Show me the doc first] available before I answer.`
    )
  },

  dismissScorePanel() {
    set({ showScorePanel: false })
  },

  getQuestionForMessage(messageId: string) {
    return get().questions.find((q) => q.messageId === messageId)
  },

  async sendMessage(query, chatSessionId, patch, getMsgs) {
    const state = get()
    if (state.mode !== 'educator' || !state.examId || !state.exam || state.isStreaming) return

    const trimmed = query.trim()
    if (!trimmed) return

    const cmd = trimmed.toLowerCase()
    if (cmd === '/quit' || cmd === '/exit') {
      get().exitEducatorMode()
      patch((msgs) => [
        ...msgs,
        { id: makeId(), role: 'user', content: trimmed },
        {
          id: makeId(),
          role: 'assistant',
          content: 'Educator mode ended. You are back in standard Rovr — ask any Adobe documentation question.',
        },
      ])
      return
    }

    if (cmd === '/score') {
      const report = generateReadinessReport(state.exam, state.questions)
      set({ scoreReport: report, showScorePanel: true })
      patch((msgs) => [
        ...msgs,
        { id: makeId(), role: 'user', content: '/score' },
        {
          id: makeId(),
          role: 'assistant',
          content:
            `**Readiness report** — first-try ${report.firstTryPct}% · overall ${report.overallPct}% ` +
            `(${report.totalCorrect}/${report.totalResolved} resolved). Verdict: **${report.verdict}**. ` +
            `See the score panel for domain breakdown and revisit queue.`,
        },
      ])
      return
    }

    if (cmd === '/hint') return get().requestHint(chatSessionId, patch, getMsgs)
    if (cmd === '/doc') return get().requestDoc(chatSessionId, patch, getMsgs)
    if (cmd === '/skip') return get().skipQuestion(chatSessionId, patch, getMsgs)

    if (cmd === '/revisit') {
      const skipped = state.questions.filter((q) => q.skipped)
      const list =
        skipped.length === 0
          ? 'No skipped questions yet.'
          : skipped.map((q, i) => `${i + 1}. ${q.domain}: ${q.questionText.slice(0, 80)}…`).join('\n')
      patch((msgs) => [
        ...msgs,
        { id: makeId(), role: 'user', content: '/revisit' },
        { id: makeId(), role: 'assistant', content: `**Revisit queue**\n\n${list}` },
      ])
      return
    }

    await get().submitAnswer(trimmed, chatSessionId, patch, getMsgs)
  },

  async requestHint(chatSessionId, patch, getMsgs) {
    await get().submitAnswer('Give me a hint', chatSessionId, patch, getMsgs)
  },

  async requestDoc(chatSessionId, patch, getMsgs) {
    await get().submitAnswer('Show me the doc first', chatSessionId, patch, getMsgs)
  },

  async skipQuestion(chatSessionId, patch, getMsgs) {
    const { currentQuestionId, questions, exam } = get()
    if (currentQuestionId && exam) {
      const updated = questions.map((q) =>
        q.questionId === currentQuestionId ? { ...q, skipped: true, resolved: false } : q,
      )
      const domainScores = syncDomainScoresFromQuestions(exam, updated)
      set({ questions: updated, domainScores, currentQuestionId: null })
      persistSession(get())
    }
    await get().submitAnswer('Skip (I will come back to this)', chatSessionId, patch, getMsgs)
  },

  async deepen(action, chatSessionId, patch, getMsgs) {
    if (action.type === 'next') {
      set({ currentQuestionId: null })
      await get().submitAnswer('Next question', chatSessionId, patch, getMsgs)
      return
    }
    await get().submitAnswer(action.prompt, chatSessionId, patch, getMsgs)
  },

  async submitAnswer(query, chatSessionId, patch, getMsgs) {
    const state = get()
    const { examId, exam, questions, questionNumber, activeDomainId, currentQuestionId } = state
    if (!examId || !exam) return

    const isAnswerChoice =
      /^I choose [A-D]$/i.test(query.trim()) || /^[A-D]$/i.test(query.trim())
    let workingQuestions = [...questions]

    if (isAnswerChoice && currentQuestionId) {
      const letter = (query.match(/[A-D]/i)?.[0] ?? query).toUpperCase()
      workingQuestions = workingQuestions.map((q) =>
        q.questionId === currentQuestionId
          ? {
              ...q,
              attempts: [
                ...q.attempts,
                { answer: letter, correct: false, timestamp: Date.now() },
              ],
            }
          : q,
      )
      set({ questions: workingQuestions })
    }

    set({ isStreaming: true, error: null })

    const userMsg: Message = { id: makeId(), role: 'user', content: query }
    const assistantId = makeId()
    patch((msgs) => [
      ...msgs,
      userMsg,
      { id: assistantId, role: 'assistant', content: '', streaming: true },
    ])

    const currentQ = workingQuestions.find((q) => q.questionId === currentQuestionId) ?? null
    const history = getMsgs()
      .filter((m) => m.id !== assistantId && !m.streaming)
      .map((m) => ({ role: m.role, content: m.content }))

    try {
      let nextDomainId = activeDomainId

      for await (const event of streamEducatorChat({
        messages: history,
        examId,
        sessionId: chatSessionId,
        domainScores: syncDomainScoresFromQuestions(exam, workingQuestions),
        questionNumber,
        currentQuestion: currentQ
          ? {
              questionId: currentQ.questionId,
              domainId: currentQ.domainId,
              attempts: currentQ.attempts,
              skipped: currentQ.skipped,
              resolved: currentQ.resolved,
            }
          : null,
        activeDomainId: activeDomainId ?? undefined,
      })) {
        if (event.type === 'token') {
          patch((msgs) =>
            msgs.map((m) =>
              m.id === assistantId ? { ...m, content: m.content + event.content } : m,
            ),
          )
        } else if (event.type === 'done') {
          nextDomainId = event.active_domain ?? event.next_domain ?? nextDomainId
          patch((msgs) =>
            msgs.map((m) =>
              m.id === assistantId ? { ...m, streaming: false, model: 'educator' } : m,
            ),
          )
        } else if (event.type === 'error') {
          set({ error: event.message })
          patch((msgs) =>
            msgs.map((m) =>
              m.id === assistantId
                ? { ...m, content: `Error: ${event.message}`, streaming: false }
                : m,
            ),
          )
        }
      }

      const content = getMsgs().find((m) => m.id === assistantId)?.content ?? ''
      let updatedQuestions = [...get().questions]

      const parsed = parseQuestionFromMessage(content)
      if (parsed && !currentQuestionId) {
        const qid = makeId()
        updatedQuestions = [
          ...updatedQuestions,
          {
            questionId: qid,
            messageId: assistantId,
            domain: parsed.domain,
            domainId: nextDomainId ?? '',
            questionText: parsed.text,
            options: parsed.options.map((o) => `${o.key}. ${o.label}`),
            attempts: [],
            skipped: false,
            resolved: false,
          },
        ]
        set({ currentQuestionId: qid, activeDomainId: nextDomainId })
      }

      if (currentQuestionId) {
        updatedQuestions = updatedQuestions.map((q) => {
          if (q.questionId !== currentQuestionId) return q

          let attempts = [...q.attempts]
          if (isAnswerChoice && attempts.length > 0) {
            const last = attempts[attempts.length - 1]
            attempts[attempts.length - 1] = {
              ...last,
              correct: isCorrectResponse(content),
            }
          }

          const docPreview = parseDocCitation(content, 'preview')
          const docCite = parseDocCitation(content, 'citation')
          const resolved =
            isCorrectResponse(content) ||
            isRevealedResponse(content) ||
            isSkipAcknowledged(content)

          if (isSkipAcknowledged(content)) {
            return { ...q, skipped: true, resolved: false, attempts }
          }

          return {
            ...q,
            attempts,
            resolved,
            docCitation: docCite ?? docPreview ?? q.docCitation,
          }
        })

        if (isCorrectResponse(content) || isRevealedResponse(content)) {
          set({ currentQuestionId: null, questionNumber: questionNumber + 1 })
        }
      }

      const domainScores = syncDomainScoresFromQuestions(exam, updatedQuestions)
      set({
        questions: updatedQuestions,
        domainScores,
        activeDomainId: nextDomainId,
      })
      persistSession(get())
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) })
    } finally {
      set({ isStreaming: false })
    }
  },
}))
