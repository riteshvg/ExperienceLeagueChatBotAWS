import { BookOpen, ExternalLink } from 'lucide-react'
import type { DocCitation } from '@/types/educator'
import { cn } from '@/lib/utils'

interface Props {
  citation: DocCitation
  variant: 'preview' | 'citation'
}

export function DocCitationCard({ citation, variant }: Props) {
  return (
    <div
      className={cn(
        'mt-3 rounded-lg border p-3 text-sm',
        variant === 'preview'
          ? 'border-blue-200 bg-blue-50/60'
          : 'border-emerald-200 bg-emerald-50/60',
      )}
    >
      <div className="flex items-start gap-2">
        <BookOpen
          className={cn(
            'h-4 w-4 shrink-0 mt-0.5',
            variant === 'preview' ? 'text-blue-600' : 'text-emerald-600',
          )}
        />
        <div className="min-w-0">
          <p className="font-medium text-slate-800">{citation.title}</p>
          {citation.section && (
            <p className="text-xs text-slate-600 mt-1 leading-relaxed">{citation.section}</p>
          )}
          <a
            href={citation.url}
            target="_blank"
            rel="noopener noreferrer"
            className={cn(
              'inline-flex items-center gap-1 mt-2 text-xs font-medium',
              variant === 'preview' ? 'text-blue-700 hover:underline' : 'text-emerald-700 hover:underline',
            )}
          >
            Open in Experience League
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      </div>
    </div>
  )
}
