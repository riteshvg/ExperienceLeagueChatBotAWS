import { create } from 'zustand'
import {
  fetchEducatorExams,
  getEducatorStatus,
  logEducatorSession,
  streamEducatorChat,
  type Message,
} from '@/lib/api'
import { generateReadinessReport } from '@/lib/readiness-report'
import { isVerificationMessage, parseQuestionFromMessage } from '@/lib/educator-parse'
import type { DomainScores, Exam, ReadinessReport, RovrMode } from '@/types/educator'

const EDUCATOR_SESSION_KEY = 'rovr_educator_session'

function makeId() {
  return Math.random().toString(36).slice(2)
}

function emptyDomainScores(exam: Exam): DomainScores {
  return Object.fromEntries(exam.domains.map((d) => [d.id, { correct: 0, total: 0 }]))
}

interface EducatorState {
  mode: RovrMode
  featureAvailable: boolean
  examId: string | null
  exam: Exam | null
  exams: Exam[]
  domainScores: DomainScores
  sessionStarted: number | null
  questionNumber: number
  pendingQuestionDomainId: string | null
  scoreReport: ReadinessReport | null
  showScorePanel: boolean
  isStreaming: boolean
  error: string | null

  init: () => Promise<void>
  loadExams: () => Promise<void>
  startExam: (examId: string) => Promise<string>
  exitEducatorMode: () => void
  handleDeepLink: (examId: string | null) => Promise<void>
  sendMessage: (
    query: string,
    chatSessionId: string,
    patchMessages: (updater: (msgs: Message[]) => Message[]) => void,
    getMessages: () => Message[],
  ) => Promise<void>
  submitAnswer: (
    answer: string,
    chatSessionId: string,
    patchMessages: (updater: (msgs: Message[]) => Message[]) => void,
    getMessages: () => Message[],
  ) => Promise<void>
  dismissScorePanel: () => void
  getStartupMessage: () => string
}

function persistEducatorSession(examId: string | null, domainScores: DomainScores, started: number | null) {
  if (!examId) {
    sessionStorage.removeItem(EDUCATOR_SESSION_KEY)
    return
  }
  sessionStorage.setItem(
    EDUCATOR_SESSION_KEY,
    JSON.stringify({ examId, domainScores, sessionStarted: started }),
  )
}

