import type { LandingQuestion } from '@/lib/api'

export type ProductSlug = 'analytics' | 'cja' | 'aep' | 'target' | 'ajo' | 'general'

export interface TickerQuestion {
  text: string
  asked: number
  product: ProductSlug
  solutions: string[]
}

export const PRODUCT_PILL_STYLES: Record<ProductSlug, { bg: string; text: string; label: string }> = {
  analytics: { bg: '#FAEEDA', text: '#854F0B', label: 'Analytics' },
  cja: { bg: '#EEEDFE', text: '#534AB7', label: 'CJA' },
  aep: { bg: '#E6F1FB', text: '#185FA5', label: 'AEP' },
  target: { bg: '#E1F5EE', text: '#0F6E56', label: 'Target' },
  ajo: { bg: '#FAECE7', text: '#993C1D', label: 'AJO' },
  general: { bg: '#F1EFE8', text: '#5F5E5A', label: 'General' },
}

export const SOLUTION_PILL_STYLE = { bg: '#F1EFE8', text: '#5F5E5A' }

/** Curated seed — extend here as the product list grows. */
export const SEED_QUESTIONS: TickerQuestion[] = [
  {
    text: 'How do I create a segment in Adobe Analytics?',
    asked: 12,
    product: 'analytics',
    solutions: ['segment', 'workspace'],
  },
  {
    text: 'What is the difference between eVars and props in Adobe Analytics?',
    asked: 9,
    product: 'analytics',
    solutions: ['tracking', 'metrics'],
  },
  {
    text: 'What is a Data View in Customer Journey Analytics?',
    asked: 8,
    product: 'cja',
    solutions: ['workspace', 'metrics'],
  },
  {
    text: 'How do I create a calculated metric in CJA?',
    asked: 7,
    product: 'cja',
    solutions: ['metrics', 'implementation'],
  },
  {
    text: 'How do I create an XDM schema in Adobe Experience Platform?',
    asked: 11,
    product: 'aep',
    solutions: ['ingestion', 'identity'],
  },
  {
    text: 'What are the different ways to ingest data into Adobe Experience Platform?',
    asked: 10,
    product: 'aep',
    solutions: ['ingestion', 'api'],
  },
  {
    text: 'How do I create an A/B test in Adobe Target?',
    asked: 6,
    product: 'target',
    solutions: ['audience', 'implementation'],
  },
  {
    text: 'How do I use Recommendations in Adobe Target?',
    asked: 5,
    product: 'target',
    solutions: ['audience', 'metrics'],
  },
  {
    text: 'How do I create a journey in Adobe Journey Optimizer?',
    asked: 8,
    product: 'ajo',
    solutions: ['journey', 'audience'],
  },
  {
    text: 'What is decision management in Adobe Journey Optimizer?',
    asked: 4,
    product: 'ajo',
    solutions: ['journey', 'implementation'],
  },
  {
    text: 'How do I connect an Adobe Analytics report suite to CJA?',
    asked: 6,
    product: 'general',
    solutions: ['implementation', 'workspace'],
  },
  {
    text: 'How do I install the Adobe Experience Platform Web SDK?',
    asked: 5,
    product: 'general',
    solutions: ['tracking', 'implementation'],
  },
]

const SOLUTION_TO_PRODUCT: Record<string, ProductSlug> = {
  Analytics: 'analytics',
  CJA: 'cja',
  AEP: 'aep',
  Target: 'target',
  AJO: 'ajo',
  'Data Collection': 'general',
  'Cross-Product': 'general',
  General: 'general',
}

const TOPIC_KEYWORDS: Array<{ pattern: RegExp; tag: string }> = [
  { pattern: /\bsegment(s)?\b/i, tag: 'segment' },
  { pattern: /\bapi\b/i, tag: 'api' },
  { pattern: /\btrack(ing)?\b/i, tag: 'tracking' },
  { pattern: /\bworkspace\b/i, tag: 'workspace' },
  { pattern: /\bingest(ion)?\b/i, tag: 'ingestion' },
  { pattern: /\baudience(s)?\b/i, tag: 'audience' },
  { pattern: /\bidentity\b/i, tag: 'identity' },
  { pattern: /\bjourney\b/i, tag: 'journey' },
  { pattern: /\bmetric(s)?\b/i, tag: 'metrics' },
  { pattern: /\bimplement(ation)?\b/i, tag: 'implementation' },
  { pattern: /\bschema\b/i, tag: 'ingestion' },
  { pattern: /\bxdm\b/i, tag: 'identity' },
  { pattern: /\brecommendation(s)?\b/i, tag: 'audience' },
]

function inferSolutions(text: string, product: ProductSlug): string[] {
  const tags = TOPIC_KEYWORDS.filter(({ pattern }) => pattern.test(text)).map(({ tag }) => tag)
  const unique = [...new Set(tags)].slice(0, 3)
  if (unique.length > 0) return unique
  const defaults: Record<ProductSlug, string[]> = {
    analytics: ['workspace', 'metrics'],
    cja: ['workspace', 'metrics'],
    aep: ['ingestion', 'identity'],
    target: ['audience', 'implementation'],
    ajo: ['journey', 'audience'],
    general: ['implementation'],
  }
  return defaults[product]
}

export function mapLandingToTicker(q: LandingQuestion): TickerQuestion {
  const product = SOLUTION_TO_PRODUCT[q.solution] ?? 'general'
  return {
    text: q.text,
    asked: q.times_asked,
    product,
    solutions: inferSolutions(q.text, product),
  }
}

export function mergeTickerQuestions(apiQuestions: LandingQuestion[]): TickerQuestion[] {
  const seen = new Set<string>()
  const merged: TickerQuestion[] = []

  for (const q of apiQuestions) {
    const key = q.text.trim().toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    merged.push(mapLandingToTicker(q))
  }

  for (const seed of SEED_QUESTIONS) {
    const key = seed.text.trim().toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    merged.push(seed)
  }

  return merged
}
