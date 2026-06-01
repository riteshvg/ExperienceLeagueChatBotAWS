import { ExternalLink } from 'lucide-react'
import { type Citation } from '@/lib/api'

interface Props {
  citation: Citation
}

export function CitationCard({ citation }: Props) {
  return (
    <a
      href={citation.url}
      target="_blank"
      rel="noopener noreferrer"
      title={citation.title}
      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium
        bg-slate-100 text-slate-600 border border-slate-200
        hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300
        transition-colors no-underline max-w-[220px]"
    >
      <ExternalLink className="w-3 h-3 flex-shrink-0" />
      <span className="truncate">{citation.title || citation.product || 'Doc'}</span>
    </a>
  )
}