export const useEducatorStore = create<EducatorState>()((set, get) => ({
  mode: 'standard',
  featureAvailable: false,
  examId: null,
  exam: null,
  exams: [],
  domainScores: {},
  sessionStarted: null,
  questionNumber: 1,
  pendingQuestionDomainId: null,
  scoreReport: null,
  showScorePanel: false,
  isStreaming: false,
  error: null,

  async init() {
    const status = await getEducatorStatus()
    const available = !!(status?.enabled && status.is_admin)
    set({ featureAvailable: available })
    if (available) {
      await get().loadExams()
    }
  },

  async loadExams() {
    try {
      const exams = await fetchEducatorExams()
      set({ exams })
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
      domainScores,
      sessionStarted: started,
      questionNumber: 1,
      scoreReport: null,
      showScorePanel: false,
      pendingQuestionDomainId: null,
    })
    persistEducatorSession(examId, domainScores, started)

    return (
      `I'm preparing for the ${exam.id} exam (${exam.name}). ` +
      `Please ask me which certification I'm preparing for, then begin with the first practice question.`
    )
  },

  exitEducatorMode() {
    const { examId, domainScores, sessionStarted, questionNumber } = get()
    if (examId && sessionStarted) {
      logEducatorSession({
        examId,
        domainScores,
        questionsAsked: questionNumber - 1,
        sessionStarted,
        durationSecs: Math.round((Date.now() - sessionStarted) / 1000),
      })
    }
    persistEducatorSession(null, {}, null)
    set({
      mode: 'standard',
      examId: null,
      exam: null,
      domainScores: {},
      sessionStarted: null,
      questionNumber: 1,
      scoreReport: null,
      showScorePanel: false,
      pendingQuestionDomainId: null,
    })
  },

  async handleDeepLink(examId: string | null) {
    if (!examId || !get().featureAvailable) return
    const params = new URLSearchParams(window.location.search)
    if (params.get('mode') !== 'educator') return
    if (params.get('exam') !== examId && params.get('exam')) return
    const target = params.get('exam') ?? examId
    if (!target) return
    await get().startExam(target)
  },

  getStartupMessage() {
    const { exam } = get()
    if (!exam) return ''
    return (
      `Start my educator session for ${exam.id} — ${exam.name}. ` +
      `Introduce the exam briefly, then ask Question 1 weighted to the highest-priority domain.`
    )
  },

  dismissScorePanel() {
    set({ showScorePanel: false })
  },

  async sendMessage(query, chatSessionId, patchMessages, getMessages) {
    const state = get()
    if (state.mode !== 'educator' || !state.examId || !state.exam || state.isStreaming) return

    const trimmed = query.trim()
    if (!trimmed) return

    if (trimmed === '/quit' || trimmed === '/exit') {
      get().exitEducatorMode()
      patchMessages((msgs) => [
        ...msgs,
        { id: makeId(), role: 'user', content: trimmed },
        {
          id: makeId(),
          role: 'assistant',
          content:
            'Educator mode ended. You are back in standard Rovr mode — ask any Adobe documentation question.',
        },
      ])
      return
    }

    if (trimmed === '/score') {
      const report = generateReadinessReport(state.exam, state.domainScores)
      set({ scoreReport: report, showScorePanel: true })
      patchMessages((msgs) => [
        ...msgs,
        { id: makeId(), role: 'user', content: '/score' },
        {
          id: makeId(),
          role: 'assistant',
          content:
            `**Readiness report** — ${report.totalCorrect}/${report.totalAsked} correct (${report.overallPct}%). ` +
            `Verdict: **${report.verdict}** (passing benchmark: ${report.passingPct}%). ` +
            `See the score panel for per-domain breakdown.`,
        },
      ])
      return
    }

    await get().submitAnswer(trimmed, chatSessionId, patchMessages, getMessages)
  },

  async submitAnswer(query, chatSessionId, patchMessages, getMessages) {
    const {
      examId,
      exam,
      domainScores,
      questionNumber,
      pendingQuestionDomainId,
    } = get()
    if (!examId || !exam) return

    set({ isStreaming: true, error: null })

    const userMsg: Message = { id: makeId(), role: 'user', content: query }
    const assistantId = makeId()
    const assistantMsg: Message = { id: assistantId, role: 'assistant', content: '', streaming: true }

    patchMessages((msgs) => [...msgs, userMsg, assistantMsg])

    const history = getMessages()
      .filter((m) => m.id !== assistantId && !m.streaming)
      .map((m) => ({ role: m.role, content: m.content }))

    try {
      let nextDomainId = pendingQuestionDomainId

      for await (const event of streamEducatorChat(
        history,
        examId,
        chatSessionId,
        domainScores,
        questionNumber,
      )) {
        if (event.type === 'token') {
          patchMessages((msgs) =>
            msgs.map((m) =>
              m.id === assistantId ? { ...m, content: m.content + event.content } : m,
            ),
          )
        } else if (event.type === 'done') {
          nextDomainId = event.next_domain ?? nextDomainId
          patchMessages((msgs) =>
            msgs.map((m) =>
              m.id === assistantId ? { ...m, streaming: false, model: 'educator' } : m,
            ),
          )
        } else if (event.type === 'error') {
          set({ error: event.message })
          patchMessages((msgs) =>
            msgs.map((m) =>
              m.id === assistantId
                ? { ...m, content: `Error: ${event.message}`, streaming: false }
                : m,
            ),
          )
        }
      }

      const finalMsg = getMessages().find((m) => m.id === assistantId)
      const content = finalMsg?.content ?? ''

      let updatedScores = { ...get().domainScores }
      if (isVerificationMessage(content) && pendingQuestionDomainId) {
        const correct = content.trimStart().startsWith('✓')
        const prev = updatedScores[pendingQuestionDomainId] ?? { correct: 0, total: 0 }
        updatedScores = {
          ...updatedScores,
          [pendingQuestionDomainId]: {
            correct: prev.correct + (correct ? 1 : 0),
            total: prev.total + 1,
          },
        }
      }

      const parsed = parseQuestionFromMessage(content)
      const newPending = parsed ? (nextDomainId ?? pendingQuestionDomainId) : pendingQuestionDomainId
      const newQuestionNumber = parsed ? questionNumber + 1 : questionNumber

      set({
        domainScores: updatedScores,
        pendingQuestionDomainId: newPending,
        questionNumber: newQuestionNumber,
      })
      persistEducatorSession(examId, updatedScores, get().sessionStarted)

      if (newQuestionNumber > 0 && newQuestionNumber % 10 === 1 && parsed) {
        // checkpoint handled by LLM per system prompt
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      set({ error: msg })
    } finally {
      set({ isStreaming: false })
    }
  },
}))
