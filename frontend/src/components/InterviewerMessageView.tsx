import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Copy, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { InterviewQuestionCard } from './InterviewQuestionCard'
import type { InterviewerMessage } from '@/types/interviewer'

interface Props {
  message: InterviewerMessage
}

export function InterviewerMessageView({ message }: Props) {
  const isUser = message.role === 'user'
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={cn('flex w-full', isUser ? 'justify-end' : 'justify-start')}>
      <div className={cn('max-w-[85%] space-y-2', isUser ? 'items-end' : 'items-start')}>
        {(isUser || message.content.trim()) && (
          <div
            className={cn(
              'relative px-4 py-3 rounded-2xl text-sm leading-relaxed',
              isUser
                ? 'bg-[#14532D] text-white rounded-br-sm'
                : 'bg-white border border-slate-200 text-slate-800 rounded-bl-sm shadow-sm',
              !isUser && !message.streaming && message.content.trim() && 'pr-10',
            )}
          >
            {!isUser && !message.streaming && message.content.trim() && (
              <button
                type="button"
                onClick={handleCopy}
                title="Copy feedback"
                className="absolute right-2 top-2 p-1 rounded-md text-slate-300 hover:text-slate-600 hover:bg-slate-100/90"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            )}
            {isUser ? (
              <p>{message.content}</p>
            ) : (
              <div className={cn('prose prose-sm max-w-none', message.streaming && 'streaming-cursor')}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
              </div>
            )}
          </div>
        )}

        {message.question && !isUser && (
          <InterviewQuestionCard question={message.question} />
        )}
      </div>
    </div>
  )
}
