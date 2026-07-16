/**
 * Throwaway dev script — NOT a permanent test.
 *
 * Feeds the real session_report produced by dev_generate_sample_report.py into
 * the actual, unmodified generateInterviewReportPdf() from
 * frontend/src/lib/generateInterviewReportPdf.ts, so the resulting PDF reflects
 * the real production renderer (Unicode font embedding + sanitization included)
 * — not a reimplementation.
 *
 * jsPDF's Node build writes doc.save(filename) straight to disk via fs
 * (no browser/DOM needed), so no shimming is required — we just chdir into
 * the output directory first so the relative filename lands there.
 *
 * Usage (from frontend/):
 *   npx tsx scripts/dev_render_sample_report_pdf.ts
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const inputPath = path.resolve(__dirname, '..', '..', 'scripts', 'sample_session_report.json')

function latestReportPdf(): string | undefined {
  return fs
    .readdirSync(__dirname)
    .filter((f) => f.startsWith('interview-report-') && f.endsWith('.pdf'))
    .map((f) => ({ f, mtime: fs.statSync(path.join(__dirname, f)).mtimeMs }))
    .sort((a, b) => b.mtime - a.mtime)[0]?.f
}

async function main() {
  const { generateInterviewReportPdf } = await import('../src/lib/generateInterviewReportPdf')
  const { report, debriefText, level, profileLabel } = JSON.parse(fs.readFileSync(inputPath, 'utf-8'))
  process.chdir(__dirname)

  // Pass 1: the real, unmodified session_report from real grading + synthesis.
  generateInterviewReportPdf({ report, debriefText, level, profileLabel })
  const realPdf = latestReportPdf()
  if (realPdf) fs.renameSync(path.join(__dirname, realPdf), path.join(__dirname, 'sample_interview_report.pdf'))
  console.log(`Wrote ${path.join(__dirname, 'sample_interview_report.pdf')} (real grading + synthesis, unmodified)`)

  // Pass 2: this run's real LLM output happened to contain zero non-ASCII
  // characters (no arrows/dashes/smart quotes), so it can't visually confirm
  // the Unicode-font fix. Same real report, with one clearly-labeled synthetic
  // line prepended to overall_feedback purely to exercise the font — not a
  // fabricated grading result.
  const fontQaLine =
    '**[Font QA addendum — not model-generated, added only to verify the ' +
    'PDF renderer’s Unicode font]** Data flow: Web SDK → Edge Network → AEP → CJA → ' +
    'Real-Time CDP → Destinations. Typographic check: em dash —, en dash –, ' +
    'curly quotes “quoted”, bullet •, accents café/naïve.\n\n'
  const qaReport = { ...report, overall_feedback: fontQaLine + (report.overall_feedback || '') }
  generateInterviewReportPdf({ report: qaReport, debriefText: fontQaLine + debriefText, level, profileLabel })
  const qaPdf = latestReportPdf()
  if (qaPdf) fs.renameSync(path.join(__dirname, qaPdf), path.join(__dirname, 'sample_interview_report_font_qa.pdf'))
  console.log(`Wrote ${path.join(__dirname, 'sample_interview_report_font_qa.pdf')} (font/glyph QA addendum)`)
}

main()
