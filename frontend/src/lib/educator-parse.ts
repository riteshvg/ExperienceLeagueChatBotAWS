/** Parse educator v2 teaching responses for UI components. */

import type { DeepenAction, DocCitation, QuestionCardPhase } from '@/types/educator'

const QUESTION_RE =
  /\*\*Question\s+(\d+)\*\*\s*·\s*\*([^*]+)\*([\s\S]*?)(?=\n\[Give me a hint\]|$)/i

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
  OPTION_RE.lastIndex = 0
  while ((optionMatch = OPTION_RE.exec(body)) !== null) {
    options.push({ key: optionMatch[1], label: optionMatch[2].trim() })
  }

  const textEnd = body.search(/^[A-D]\.\s/m)
  const text = (textEnd >= 0 ? body.slice(0, textEnd) : body).trim()

  if (options.length === 0) return null
  return { number, domain, text, options }
}

export function parseTeachingPhase(content: string, attemptCount: number): QuestionCardPhase {
  if (/Noted — I'll add this to your revisit list/i.test(content)) return 'skipped'
  if (/\*\*Nailed it\*\*|\*\*Got it\*\*|\*\*There we go\*\*/i.test(content)) return 'correct'
  if (/\*\*let's work through it\*\*|Let's look at this together/i.test(content)) return 'revealed'
  if (/\*\*Attempt\s+\d+\s*—\s*not quite\*\*/i.test(content)) return 'wrong'
  if (/\*\*doc-preview\*\*/i.test(content)) return 'doc-shown'
  if (/\*\*hint\*\*/i.test(content)) return 'hinted'
  if (parseQuestionFromMessage(content)) return attemptCount > 0 ? 'wrong' : 'posed'
  return 'posed'
}

export function parseAttemptBadge(content: string): { attempt: number; label: string } | null {
  const wrong = content.match(/\*\*Attempt\s+(\d+)\s*—\s*not quite\*\*/i)
  if (wrong) return { attempt: parseInt(wrong[1], 10), label: 'not quite' }
  if (/\*\*Nailed it\*\*/i.test(content)) return { attempt: 1, label: 'Nailed it' }
  if (/\*\*Got it\*\*/i.test(content)) return { attempt: 2, label: 'Got it' }
  if (/\*\*There we go\*\*/i.test(content)) return { attempt: 3, label: 'There we go' }
  return null
}

export function parseTeachingNudge(content: string): { type: 'hint' | 'think' | 'walkthrough'; text: string } | null {
  const hint = content.match(/\*\*hint\*\*\s*·\s*([\s\S]*?)(?=\n\n|\*\*|$)/i)
  if (hint) return { type: 'hint', text: hint[1].trim() }

  const think = content.match(/\*\*think about this\*\*\s*·\s*([\s\S]*?)(?=\n\n|\*\*|$)/i)
  if (think) return { type: 'think', text: think[1].trim() }

  const walk = content.match(/\*\*let's work through it\*\*\s*·\s*([\s\S]*?)(?=\n\n\*\*doc-citation|\*\*doc-citation|$)/i)
  if (walk) return { type: 'walkthrough', text: walk[1].trim() }

  return null
}

export function parseDocCitation(content: string, variant: 'preview' | 'citation'): DocCitation | null {
  const tag = variant === 'preview' ? 'doc-preview' : 'doc-citation'
  const re = new RegExp(
    `\\*\\*${tag}\\*\\*\\s*·\\s*\\[([^\\]]+)\\]\\(([^)]+)\\)(?:\\s*—\\s*([\\s\\S]*?))?(?=\\n\\n|$)`,
    'i',
  )
  const m = content.match(re)
  if (!m) return null
  return { title: m[1].trim(), url: m[2].trim(), section: m[3]?.trim() ?? m[1].trim() }
}

export function parseDeepenActions(content: string): DeepenAction[] {
  const actions: DeepenAction[] = []
  const linkRe = /\[([^\]]+?)\s*↗\]\(#deepen:(explore|usecase|next)(?::([^)]*))?\)/gi
  let m: RegExpExecArray | null
  while ((m = linkRe.exec(content)) !== null) {
    const type = m[2] as DeepenAction['type']
    actions.push({
      type,
      label: m[1].trim(),
      prompt: m[3] ? decodeURIComponent(m[3]) : m[1].trim(),
    })
  }
  if (actions.length === 0 && /Next question/i.test(content)) {
    actions.push({ type: 'next', label: 'Next question ↗', prompt: 'Next question' })
  }
  return actions
}

export function parseDomainProgress(content: string): { correct: number; total: number; domainName: string } | null {
  const m = content.match(/\*\*Domain progress\*\*\s*·\s*(\d+)\/(\d+)\s+in\s+(.+)/i)
  if (!m) return null
  return { correct: parseInt(m[1], 10), total: parseInt(m[2], 10), domainName: m[3].trim() }
}

export function isCorrectResponse(content: string): boolean {
  return /\*\*Nailed it\*\*|\*\*Got it\*\*|\*\*There we go\*\*/i.test(content)
}

export function isWrongResponse(content: string): boolean {
  return /\*\*Attempt\s+\d+\s*—\s*not quite\*\*/i.test(content)
}

export function isRevealedResponse(content: string): boolean {
  return /\*\*let's work through it\*\*|Let's look at this together/i.test(content)
}

export function isSkipAcknowledged(content: string): boolean {
  return /revisit list/i.test(content)
}

export function extractLastWrongAnswer(userMessages: string[]): string | null {
  for (let i = userMessages.length - 1; i >= 0; i--) {
    const m = userMessages[i].match(/^(?:I choose |My answer is )?([A-D])\b/i)
    if (m) return m[1].toUpperCase()
  }
  return null
}
