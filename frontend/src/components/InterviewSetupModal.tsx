import { useMemo, useState } from 'react'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { InterviewLevel, InterviewerProfiles } from '@/types/interviewer'

interface Props {
  open: boolean
  profiles: InterviewerProfiles | null
  onClose: () => void
  onStart: (level: InterviewLevel, profileId: string) => void
  loading?: boolean
}

export function InterviewSetupModal({ open, profiles, onClose, onStart, loading }: Props) {
  const [level, setLevel] = useState<InterviewLevel>('senior')
  const [profileId, setProfileId] = useState('all')

  const profileOptions = useMemo(() => {
    if (!profiles) return []
    const pool = level === 'principal' ? profiles.collections : profiles.solutions
    const validIds = new Set(
      profiles.combinations
        ?.filter((c) => c.level === level)
        .map((c) => c.profile_id) ?? [],
    )
    return pool.filter((p) => validIds.has(p.id))
  }, [profiles, level])

  const handleLevelChange = (next: InterviewLevel) => {
    setLevel(next)
    if (!profiles) return
    const valid = profiles.combinations?.filter((c) => c.level === next).map((c) => c.profile_id) ?? []
    const pool = next === 'principal' ? profiles.collections : profiles.solutions
    const first = pool.find((p) => valid.includes(p.id))
    if (first) setProfileId(first.id)
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="interview-setup-title"
        className="w-full max-w-lg rounded-2xl bg-white shadow-xl border border-slate-200"
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <div>
            <h2 id="interview-setup-title" className="text-base font-semibold text-slate-800">
              Interview prep setup
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Choose your target level and Adobe solution focus
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="px-5 py-4 space-y-5">
          <div>
            <p className="text-xs font-medium text-slate-500 mb-2">Experience level</p>
            <div className="grid grid-cols-2 gap-2">
              {(profiles?.levels ?? []).map((l) => (
                <button
                  key={l.id}
                  type="button"
                  onClick={() => handleLevelChange(l.id as InterviewLevel)}
                  className={cn(
                    'text-left rounded-lg border px-3 py-2.5 transition-colors',
                    level === l.id
                      ? 'border-emerald-600 bg-emerald-50'
                      : 'border-slate-200 hover:border-slate-300',
                  )}
                >
                  <span className="block text-sm font-medium text-slate-800">{l.label}</span>
                  {'description' in l && l.description && (
                    <span className="block text-[11px] text-slate-500 mt-0.5">{l.description}</span>
                  )}
                </button>
              ))}
            </div>
          </div>

          <div>
            <p className="text-xs font-medium text-slate-500 mb-2">
              {level === 'principal' ? 'Cross-solution collection' : 'Solution focus'}
            </p>
            <div className="flex flex-col gap-2">
              {profileOptions.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setProfileId(p.id)}
                  className={cn(
                    'text-left rounded-lg border px-3 py-2.5 transition-colors',
                    profileId === p.id
                      ? 'border-emerald-600 bg-emerald-50'
                      : 'border-slate-200 hover:border-slate-300',
                  )}
                >
                  <span className="block text-sm font-medium text-slate-800">{p.label}</span>
                  {p.description && (
                    <span className="block text-[11px] text-slate-500 mt-0.5">{p.description}</span>
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-2 px-5 py-4 border-t border-slate-100 bg-slate-50/50 rounded-b-2xl">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm text-slate-600 hover:text-slate-800"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={loading || !profiles}
            onClick={() => onStart(level, profileId)}
            className="px-4 py-2 rounded-lg bg-emerald-700 text-white text-sm font-medium hover:bg-emerald-800 disabled:opacity-50"
          >
            {loading ? 'Starting…' : 'Start practice'}
          </button>
        </div>
      </div>
    </div>
  )
}
