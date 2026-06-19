import type { DomainScores, Exam, ReadinessReport } from '@/types/educator'

export function generateReadinessReport(
  exam: Exam,
  domainScores: DomainScores,
  totalCorrect?: number,
  totalAsked?: number,
): ReadinessReport {
  const asked =
    totalAsked ?? Object.values(domainScores).reduce((s, d) => s + d.total, 0)
  const correct =
    totalCorrect ?? Object.values(domainScores).reduce((s, d) => s + d.correct, 0)

  const overallPct = asked > 0 ? Math.round((correct / asked) * 100) : 0
  const passingPct = Math.round((exam.passingScore / exam.totalQuestions) * 100)

  const domainReports = exam.domains.map((domain) => {
    const scores = domainScores[domain.id] ?? { correct: 0, total: 0 }
    const pct = scores.total > 0 ? Math.round((scores.correct / scores.total) * 100) : 0
    return {
      domain: domain.name,
      domainId: domain.id,
      correct: scores.correct,
      total: scores.total,
      pct,
      weak: pct < passingPct && scores.total >= 2,
      docSearchHint: domain.docSearchHint,
    }
  })

  const verdict: ReadinessReport['verdict'] =
    overallPct >= passingPct + 10
      ? 'Ready'
      : overallPct >= passingPct - 5
        ? 'Almost ready'
        : 'Needs more prep'

  return {
    overallPct,
    passingPct,
    totalCorrect: correct,
    totalAsked: asked,
    verdict,
    domainReports,
  }
}
