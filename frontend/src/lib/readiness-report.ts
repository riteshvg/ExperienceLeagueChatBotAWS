import type { DomainScores, Exam, QuestionRecord, ReadinessReport } from '@/types/educator'

export function generateReadinessReport(
  exam: Exam,
  questions: QuestionRecord[],
): ReadinessReport {
  const resolved = questions.filter((q) => q.resolved && !q.skipped)
  const skipped = questions.filter((q) => q.skipped)
  const totalResolved = resolved.length
  const totalCorrect = resolved.filter((q) => q.attempts.some((a) => a.correct)).length
  const firstTryCorrect = resolved.filter((q) => q.attempts[0]?.correct).length

  const overallPct = totalResolved > 0 ? Math.round((totalCorrect / totalResolved) * 100) : 0
  const firstTryPct = totalResolved > 0 ? Math.round((firstTryCorrect / totalResolved) * 100) : 0
  const passingPct = Math.round((exam.passingScore / exam.totalQuestions) * 100)

  const domainReports = exam.domains.map((domain) => {
    const domainQs = questions.filter((q) => q.domainId === domain.id)
    const resolvedD = domainQs.filter((q) => q.resolved && !q.skipped)
    const correct = resolvedD.filter((q) => q.attempts.some((a) => a.correct)).length
    const total = resolvedD.length
    const skippedCount = domainQs.filter((q) => q.skipped).length
    const pct = total > 0 ? Math.round((correct / total) * 100) : 0
    return {
      domain: domain.name,
      domainId: domain.id,
      correct,
      total,
      skipped: skippedCount,
      pct,
      weak: total >= 2 && pct < passingPct,
      docSearchHint: domain.docSearchHint,
    }
  })

  domainReports.sort((a, b) => Number(b.weak) - Number(a.weak) || a.pct - b.pct)

  const verdict: ReadinessReport['verdict'] =
    firstTryPct >= passingPct + 10
      ? 'Ready to attempt'
      : firstTryPct >= passingPct - 5
        ? 'Almost there'
        : 'Keep going'

  return {
    overallPct,
    firstTryPct,
    passingPct,
    totalCorrect,
    totalResolved,
    totalSkipped: skipped.length,
    totalAsked: totalResolved,
    verdict,
    domainReports,
    skippedQuestions: skipped.map((q) => ({
      questionId: q.questionId,
      domainId: q.domainId,
      questionText: q.questionText,
      domain: q.domain,
    })),
  }
}

export function emptyDomainScores(exam: Exam): DomainScores {
  return Object.fromEntries(
    exam.domains.map((d) => [d.id, { correct: 0, total: 0, skipped: 0 }]),
  )
}

export function syncDomainScoresFromQuestions(
  exam: Exam,
  questions: QuestionRecord[],
): DomainScores {
  const scores = emptyDomainScores(exam)
  for (const q of questions) {
    const bucket = scores[q.domainId]
    if (!bucket) continue
    if (q.skipped) {
      bucket.skipped += 1
      continue
    }
    if (q.resolved) {
      bucket.total += 1
      if (q.attempts.some((a) => a.correct)) bucket.correct += 1
    }
  }
  return scores
}
