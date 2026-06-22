import type { Citation, RetrievalEvidence } from '@/lib/api'

export interface InlineSource {
  url: string
  title: string
  product?: string
}

/** Sources indexed by [1], [2], … — matches backend context_index order. */
export function getInlineSourceIndex(
  evidence?: RetrievalEvidence,
  citations?: Citation[],
): InlineSource[] {
  const fromEvidence = evidence?.context_index
  if (fromEvidence?.length) {
    return fromEvidence.map((s) => ({
      url: s.url,
      title: s.title,
      product: s.product,
    }))
  }
  if (evidence?.sources?.length) {
    return evidence.sources.map((s) => ({
      url: s.url,
      title: s.title,
      product: s.product,
    }))
  }
  if (citations?.length) {
    return citations.map((c) => ({
      url: c.url,
      title: c.title,
      product: c.product,
    }))
  }
  return []
}

export function resolveCitationUrl(
  num: number,
  index: InlineSource[],
  evidence?: RetrievalEvidence,
): string | undefined {
  const fromIndex = index[num - 1]?.url
  if (fromIndex) return fromIndex

  const sources = evidence?.sources ?? []
  if (num >= 1 && num <= sources.length) {
    const url = sources[num - 1]?.url
    if (url) return url
  }
  return undefined
}

/** Turn [1] markers into markdown links when a matching source URL exists. */
export function linkifyCitationMarkers(
  text: string,
  index: InlineSource[],
  evidence?: RetrievalEvidence,
): string {
  if (!index.length && !evidence?.sources?.length) return text
  return text.replace(/\[(\d+)\](?!\()/g, (match, numStr: string) => {
    const num = Number.parseInt(numStr, 10)
    if (!Number.isFinite(num) || num < 1) return match
    const url = resolveCitationUrl(num, index, evidence)
    if (!url) return match
    return `[${num}](${url})`
  })
}

export function isCitationLinkLabel(label: string): boolean {
  return /^\d+$/.test(label.trim())
}
