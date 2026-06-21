export type InterviewLevel = 'junior' | 'senior' | 'architect' | 'principal'

export type InterviewPhase = 'questioning' | 'answer_pending' | 'review' | 'evaluating' | 'complete'

export type ProfileOption = {
  id: string
  label: string
  description?: string
  short?: string
}

export type InterviewQuestion = {
  id: string
  question: string
  topic: string
  difficulty: number
  expected_themes: string[]
  index?: number
  total?: number
}

export type InterviewEvaluation = {
  question_id: string
  question_index: number
  score: number
  score_pct: number
  strengths: string[]
  gaps: string[]
  model_answer_outline: string
  citations: Array<{
    url: string
    title: string
    product?: string
    score?: number
  }>
}

export type ReviewItem = {
  question: InterviewQuestion
  answer: string
}

export type EvaluationProgress = {
  total: number
  completed: number
  step: 'grading' | 'synthesis' | 'complete'
  questionResults: Array<{
    question_id: string
    question_index: number
    status: 'pending' | 'evaluating' | 'done'
    score?: number
  }>
}

export type SessionReport = {
  overall_score: number
  readiness: string
  readiness_summary: string
  strengths: string[]
  priority_gaps: string[]
  mistakes_to_avoid: string[]
  topics_to_read: Array<{ topic: string; reason: string }>
  overall_feedback: string
  per_question: Array<
    InterviewEvaluation & {
      question: string
      topic: string
      answer: string
      feedback?: string
    }
  >
  citations: Array<{
    url: string
    title: string
    product?: string
    score?: number
  }>
}

export type PendingAnswer = {
  questionId: string
  questionIndex: number
  answer: string
  isLast: boolean
}

export type InterviewerMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  question?: InterviewQuestion
  streaming?: boolean
}

export type InterviewerStatus = {
  enabled: boolean
  admin_only: boolean
  available: boolean
  is_admin: boolean
}

export type InterviewerProfiles = {
  levels: ProfileOption[]
  solutions: ProfileOption[]
  collections: ProfileOption[]
  combinations: Array<{ level: InterviewLevel; profile_id: string }>
}

export type InterviewerSessionInfo = {
  session_id: string
  level: InterviewLevel
  profile_id: string
  profile_label: string
  current_index: number
  total_questions: number
  phase: InterviewPhase
  awaiting_advance: boolean
  completed: boolean
  evaluated: boolean
  current_question: InterviewQuestion | null
}

export type InterviewerSSEEvent =
  | { type: 'token'; content: string }
  | { type: 'question'; question: InterviewQuestion }
  | { type: 'evaluating'; message: string; total?: number }
  | {
      type: 'evaluation_progress'
      question_index: number
      total: number
      status: 'evaluating' | 'done'
      score?: number
    }
  | { type: 'evaluation_progress'; step: 'synthesis' }
  | ({ type: 'question_evaluation' } & InterviewEvaluation)
  | ({ type: 'session_report' } & SessionReport)
  | { type: 'session_complete'; message: string; total_answered: number }
  | ({ type: 'done'; model: string; session_id: string } & Partial<InterviewerSessionInfo>)
  | { type: 'error'; message: string }

export type SaveAnswerResponse = {
  question_id: string
  question_index: number
  total_questions: number
  is_last: boolean
  answer: string
} & Partial<InterviewerSessionInfo>

export type AdvanceResponse = {
  phase: InterviewPhase
  review_ready?: boolean
  current_question?: InterviewQuestion | null
} & Partial<InterviewerSessionInfo>
