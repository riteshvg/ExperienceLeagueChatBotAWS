import { useRef, useCallback } from 'react'
import { Bold, Italic, List, ListOrdered, Code, Heading2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Props {
  value: string
  onChange: (value: string) => void
  disabled?: boolean
  placeholder?: string
  minRows?: number
  className?: string
}

function wrapSelection(
  textarea: HTMLTextAreaElement,
  before: string,
  after: string,
  placeholder?: string,
) {
  const start = textarea.selectionStart
  const end = textarea.selectionEnd
  const selected = textarea.value.slice(start, end) || placeholder || ''
  const next =
    textarea.value.slice(0, start) + before + selected + after + textarea.value.slice(end)
  return { next, cursor: start + before.length + selected.length + after.length }
}

function prefixLines(textarea: HTMLTextAreaElement, prefix: string) {
  const start = textarea.selectionStart
  const end = textarea.selectionEnd
  const before = textarea.value.slice(0, start)
  const selected = textarea.value.slice(start, end)
  const after = textarea.value.slice(end)
  const lines = (selected || 'item').split('\n')
  const prefixed = lines.map((line) => `${prefix}${line}`).join('\n')
  const next = before + prefixed + after
  return { next, cursor: before.length + prefixed.length }
}

export function InterviewAnswerEditor({
  value,
  onChange,
  disabled,
  placeholder = 'Write your answer here. Use Markdown for structure — **bold**, bullet lists, `code`, and headings.',
  minRows = 14,
  className,
}: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const apply = useCallback(
    (fn: (el: HTMLTextAreaElement) => { next: string; cursor: number }) => {
      const el = textareaRef.current
      if (!el || disabled) return
      const { next, cursor } = fn(el)
      onChange(next)
      requestAnimationFrame(() => {
        el.focus()
        el.setSelectionRange(cursor, cursor)
      })
    },
    [disabled, onChange],
  )

  const tools = [
    {
      icon: Bold,
      label: 'Bold',
      action: () =>
        apply((el) => wrapSelection(el, '**', '**', 'bold text')),
    },
    {
      icon: Italic,
      label: 'Italic',
      action: () =>
        apply((el) => wrapSelection(el, '*', '*', 'italic text')),
    },
    {
      icon: Heading2,
      label: 'Heading',
      action: () =>
        apply((el) => prefixLines(el, '## ')),
    },
    {
      icon: List,
      label: 'Bullet list',
      action: () =>
        apply((el) => prefixLines(el, '- ')),
    },
    {
      icon: ListOrdered,
      label: 'Numbered list',
      action: () => {
        const el = textareaRef.current
        if (!el || disabled) return
        const start = el.selectionStart
        const end = el.selectionEnd
        const before = el.value.slice(0, start)
        const selected = el.value.slice(start, end)
        const after = el.value.slice(end)
        const lines = (selected || 'item').split('\n')
        const numbered = lines.map((line, i) => `${i + 1}. ${line}`).join('\n')
        const next = before + numbered + after
        onChange(next)
        requestAnimationFrame(() => {
          el.focus()
          el.setSelectionRange(before.length + numbered.length, before.length + numbered.length)
        })
      },
    },
    {
      icon: Code,
      label: 'Code',
      action: () =>
        apply((el) => wrapSelection(el, '`', '`', 'code')),
    },
  ]

  const wordCount = value.trim() ? value.trim().split(/\s+/).length : 0

  return (
    <div className={cn('rounded-xl border border-slate-200 bg-white overflow-hidden', className)}>
      <div className="flex items-center gap-0.5 px-2 py-1.5 border-b border-slate-100 bg-slate-50/80">
        {tools.map(({ icon: Icon, label, action }) => (
          <button
            key={label}
            type="button"
            title={label}
            disabled={disabled}
            onClick={action}
            className="p-1.5 rounded-md text-slate-500 hover:text-slate-800 hover:bg-white disabled:opacity-40"
          >
            <Icon className="w-3.5 h-3.5" />
          </button>
        ))}
        <span className="ml-auto text-[10px] text-slate-400 pr-1">
          Markdown · {wordCount} {wordCount === 1 ? 'word' : 'words'}
        </span>
      </div>
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        placeholder={placeholder}
        rows={minRows}
        className={cn(
          'w-full resize-y px-4 py-3 text-sm text-slate-800 leading-relaxed',
          'placeholder:text-slate-400 focus:outline-none',
          'min-h-[280px] max-h-[480px]',
          disabled && 'opacity-60 cursor-not-allowed bg-slate-50',
        )}
      />
    </div>
  )
}
