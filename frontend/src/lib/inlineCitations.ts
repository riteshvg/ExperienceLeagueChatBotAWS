import { useEffect, useMemo, useState } from 'react'
import type { Citation, RetrievalEvidence } from '@/lib/api'

export interface InlineSource {
  url: string
  title: string
  product?: string
}

const CITATION_MARKER_RE = /\[(\d+)\](?!\()/

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

export function stripCitationMarkers(text: string): string {
  return text.replace(/\[\d+\](?!\()/g, '')
}

export function stripMdLinks(text: string, keepCitationLinks = false): string {
  return text
    .replace(/\[([^\]]+)\]\([^)]*\.md[^)]*\)/g, '$1')
    .replace(
      /\[([^\]]+)\]\(https?:\/\/(?:experienceleague|developer)\.adobe\.com[^)]+\)/g,
      (match, label) => (keepCitationLinks && isCitationLinkLabel(label) ? match : label),
    )
}

function hasLinkableCitationMarkers(
  text: string,
  index: InlineSource[],
  evidence?: RetrievalEvidence,
): boolean {
  if (!CITATION_MARKER_RE.test(text)) return false
  CITATION_MARKER_RE.lastIndex = 0
  if (!index.length && !evidence?.sources?.length) return false
  return true
}

/**
 * Streaming: strip [N] markers and render markdown immediately.
 * After the answer finishes and paints, linkify in idle time — one markdown re-parse,
 * decoupled from the streaming→done transition.
 */
export function useDeferredCitationLinkify(
  sanitizedContent: string,
  streaming: boolean,
  inlineSources: InlineSource[],
  evidence?: RetrievalEvidence,
): { displayContent: string; citationsLinked: boolean } {
  const strippedContent = useMemo(
    () => stripMdLinks(stripCitationMarkers(sanitizedContent)),
    [sanitizedContent],
  )
  const [linkedContent, setLinkedContent] = useState<string | null>(null)

  useEffect(() => {
    if (streaming) {
      setLinkedContent(null)
      return
    }

    if (!sanitizedContent.trim()) {
      setLinkedContent(null)
      return
    }

    if (!hasLinkableCitationMarkers(sanitizedContent, inlineSources, evidence)) {
      setLinkedContent(null)
      return
    }

    let cancelled = false
    let raf2 = 0
    let idleId: number | undefined
    let timeoutId: ReturnType<typeof setTimeout> | undefined

    const runLinkifyPass = () => {
      if (cancelled) return
      const linked = stripMdLinks(
        linkifyCitationMarkers(sanitizedContent, inlineSources, evidence),
        true,
      )
      setLinkedContent(linked === strippedContent ? null : linked)
    }

    const raf1 = requestAnimationFrame(() => {
      raf2 = requestAnimationFrame(() => {
        if (cancelled) return
        if (typeof requestIdleCallback !== 'undefined') {
          idleId = requestIdleCallback(runLinkifyPass, { timeout: 800 })
        } else {
          timeoutId = setTimeout(runLinkifyPass, 0)
        }
      })
    })

    return () => {
      cancelled = true
      cancelAnimationFrame(raf1)
      if (raf2) cancelAnimationFrame(raf2)
      if (idleId !== undefined && typeof cancelIdleCallback !== 'undefined') {
        cancelIdleCallback(idleId)
      }
      if (timeoutId !== undefined) clearTimeout(timeoutId)
    }
  }, [streaming, sanitizedContent, strippedContent, inlineSources, evidence])

  return {
    displayContent: linkedContent ?? strippedContent,
    citationsLinked: linkedContent !== null,
  }
}
