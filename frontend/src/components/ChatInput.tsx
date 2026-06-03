import { forwardRef, useImperativeHandle, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { Send } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Props {
  onSend: (query: string) => void
  disabled?: boolean
}

export interface ChatInputHandle {
  fill: (text: string) => void
  focus: () => void
}

export const ChatInput = forwardRef<ChatInputHandle, Props>(function ChatInput({ onSend, disabled }, ref) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useImperativeHandle(ref, () => ({
    fill: (text: string) => {
      setValue(text)
      textareaRef.current?.focus()
      // Reset height to fit new content
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
        textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`
      }
    },
    focus: () => textareaRef.current?.focus(),
  }))

  const submit = () => {
    const q = value.trim()
    if (!q || disabled) return
    onSend(q)
    setValue('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  const handleInput = () => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }

  return (
    <form
      onSubmit={(e: FormEvent) => { e.preventDefault(); submit() }}
      className="flex items-end gap-2 bg-white border border-slate-200 rounded-2xl px-4 py-2.5 shadow-sm focus-within:border-blue-400 focus-within:ring-1 focus-within:ring-blue-400 transition"
    >
      <textarea
        ref={textareaRef}
        rows={1}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        disabled={disabled}
        placeholder="Ask about Adobe Analytics, CJA, AEP, or Target…"
        className={cn(
          'flex-1 resize-none bg-transparent text-sm text-slate-800 placeholder:text-slate-400',
          'focus:outline-none leading-relaxed py-0.5',
          disabled && 'opacity-50 cursor-not-allowed',
        )}
        style={{ minHeight: '24px' }}
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className={cn(
          'flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center transition-colors',
          value.trim() && !disabled
            ? 'bg-blue-600 text-white hover:bg-blue-700'
            : 'bg-slate-100 text-slate-300 cursor-not-allowed',
        )}
      >
        <Send className="w-3.5 h-3.5" />
      </button>
    </form>
  )
})
