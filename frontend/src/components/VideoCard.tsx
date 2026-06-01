import { Play } from 'lucide-react'
import { type Citation } from '@/lib/api'

interface Props {
  citation: Citation
}

export function VideoCard({ citation }: Props) {
  return (
    <a
      href={citation.video_url}
      target="_blank"
      rel="noopener noreferrer"
      className="group flex-shrink-0 w-48 rounded-xl overflow-hidden border border-slate-200 hover:border-blue-300 hover:shadow-md transition-all no-underline bg-white"
    >
      {/* Thumbnail */}
      <div className="relative w-full aspect-video bg-slate-100 overflow-hidden">
        {citation.thumbnail_url ? (
          <img
            src={citation.thumbnail_url}
            alt={citation.title}
            className="w-full h-full object-cover"
            onError={(e) => {
              // Fallback to gradient placeholder if thumbnail fails to load
              (e.target as HTMLImageElement).style.display = 'none'
            }}
          />
        ) : null}
        {/* Play button overlay */}
        <div className="absolute inset-0 flex items-center justify-center bg-black/20 group-hover:bg-black/30 transition-colors">
          <div className="w-10 h-10 rounded-full bg-white/90 flex items-center justify-center shadow-md group-hover:scale-110 transition-transform">
            <Play className="w-4 h-4 text-slate-800 fill-slate-800 ml-0.5" />
          </div>
        </div>
      </div>
      {/* Title */}
      <div className="px-2.5 py-2">
        <p className="text-xs font-medium text-slate-700 line-clamp-2 group-hover:text-blue-700 leading-snug">
          {citation.title}
        </p>
        {citation.product && (
          <p className="text-xs text-slate-400 mt-0.5 truncate">{citation.product}</p>
        )}
      </div>
    </a>
  )
}
