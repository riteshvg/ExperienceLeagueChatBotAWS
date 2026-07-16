import { jsPDF } from 'jspdf'
import type { SessionReport } from '@/types/interviewer'
import { DEJAVU_SANS_BOLD_BASE64, DEJAVU_SANS_REGULAR_BASE64 } from './interviewReportFonts'

const FONT_NAME = 'DejaVuSans'

function registerUnicodeFont(doc: jsPDF) {
  doc.addFileToVFS('DejaVuSans.ttf', DEJAVU_SANS_REGULAR_BASE64)
  doc.addFont('DejaVuSans.ttf', FONT_NAME, 'normal')
  doc.addFileToVFS('DejaVuSans-Bold.ttf', DEJAVU_SANS_BOLD_BASE64)
  doc.addFont('DejaVuSans-Bold.ttf', FONT_NAME, 'bold')
}

// The embedded font subset only covers Latin-1, General Punctuation, and Arrows
// (see interviewReportFonts.ts) — anything outside that (e.g. stray emoji or CJK
// from LLM-generated text) would render as a missing-glyph box, so fall back to
// '?' rather than let jsPDF silently mis-render it.
const SAFE_RANGES: [number, number][] = [
  [0x0020, 0x00ff],
  [0x2000, 0x206f],
  [0x2190, 0x21ff],
]

function sanitizeForPdf(text: string): string {
  return Array.from(text)
    .map((ch) => {
      const code = ch.codePointAt(0) ?? 0
      return SAFE_RANGES.some(([lo, hi]) => code >= lo && code <= hi) ? ch : '?'
    })
    .join('')
}

const READINESS_LABELS: Record<string, string> = {
  not_ready: 'Not ready',
  needs_work: 'Needs work',
  nearly_ready: 'Nearly ready',
  interview_ready: 'Interview ready',
}

const MARGIN = 15
const PAGE_WIDTH = 210 // A4 mm
const PAGE_HEIGHT = 297
const CONTENT_WIDTH = PAGE_WIDTH - MARGIN * 2

interface Cursor {
  y: number
}

function ensureSpace(doc: jsPDF, cursor: Cursor, needed: number) {
  if (cursor.y + needed > PAGE_HEIGHT - MARGIN) {
    doc.addPage()
    cursor.y = MARGIN
  }
}

function addHeading(doc: jsPDF, cursor: Cursor, text: string) {
  ensureSpace(doc, cursor, 10)
  doc.setFont(FONT_NAME, 'bold')
  doc.setFontSize(12)
  doc.setTextColor(15, 23, 42) // slate-900
  doc.text(sanitizeForPdf(text), MARGIN, cursor.y)
  cursor.y += 7
}

function addParagraph(doc: jsPDF, cursor: Cursor, text: string, opts?: { size?: number; color?: [number, number, number] }) {
  doc.setFont(FONT_NAME, 'normal')
  doc.setFontSize(opts?.size ?? 10)
  const [r, g, b] = opts?.color ?? [30, 41, 59] // slate-800
  doc.setTextColor(r, g, b)
  const lines: string[] = doc.splitTextToSize(sanitizeForPdf(text), CONTENT_WIDTH)
  for (const line of lines) {
    ensureSpace(doc, cursor, 6)
    doc.text(line, MARGIN, cursor.y)
    cursor.y += 5.5
  }
}

function addBullet(doc: jsPDF, cursor: Cursor, text: string) {
  doc.setFont(FONT_NAME, 'normal')
  doc.setFontSize(10)
  doc.setTextColor(30, 41, 59)
  const lines: string[] = doc.splitTextToSize(`•  ${sanitizeForPdf(text)}`, CONTENT_WIDTH - 4)
  for (const line of lines) {
    ensureSpace(doc, cursor, 6)
    doc.text(line, MARGIN + 2, cursor.y)
    cursor.y += 5.5
  }
}

function addLink(doc: jsPDF, cursor: Cursor, label: string, url: string) {
  ensureSpace(doc, cursor, 11)
  doc.setFont(FONT_NAME, 'bold')
  doc.setFontSize(10)
  doc.setTextColor(4, 120, 87) // emerald-700
  const labelLines: string[] = doc.splitTextToSize(sanitizeForPdf(label), CONTENT_WIDTH)
  for (const line of labelLines) {
    ensureSpace(doc, cursor, 6)
    doc.textWithLink(line, MARGIN, cursor.y, { url })
    cursor.y += 5.5
  }
  doc.setFont(FONT_NAME, 'normal')
  doc.setFontSize(8.5)
  doc.setTextColor(100, 116, 139) // slate-500
  // Print the literal URL as visible text too — the point of this PDF is that
  // the candidate can read/copy the link later even outside a clickable viewer.
  const urlLines: string[] = doc.splitTextToSize(url, CONTENT_WIDTH)
  for (const line of urlLines) {
    ensureSpace(doc, cursor, 5)
    doc.text(line, MARGIN, cursor.y)
    cursor.y += 4.5
  }
  cursor.y += 2
}

