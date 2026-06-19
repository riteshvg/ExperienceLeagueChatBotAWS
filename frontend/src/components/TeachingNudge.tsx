interface Props {
  type: 'hint' | 'think' | 'walkthrough'
  text: string
}

const LABELS: Record<Props['type'], string> = {
  hint: 'hint',
  think: 'think about this',
  walkthrough: "let's work through it",
}

export function TeachingNudge({ type, text }: Props) {
  return (
    <div className="mt-3 border-l-2 border-violet-500 pl-3 py-1">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-violet-600 mb-1">
        {LABELS[type]}
      </p>
      <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">{text}</p>
    </div>
  )
}
