/** Format admin panel values — never show null, undefined, or [object Object]. */

export function formatAdminValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'number') {
    if (Number.isNaN(value)) return '—'
    return Number.isInteger(value) ? value.toLocaleString() : String(value)
  }
  if (typeof value === 'object') return '—'
  return String(value)
}

export function formatAdminDate(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  const d = new Date(String(value))
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString()
}

export function formatAdminDateShort(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  const d = new Date(String(value))
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleDateString()
}

export function formatAdminTime(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  const d = new Date(String(value))
  return Number.isNaN(d.getTime())
    ? '—'
    : d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export function isDemoStatus(value: unknown): value is Record<string, unknown> {
  return isRecord(value) && typeof value.questions_used === 'number'
}

export function isFeedbackPayload(value: unknown): value is { summary: Record<string, unknown>; entries: unknown[] } {
  return isRecord(value) && isRecord(value.summary) && Array.isArray(value.entries)
}

export function refreshSourceLabel(source: unknown): string {
  const labels: Record<string, string> = {
    's3:chroma_last_refreshed.json': 'GitHub Actions',
    'local:refresh_status.json': 'Admin server',
    's3:chroma_db/chroma_db.tar.gz': 'S3 Chroma backup',
    's3:state/sync_manifest.json': 'S3 sync manifest',
    'local:chroma_db_mtime': 'Local Chroma volume',
    knowledge_base: 'GitHub Actions',
  }
  if (source === null || source === undefined || source === '') return '—'
  const key = String(source)
  return labels[key] ?? key.replace(/^s3:/, 'S3 · ').replace(/^local:/, 'Local · ')
}

export const SETTINGS_DISPLAY: { key: string; label: string }[] = [
  { key: 'bedrock_model_id', label: 'Bedrock model' },
  { key: 'bedrock_region', label: 'Bedrock region' },
  { key: 'similarity_threshold', label: 'Similarity threshold' },
  { key: 'max_retrieval_results', label: 'Max retrieval results' },
  { key: 'min_retrieval_results', label: 'Min retrieval results' },
  { key: 'query_enhancement_enabled', label: 'Query enhancement' },
  { key: 'environment', label: 'Environment' },
]

export function componentDetails(name: string, info: Record<string, unknown>): string[] {
  const lines: string[] = []
  if (name === 'chromadb') {
    if (info.document_count !== undefined) lines.push(`${formatAdminValue(info.document_count)} chunks`)
    if (info.collection) lines.push(String(info.collection))
    if (info.embedding_model) lines.push(String(info.embedding_model))
  } else if (name === 'session_store' && info.active_sessions !== undefined) {
    lines.push(`${formatAdminValue(info.active_sessions)} sessions`)
  } else if (name === 'bedrock') {
    lines.push(info.healthy ? 'Connected' : 'Unavailable')
  }
  return lines
}
