import { ExternalLink } from 'lucide-react'
import { type Citation } from '@/lib/api'
import { trackCitationClick } from '@/analytics'

interface Props {
  citation: Citation
  index: number
  turnNumber?: number
}

export function CitationCard({ citation, index, turnNumber = 0 }: Props) {
  return (
    <a
      href={citation.url}
      target="_blank"
      rel="noopener noreferrer"
      title={citation.title}
      onClick={() => trackCitationClick(citation.url, citation.title || '', turnNumber)}
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium
        bg-slate-100 text-slate-600 border border-slate-200
        hover:bg-emerald-50 hover:text-[#14532D] hover:border-[#10B981]
        transition-colors no-underline max-w-[220px]"
    >
      <span className="flex-shrink-0 w-4 h-4 rounded-full bg-emerald-100 text-[#14532D]
        flex items-center justify-center text-[10px] font-bold leading-none">
        {index}
      </span>
      <span className="truncate">{citation.title || citation.product || 'Doc'}</span>
      <ExternalLink className="w-3 h-3 flex-shrink-0 opacity-60" />
    </a>
  )
}
