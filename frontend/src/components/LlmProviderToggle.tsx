import { useEffect, useState } from 'react'
import { Cloud, Zap } from 'lucide-react'
import { cn } from '@/lib/utils'
import { getLlmProvider, setLlmProvider, type LlmProvider } from '@/lib/api'

const ADMIN_TOKEN_KEY = 'el_admin_token'

interface Props {
  className?: string
}

/**
 * Admin-only toggle between the direct Anthropic API (default) and AWS
 * Bedrock for main-answer generation. Uses the separate admin JWT (from the
 * /admin password login, stored under 'el_admin_token') rather than the
 * regular Google OAuth session — the backend's /api/admin/* routes only
 * accept that token, same as the kill switch and other admin settings.
 */
export function LlmProviderToggle({ className }: Props) {
  const [adminToken] = useState<string | null>(() => localStorage.getItem(ADMIN_TOKEN_KEY))
  const [provider, setProvider] = useState<LlmProvider | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!adminToken) return
    getLlmProvider(adminToken)
      .then((res) => setProvider(res.provider))
      .catch(() => setError('Could not load'))
  }, [adminToken])

  if (!adminToken) {
    return (
      <div className={cn('px-2.5 py-2 text-xs text-slate-400 dark:text-slate-500', className)}>
        LLM provider — sign in to Admin panel to change
      </div>
    )
  }

  const handleSelect = async (next: LlmProvider) => {
    if (next === provider || saving) return
    setSaving(true)
    setError(null)
    const previous = provider
    setProvider(next)
    try {
      await setLlmProvider(adminToken, next)
    } catch {
      setProvider(previous)
      setError('Failed to update')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className={cn('px-2.5 py-2', className)}>
      <p className="mb-1.5 text-xs font-medium text-slate-500 dark:text-slate-400">LLM provider</p>
      <div className="flex rounded-lg border border-slate-200 bg-slate-50 p-0.5 text-xs dark:border-slate-700 dark:bg-slate-800">
        <button
          type="button"
          disabled={saving}
          onClick={() => handleSelect('anthropic')}
          className={cn(
            'flex flex-1 items-center justify-center gap-1.5 rounded-md px-2 py-1.5 font-medium transition-colors disabled:opacity-60',
            provider === 'anthropic'
              ? 'bg-white text-[#14532D] shadow-sm dark:bg-slate-700 dark:text-emerald-300'
              : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200',
          )}
        >
          <Zap className="h-3.5 w-3.5" />
          Anthropic
        </button>
        <button
          type="button"
          disabled={saving}
          onClick={() => handleSelect('bedrock')}
          className={cn(
            'flex flex-1 items-center justify-center gap-1.5 rounded-md px-2 py-1.5 font-medium transition-colors disabled:opacity-60',
            provider === 'bedrock'
              ? 'bg-white text-[#14532D] shadow-sm dark:bg-slate-700 dark:text-emerald-300'
              : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200',
          )}
        >
          <Cloud className="h-3.5 w-3.5" />
          Bedrock
        </button>
      </div>
      {error && <p className="mt-1 text-xs text-red-500">{error}</p>}
    </div>
  )
}
