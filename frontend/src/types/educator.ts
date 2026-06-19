export type ExamLevel = 'Professional' | 'Expert' | 'Master'

export type ExamDomain = {
  id: string
  name: string
  weightPct: number
  docSearchHint: string
  conceptAnchors: string[]
}

export type Exam = {
  id: string
  name: string
  product: string
  level: ExamLevel
  totalQuestions: number
  passingScore: number
  timeLimitMins: number
  domains: ExamDomain[]
}

export type AttemptRecord = {
  answer: string
  correct: boolean
  timestamp: number
}

export type DocCitation = {
  title: string
  url: string
  section: string
}

export type QuestionRecord = {
  questionId: string
  messageId: string
  domain: string
  domainId: string
  questionText: string
  options: string[]
  correctAnswer?: string
  docCitation?: DocCitation
  attempts: AttemptRecord[]
  skipped: boolean
  resolved: boolean
  deepenedWith?: string
}

export type DomainScores = Record<string, { correct: number; total: number; skipped: number }>

export type QuestionCardPhase =
  | 'posed'
  | 'hinted'
  | 'doc-shown'
  | 'wrong'
  | 'correct'
  | 'revealed'
  | 'skipped'

export type ReadinessReport = {
  overallPct: number
  firstTryPct: number
  passingPct: number
  totalCorrect: number
  totalResolved: number
  totalSkipped: number
  totalAsked: number
  verdict: 'Ready to attempt' | 'Almost there' | 'Keep going'
  domainReports: {
    domain: string
    domainId: string
    correct: number
    total: number
    skipped: number
    pct: number
    weak: boolean
    docSearchHint: string
  }[]
  skippedQuestions: {
    questionId: string
    domainId: string
    questionText: string
    domain: string
  }[]
}

export type RovrMode = 'standard' | 'educator'

export type DeepenAction = {
  type: 'explore' | 'usecase' | 'next'
  label: string
  prompt: string
}
