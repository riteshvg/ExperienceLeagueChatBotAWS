/** Parse MCQ blocks from educator assistant messages for QuestionCard UI. */

const QUESTION_RE =
  /\*\*Question\s+(\d+)\*\*\s*·\s*\*([^*]+)\*([\s\S]*?)(?=\n\*Type your answer|\n---|\n\*\*Question|$)/i

const OPTION_RE = /^([A-D])\.\s+(.+)$/gm

export type ParsedQuestion = {
  number: number
  domain: string
  text: string
  options: { key: string; label: string }[]
}

export function parseQuestionFromMessage(content: string): ParsedQuestion | null {
  const match = content.match(QUESTION_RE)
  if (!match) return null

  const number = parseInt(match[1], 10)
  const domain = match[2].trim()
  const body = match[3].trim()

  const options: { key: string; label: string }[] = []
  let optionMatch: RegExpExecArray | null
  const optionBlock = body
  OPTION_RE.lastIndex = 0
  while ((optionMatch = OPTION_RE.exec(optionBlock)) !== null) {
    options.push({ key: optionMatch[1], label: optionMatch[2].trim() })
  }

  const textEnd = body.search(/^[A-D]\.\s/m)
  const text = (textEnd >= 0 ? body.slice(0, textEnd) : body).trim()

  if (options.length === 0) return null

  return { number, domain, text, options }
}

export function isVerificationMessage(content: string): boolean {
  return /^[✓✗]/.test(content.trim()) || content.includes('✓') || content.includes('✗')
}
