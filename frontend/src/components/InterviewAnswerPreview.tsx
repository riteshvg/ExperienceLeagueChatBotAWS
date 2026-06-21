import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { cn } from '@/lib/utils'

interface Props {
  answer: string
  className?: string
}

export function InterviewAnswerPreview({ answer, className }: Props) {
  return (
    <div
      className={cn(
        'rounded-xl border border-slate-200 bg-slate-50/60 px-4 py-3 prose prose-sm max-w-none text-slate-800',
        className,
      )}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{answer}</ReactMarkdown>
    </div>
  )
}
