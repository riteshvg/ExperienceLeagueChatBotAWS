import { useEffect, useCallback } from 'react'
import { ChevronLeft, ChevronRight, X } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface CarouselImage {
  src: string
  alt: string
}

interface Props {
  images: CarouselImage[]
  index: number
  onClose: () => void
  onIndexChange: (index: number) => void
}

export function ImageCarousel({ images, index, onClose, onIndexChange }: Props) {
  const hasPrev = index > 0
  const hasNext = index < images.length - 1
  const current = images[index]

  const goPrev = useCallback(() => {
    if (hasPrev) onIndexChange(index - 1)
  }, [hasPrev, index, onIndexChange])

  const goNext = useCallback(() => {
    if (hasNext) onIndexChange(index + 1)
  }, [hasNext, index, onIndexChange])

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault()
        goPrev()
      } else if (e.key === 'ArrowRight') {
        e.preventDefault()
        goNext()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose, goPrev, goNext])

  useEffect(() => {
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prev
    }
  }, [])

  if (!current) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/85"
      role="dialog"
      aria-modal="true"
      aria-label="Image gallery"
      onClick={onClose}
    >
      <button
        type="button"
        onClick={onClose}
        className="absolute top-4 right-4 z-10 p-2 rounded-full text-white/80 hover:text-white hover:bg-white/10 transition-colors"
        aria-label="Close gallery"
      >
        <X className="w-6 h-6" />
      </button>

      {images.length > 1 && (
        <span className="absolute top-4 left-1/2 -translate-x-1/2 z-10 px-3 py-1 rounded-full bg-black/50 text-white text-xs font-medium tabular-nums">
          {index + 1} / {images.length}
        </span>
      )}

      {hasPrev && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            goPrev()
          }}
          className="absolute left-3 sm:left-6 z-10 p-2 rounded-full bg-black/40 text-white hover:bg-black/60 transition-colors"
          aria-label="Previous image"
        >
          <ChevronLeft className="w-7 h-7" />
        </button>
      )}

      {hasNext && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            goNext()
          }}
          className="absolute right-3 sm:right-6 z-10 p-2 rounded-full bg-black/40 text-white hover:bg-black/60 transition-colors"
          aria-label="Next image"
        >
          <ChevronRight className="w-7 h-7" />
        </button>
      )}

      <figure
        className="flex flex-col items-center max-w-[min(92vw,1200px)] max-h-[90vh] px-14 sm:px-20"
        onClick={(e) => e.stopPropagation()}
      >
        <img
          key={current.src}
          src={current.src}
          alt={current.alt}
          className="max-w-full max-h-[78vh] object-contain rounded-lg"
        />
        {current.alt && (
          <figcaption className="mt-3 text-center text-sm text-white/80 max-w-prose line-clamp-3">
            {current.alt}
          </figcaption>
        )}
      </figure>

      {images.length > 1 && (
        <div
          className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2 max-w-[min(92vw,640px)] overflow-x-auto px-2 py-1"
          onClick={(e) => e.stopPropagation()}
        >
          {images.map((img, i) => (
            <button
              key={`${img.src}-${i}`}
              type="button"
              onClick={() => onIndexChange(i)}
              aria-label={`View image ${i + 1}${img.alt ? `: ${img.alt}` : ''}`}
              aria-current={i === index ? 'true' : undefined}
              className={cn(
                'flex-shrink-0 w-14 h-14 rounded-md overflow-hidden border-2 transition-all',
                i === index
                  ? 'border-white opacity-100 ring-2 ring-white/30'
                  : 'border-transparent opacity-50 hover:opacity-80',
              )}
            >
              <img src={img.src} alt="" className="w-full h-full object-cover" />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
