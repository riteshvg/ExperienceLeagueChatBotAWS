import { ExternalLink } from 'lucide-react'
import { type Citation } from '@/lib/api'
import { cn } from '@/lib/utils'

interface Props {
  citation: Citation
  index: number
}

export function CitationCard({ citation, index }: Props) {
  return (
    <a
      href={citation.url}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(
        'group flex items-start gap-2 p-2.5 rounded-lg border border-slate-200',
        'bg-white hover:bg-slate-50 hover:border-blue-300 transition-colors text-sm no-underline',
      )}
    >
      <span className="flex-shrink-0 w-5 h-5 rounded-full bg-slate-100 text-slate-500 text-xs flex items-center justify-center font-medium mt-0.5">
        {index + 1}
      </span>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-slate-800 truncate group-hover:text-blue-700">
          {citation.title || 'Documentation'}
        </p>
        {citation.product && (
          <p className="text-xs text-slate-400 mt-0.5">{citation.product}</p>
        )}
      </div>
      <ExternalLink className="w-3.5 h-3.5 text-slate-300 group-hover:text-blue-400 flex-shrink-0 mt-0.5" />
    </a>
  )
}
