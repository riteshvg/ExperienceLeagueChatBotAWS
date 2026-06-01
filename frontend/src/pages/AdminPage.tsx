import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, RefreshCw } from 'lucide-react'
import { useAdmin } from '@/hooks/useAdmin'
import { cn } from '@/lib/utils'

type Tab = 'status' | 'settings' | 'analytics'

function StatCard({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4">
      <p className="text-xs text-slate-500 uppercase tracking-wider">{label}</p>
      <p className="text-lg font-semibold text-slate-800 mt-1 break-all">
        {String(value ?? '—')}
      </p>
    </div>
  )
}

function JsonTree({ data }: { data: unknown }) {
  return (
    <pre className="text-xs bg-slate-50 border border-slate-200 rounded-lg p-3 overflow-auto max-h-96 text-slate-600">
      {JSON.stringify(data, null, 2)}
    </pre>
  )
}

export function AdminPage() {
  const { isAuthenticated, login, logout, refresh, status, settings, analytics, loading, error } = useAdmin()
  const [password, setPassword] = useState('')
  const [tab, setTab] = useState<Tab>('status')

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-8 w-full max-w-sm">
          <div className="flex items-center gap-2 mb-6">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center">
              <span className="text-white text-xs font-bold">EL</span>
            </div>
            <h1 className="font-semibold text-slate-800">Admin Panel</h1>
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2 mb-4">{error}</p>
          )}

          <form
            onSubmit={(e) => { e.preventDefault(); login(password) }}
            className="space-y-3"
          >
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Admin password"
              className="w-full px-3 py-2.5 rounded-lg border border-slate-200 text-sm focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
            />
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <div className="mt-4 text-center">
            <Link to="/" className="text-xs text-slate-400 hover:text-slate-600">
              ← Back to chat
            </Link>
          </div>
        </div>
      </div>
    )
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: 'status', label: 'System Status' },
    { id: 'settings', label: 'Settings' },
    { id: 'analytics', label: 'Analytics' },
  ]

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link to="/" className="text-slate-400 hover:text-slate-600">
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <h1 className="text-sm font-semibold text-slate-800">Admin Panel</h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={refresh}
            disabled={loading}
            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700 px-3 py-1.5 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <RefreshCw className={cn('w-3.5 h-3.5', loading && 'animate-spin')} />
            Refresh
          </button>
          <button
            onClick={logout}
            className="text-xs text-red-500 hover:text-red-700 px-3 py-1.5 rounded-lg hover:bg-red-50 transition-colors"
          >
            Sign out
          </button>
        </div>
      </header>

      {/* Tab nav */}
      <div className="bg-white border-b border-slate-200 px-6">
        <nav className="flex gap-0">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={cn(
                'px-4 py-3 text-sm border-b-2 transition-colors',
                tab === t.id
                  ? 'border-blue-600 text-blue-600 font-medium'
                  : 'border-transparent text-slate-500 hover:text-slate-700',
              )}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Content */}
      <div className="px-6 py-6 max-w-4xl">
        {tab === 'status' && status && (
          <div className="space-y-6">
            <div>
              <h2 className="text-sm font-semibold text-slate-600 mb-3">Components</h2>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {Object.entries(status.components as Record<string, Record<string, unknown>>).map(
                  ([name, info]) => (
                    <div
                      key={name}
                      className={cn(
                        'bg-white rounded-xl border p-4',
                        info.healthy ? 'border-emerald-200' : 'border-red-200',
                      )}
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className={cn(
                            'w-2 h-2 rounded-full',
                            info.healthy ? 'bg-emerald-400' : 'bg-red-400',
                          )}
                        />
                        <p className="text-sm font-medium text-slate-700 capitalize">{name.replace('_', ' ')}</p>
                      </div>
                      {info.document_count !== undefined && (
                        <p className="text-xs text-slate-400 mt-1">{String(info.document_count)} docs</p>
                      )}
                      {info.active_sessions !== undefined && (
                        <p className="text-xs text-slate-400 mt-1">{String(info.active_sessions)} sessions</p>
                      )}
                    </div>
                  ),
                )}
              </div>
            </div>

            <div>
              <h2 className="text-sm font-semibold text-slate-600 mb-3">Citation Stats</h2>
              <div className="grid grid-cols-2 gap-3">
                {Object.entries(status.citation_stats as Record<string, unknown>).map(([k, v]) => (
                  <StatCard key={k} label={k.replace(/_/g, ' ')} value={v} />
                ))}
              </div>
            </div>
          </div>
        )}

        {tab === 'settings' && settings && (
          <div className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {Object.entries(settings as Record<string, unknown>).map(([k, v]) => (
                <StatCard key={k} label={k.replace(/_/g, ' ')} value={v} />
              ))}
            </div>
          </div>
        )}

        {tab === 'analytics' && analytics && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {Object.entries(analytics as Record<string, unknown>).map(([k, v]) => (
                <StatCard key={k} label={k.replace(/_/g, ' ')} value={v} />
              ))}
            </div>
            <div>
              <h2 className="text-sm font-semibold text-slate-600 mb-2">Raw data</h2>
              <JsonTree data={analytics} />
            </div>
          </div>
        )}

        {loading && (
          <p className="text-sm text-slate-400">Loading…</p>
        )}
      </div>
    </div>
  )
}
