export type ExamLevel = 'Professional' | 'Expert' | 'Master'

export type ExamDomain = {
  id: string
  name: string
  weightPct: number
  docSearchHint: string
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

export type QuestionRecord = {
  questionId: string
  domain: string
  domainId: string
  questionText: string
  options: string[]
  correctAnswer: string
  docCitation: string
  candidateAnswer: string | null
  correct: boolean | null
  timestamp: number
}

export type DomainScores = Record<string, { correct: number; total: number }>

export type EducatorSession = {
  examId: string
  exam: Exam | null
  questionsAsked: QuestionRecord[]
  domainScores: DomainScores
  sessionStarted: number
  active: boolean
  questionNumber: number
}

export type ReadinessReport = {
  overallPct: number
  passingPct: number
  totalCorrect: number
  totalAsked: number
  verdict: 'Ready' | 'Almost ready' | 'Needs more prep'
  domainReports: {
    domain: string
    domainId: string
    correct: number
    total: number
    pct: number
    weak: boolean
    docSearchHint: string
  }[]
}

export type RovrMode = 'standard' | 'educator'
