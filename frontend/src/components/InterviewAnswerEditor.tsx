import { useRef, useCallback, useState, useEffect } from 'react'
import { Bold, Italic, List, ListOrdered, Code, Heading2, Mic, Square, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { transcribeInterviewerAnswer } from '@/lib/api'

interface Props {
  value: string
  onChange: (value: string) => void
  disabled?: boolean
  placeholder?: string
  minRows?: number
  className?: string
  sessionId?: string | null
  onVoiceInputUsed?: () => void
}

const MAX_RECORDING_MS = 4 * 60 * 1000
const LEVEL_BAR_COUNT = 12

type VoiceState = 'idle' | 'recording' | 'transcribing'

function formatElapsed(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
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
  sessionId,
  onVoiceInputUsed,
}: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const maxDurationTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const rafRef = useRef<number | null>(null)
  const elapsedTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const recordStartRef = useRef<number | null>(null)

  const [voiceState, setVoiceState] = useState<VoiceState>('idle')
  const [voiceError, setVoiceError] = useState<string | null>(null)
  const [audioLevel, setAudioLevel] = useState(0)
  const [levelHistory, setLevelHistory] = useState<number[]>(() => Array(LEVEL_BAR_COUNT).fill(0))
  const [elapsedMs, setElapsedMs] = useState(0)

  const teardownAudioAnalysis = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current)
      rafRef.current = null
    }
    if (elapsedTimerRef.current) {
      clearInterval(elapsedTimerRef.current)
      elapsedTimerRef.current = null
    }
    analyserRef.current = null
    void audioContextRef.current?.close()
    audioContextRef.current = null
    recordStartRef.current = null
    setAudioLevel(0)
    setLevelHistory(Array(LEVEL_BAR_COUNT).fill(0))
    setElapsedMs(0)
  }, [])

  useEffect(() => teardownAudioAnalysis, [teardownAudioAnalysis])

  const stopRecording = useCallback(() => {
    if (maxDurationTimerRef.current) {
      clearTimeout(maxDurationTimerRef.current)
      maxDurationTimerRef.current = null
    }
    mediaRecorderRef.current?.stop()
  }, [])

  const startRecording = useCallback(async () => {
    if (disabled || !sessionId) return
    setVoiceError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []

      const AudioCtx = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
      const audioCtx = new AudioCtx()
      const source = audioCtx.createMediaStreamSource(stream)
      const analyser = audioCtx.createAnalyser()
      analyser.fftSize = 256
      source.connect(analyser)
      audioContextRef.current = audioCtx
      analyserRef.current = analyser

      const dataArray = new Uint8Array(analyser.frequencyBinCount)
      const tick = () => {
        analyser.getByteTimeDomainData(dataArray)
        let sumSquares = 0
        for (let i = 0; i < dataArray.length; i++) {
          const centered = (dataArray[i] - 128) / 128
          sumSquares += centered * centered
        }
        const rms = Math.sqrt(sumSquares / dataArray.length)
        const level = Math.min(1, rms * 4)
        setAudioLevel(level)
        setLevelHistory((prev) => [...prev.slice(1), level])
        rafRef.current = requestAnimationFrame(tick)
      }
      tick()

      recordStartRef.current = Date.now()
      elapsedTimerRef.current = setInterval(() => {
        setElapsedMs(Date.now() - (recordStartRef.current ?? Date.now()))
      }, 500)

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop())
        teardownAudioAnalysis()
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' })
        chunksRef.current = []
        void (async () => {
          setVoiceState('transcribing')
          try {
            const transcript = await transcribeInterviewerAnswer(sessionId, blob)
            if (transcript.trim()) {
              const el = textareaRef.current
              if (el && value) {
                const start = el.selectionStart ?? value.length
                const end = el.selectionEnd ?? value.length
                const next = value.slice(0, start) + transcript + value.slice(end)
                onChange(next)
              } else {
                onChange(transcript)
              }
              onVoiceInputUsed?.()
            }
          } catch (err) {
            setVoiceError(err instanceof Error ? err.message : 'Transcription failed')
          } finally {
            setVoiceState('idle')
          }
        })()
      }

      mediaRecorderRef.current = recorder
      recorder.start()
      setVoiceState('recording')
      maxDurationTimerRef.current = setTimeout(stopRecording, MAX_RECORDING_MS)
    } catch {
      setVoiceError('Microphone access was denied or unavailable.')
      setVoiceState('idle')
      teardownAudioAnalysis()
    }
  }, [disabled, sessionId, stopRecording, teardownAudioAnalysis, value, onChange, onVoiceInputUsed])

  const handleMicClick = () => {
    if (voiceState === 'idle') void startRecording()
    else if (voiceState === 'recording') stopRecording()
  }

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
    <div className={cn('rounded-lg border border-slate-200 overflow-hidden', className)}>
      <div className="flex items-center gap-0.5 px-1 py-1.5 border-b border-slate-200">
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
        {sessionId && (
          <>
            <span className="w-px h-4 bg-slate-200 mx-0.5" />
            <div className="relative flex items-center justify-center shrink-0">
              {voiceState === 'recording' && (
                <span className="absolute inline-flex h-6 w-6 rounded-full bg-red-500 opacity-40 animate-ping" />
              )}
              <button
                type="button"
                title={
                  voiceState === 'recording'
                    ? 'Stop recording'
                    : voiceState === 'transcribing'
                      ? 'Transcribing'
                      : 'Record answer'
                }
                disabled={disabled || voiceState === 'transcribing'}
                onClick={handleMicClick}
                style={
                  voiceState === 'recording'
                    ? { transform: `scale(${1 + audioLevel * 0.3})` }
                    : undefined
                }
                className={cn(
                  'relative flex items-center justify-center w-6 h-6 rounded-full transition-transform duration-75 ease-out disabled:opacity-40',
                  voiceState === 'idle' && 'text-slate-500 hover:text-slate-800 hover:bg-white',
                  voiceState === 'recording' && 'bg-red-800 text-white hover:bg-red-900',
                  voiceState === 'transcribing' && 'bg-red-700/70 text-white',
                )}
              >
                {voiceState === 'transcribing' ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : voiceState === 'recording' ? (
                  <Square className="w-3 h-3" />
                ) : (
                  <Mic className="w-3.5 h-3.5" />
                )}
              </button>
            </div>
            {voiceState === 'recording' && (
              <div className="flex items-end gap-px h-3.5 ml-1">
                {levelHistory.map((level, i) => (
                  <span
                    key={i}
                    className="w-0.5 rounded-sm bg-red-500 transition-[height] duration-75 ease-out"
                    style={{ height: `${Math.max(15, level * 100)}%` }}
                  />
                ))}
              </div>
            )}
            {voiceState === 'recording' && (
              <span className="text-[10px] tabular-nums text-red-700 ml-1">
                {formatElapsed(elapsedMs)}
              </span>
            )}
          </>
        )}
        <span className="ml-auto text-[10px] text-slate-400 pr-1">
          {voiceState === 'transcribing'
            ? 'Transcribing…'
            : voiceState === 'recording'
              ? 'Recording…'
              : `Markdown · ${wordCount} ${wordCount === 1 ? 'word' : 'words'}`}
        </span>
      </div>

      {voiceError && (
        <p className="px-4 pt-2 text-xs text-red-600">{voiceError}</p>
      )}
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