export function generateInterviewReportPdf(params: {
  report: SessionReport
  debriefText: string
  level?: string | null
  profileLabel?: string | null
}): void {
  const { report, debriefText, level, profileLabel } = params
  const doc = new jsPDF({ unit: 'mm', format: 'a4' })
  registerUnicodeFont(doc)
  const cursor: Cursor = { y: MARGIN }

  doc.setFont(FONT_NAME, 'bold')
  doc.setFontSize(16)
  doc.setTextColor(4, 120, 87)
  doc.text('Mock Interview Report', MARGIN, cursor.y)
  cursor.y += 8

  const subtitleParts = [level, profileLabel].filter(Boolean)
  if (subtitleParts.length > 0) {
    doc.setFont(FONT_NAME, 'normal')
    doc.setFontSize(10)
    doc.setTextColor(100, 116, 139)
    doc.text(sanitizeForPdf(subtitleParts.join(' · ')), MARGIN, cursor.y)
    cursor.y += 6
  }
  doc.setFontSize(9)
  doc.setTextColor(148, 163, 184)
  doc.text(new Date().toLocaleDateString(), MARGIN, cursor.y)
  cursor.y += 10

  const readinessLabel = READINESS_LABELS[report.readiness] ?? report.readiness
  addHeading(doc, cursor, `Overall score: ${report.overall_score.toFixed(1)}/5 — ${readinessLabel}`)
  addParagraph(doc, cursor, report.readiness_summary)
  if (report.questions_answered < report.questions_total) {
    addParagraph(
      doc,
      cursor,
      `Interview ended early — scored on ${report.questions_answered} of ${report.questions_total} questions.`,
      { size: 9, color: [180, 83, 9] },
    )
  }
  cursor.y += 4

  if (debriefText.trim()) {
    addHeading(doc, cursor, "Coach's debrief")
    addParagraph(doc, cursor, debriefText.trim())
    cursor.y += 4
  }

  if (report.strengths.length > 0) {
    addHeading(doc, cursor, 'Overall strengths')
    report.strengths.forEach((s) => addBullet(doc, cursor, s))
    cursor.y += 4
  }

  if (report.priority_gaps.length > 0) {
    addHeading(doc, cursor, 'Priority gaps')
    report.priority_gaps.forEach((g) => addBullet(doc, cursor, g))
    cursor.y += 4
  }

  if (report.mistakes_to_avoid.length > 0) {
    addHeading(doc, cursor, 'Mistakes to avoid')
    report.mistakes_to_avoid.forEach((m) => addBullet(doc, cursor, m))
    cursor.y += 4
  }

  if (report.per_question.length > 0) {
    addHeading(doc, cursor, 'Per-question scores')
    for (const q of report.per_question) {
      addParagraph(doc, cursor, `Q${q.question_index} (${q.score}/5): ${q.question}`, { size: 9.5 })
      if (q.gaps.length > 0) {
        addParagraph(doc, cursor, `Gap: ${q.gaps[0]}`, { size: 8.5, color: [100, 116, 139] })
      }
      cursor.y += 2
    }
    cursor.y += 2
  }

  if (report.topics_to_read.length > 0) {
    addHeading(doc, cursor, 'Topics to study')
    for (const t of report.topics_to_read) {
      if (t.url) {
        addLink(doc, cursor, t.topic, t.url)
      } else {
        addParagraph(doc, cursor, t.topic, { size: 10, color: [30, 41, 59] })
      }
      if (t.reason) {
        addParagraph(doc, cursor, t.reason, { size: 8.5, color: [100, 116, 139] })
      }
      cursor.y += 2
    }
    cursor.y += 2
  }

  if (report.citations.length > 0) {
    addHeading(doc, cursor, 'Suggested reading')
    for (const c of report.citations) {
      addLink(doc, cursor, c.title, c.url)
    }
  }

  cursor.y += 4
  addParagraph(
    doc,
    cursor,
    'This is AI-generated interview guidance for practice purposes only — questions, feedback, and scoring '
      + 'may be imperfect and should not be taken as a literal or authoritative assessment.',
    { size: 8, color: [148, 163, 184] },
  )
  addParagraph(doc, cursor, 'Generated via Rovr', { size: 8, color: [148, 163, 184] })

  const dateStamp = new Date().toISOString().slice(0, 10)
  doc.save(`interview-report-${dateStamp}.pdf`)
}
