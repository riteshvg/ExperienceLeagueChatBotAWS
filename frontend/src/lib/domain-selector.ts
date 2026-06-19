import type { DomainScores, Exam, ExamDomain } from '@/types/educator'

export function selectNextDomain(exam: Exam, domainScores: DomainScores): ExamDomain {
  const totalAsked = Object.values(domainScores).reduce((s, d) => s + d.total, 0)

  let maxDeficit = -Infinity
  let selected = exam.domains[0]

  for (const domain of exam.domains) {
    const targetCount = (domain.weightPct / 100) * (totalAsked + 1)
    const actualCount = domainScores[domain.id]?.total ?? 0
    const deficit = targetCount - actualCount
    if (deficit > maxDeficit) {
      maxDeficit = deficit
      selected = domain
    }
  }

  return selected
}
