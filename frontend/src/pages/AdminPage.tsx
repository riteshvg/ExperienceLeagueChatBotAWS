import { useState } from 'react'
import { RotateCcw } from 'lucide-react'
import { Link } from 'react-router-dom'
import { ArrowLeft, RefreshCw } from 'lucide-react'
import { useAdmin } from '@/hooks/useAdmin'
import { cn } from '@/lib/utils'

type Tab = 'status' | 'settings' | 'analytics' | 'feedback' | 'refresh'

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4">
      <p className="text-xs text-slate-500 uppercase tracking-wider">{label}</p>
      <p className="text-lg font-semibold text-slate-800 mt-1 break-all">
        {String(value)}
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
  const { isAuthenticated, login, logout, refresh, resetDemo, triggerRefresh, triggerGitHubActions, status, settings, analytics, demoStatus, feedback, refreshStatus, loading, error } = useAdmin()
  const [refreshing, setRefreshing] = useState(false)
  const [actionsTriggered, setActionsTriggered] = useState(false)

  const handleRefresh = async (force = false) => {
    setRefreshing(true)
    await triggerRefresh(force)
    setRefreshing(false)
  }

  const rsState = refreshStatus?.state ?? 'idle'
  const rsRunning = rsState === 'running'

  const handleTriggerActions = async (force = false) => {
    setActionsTriggered(false)
    const result = await triggerGitHubActions(force)
    if (result?.triggered) {
      setActionsTriggered(true)
      setTimeout(() => setActionsTriggered(false), 4000)
    }
  }
  const [resetting, setResetting] = useState(false)

  const handleResetDemo = async () => {
    setResetting(true)
    await resetDemo()
    setResetting(false)
  }
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
    { id: 'feedback', label: 'Feedback' },
    { id: 'refresh', label: 'Data Refresh' },
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

            {/* Demo account */}
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-slate-700">Demo Account</h2>
                <span className="text-xs text-slate-400">demo / demo</span>
              </div>
              {demoStatus ? (
                <div className="flex items-center gap-6">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className={cn(
                            'h-2 rounded-full transition-all',
                            (demoStatus.exhausted as boolean)
                              ? 'bg-red-400'
                              : (demoStatus.questions_used as number) > 0
                              ? 'bg-amber-400'
                              : 'bg-emerald-400',
                          )}
                          style={{ width: `${((demoStatus.questions_used as number) / (demoStatus.questions_limit as number)) * 100}%` }}
                        />
                      </div>
                      <span className="text-xs text-slate-500 whitespace-nowrap">
                        {demoStatus.questions_used as number} / {demoStatus.questions_limit as number} used
                      </span>
                    </div>
                    <p className="text-xs text-slate-400">
                      {(demoStatus.exhausted as boolean)
                        ? 'Demo limit reached — reset to allow more questions'
                        : `${demoStatus.questions_remaining as number} question${(demoStatus.questions_remaining as number) !== 1 ? 's' : ''} remaining`}
                    </p>
                  </div>
                  <button
                    onClick={handleResetDemo}
                    disabled={resetting}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium
                      bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50
                      disabled:cursor-not-allowed transition-colors flex-shrink-0"
                  >
                    <RotateCcw className={cn('w-3.5 h-3.5', resetting && 'animate-spin')} />
                    {resetting ? 'Resetting…' : 'Reset counter'}
                  </button>
                </div>
              ) : (
                <p className="text-sm text-slate-400">Loading demo status…</p>
              )}
            </div>

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
                  <StatCard key={k} label={k.replace(/_/g, ' ')} value={String(v ?? "—")} />
                ))}
              </div>
            </div>

            {Boolean(status.knowledge_base) && (() => {
              const KNOWN_PRODUCTS = [
                'Adobe Analytics',
                'Customer Journey Analytics',
                'Adobe Experience Platform',
                'Adobe Target',
                'Adobe Data Collection',
              ]
              type KbRow = { product: string; pages: number; chunks: number; pending: boolean }
              const liveRows = (status.knowledge_base as Record<string, unknown>).product_breakdown as Array<Record<string, unknown>> ?? []
              const liveNames = new Set(liveRows.map(r => String(r.product)))
              const pendingRows: KbRow[] = KNOWN_PRODUCTS
                .filter(p => !liveNames.has(p))
                .map(p => ({ product: p, pages: 0, chunks: 0, pending: true }))
              const allRows: KbRow[] = [
                ...liveRows.map(r => ({ product: String(r.product), pages: Number(r.pages), chunks: Number(r.chunks), pending: false })),
                ...pendingRows,
              ]
              return (
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h2 className="text-sm font-semibold text-slate-600">Knowledge Base</h2>
                    <span className="text-xs text-slate-400">
                      Last refreshed:{' '}
                      {(status.knowledge_base as Record<string, unknown>).last_refreshed
                        ? new Date(String((status.knowledge_base as Record<string, unknown>).last_refreshed)).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
                        : 'Never'}
                    </span>
                  </div>
                  <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-slate-100 bg-slate-50">
                          <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Product</th>
                          <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Pages</th>
                          <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Chunks</th>
                        </tr>
                      </thead>
                      <tbody>
                        {allRows.map((row, i) => (
                          <tr key={String(row.product)} className={cn('border-b border-slate-100', i === allRows.length - 1 && 'border-0')}>
                            <td className="px-4 py-2.5 text-slate-700 font-medium flex items-center gap-2">
                              {String(row.product)}
                              {row.pending && (
                                <span className="text-xs px-1.5 py-0.5 rounded bg-amber-50 text-amber-600 border border-amber-200 font-normal">
                                  pending
                                </span>
                              )}
                            </td>
                            <td className="px-4 py-2.5 text-right text-slate-500">
                              {row.pending ? '—' : Number(row.pages).toLocaleString()}
                            </td>
                            <td className="px-4 py-2.5 text-right text-slate-700 font-semibold">
                              {row.pending ? '—' : Number(row.chunks).toLocaleString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot>
                        <tr className="bg-slate-50 border-t border-slate-200">
                          <td className="px-4 py-2.5 text-xs font-semibold text-slate-600 uppercase tracking-wider">Total</td>
                          <td className="px-4 py-2.5 text-right text-xs font-semibold text-slate-600">
                            {liveRows.reduce((s, r) => s + Number(r.pages), 0).toLocaleString()}
                          </td>
                          <td className="px-4 py-2.5 text-right text-xs font-semibold text-slate-700">
                            {Number((status.knowledge_base as Record<string, unknown>).total_chunks).toLocaleString()}
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </div>
              )
            })()}
          </div>
        )}

        {tab === 'settings' && settings && (
          <div className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {Object.entries(settings as Record<string, unknown>).map(([k, v]) => (
                <StatCard key={k} label={k.replace(/_/g, ' ')} value={String(v ?? "—")} />
              ))}
            </div>
          </div>
        )}

        {tab === 'analytics' && analytics && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {Object.entries(analytics as Record<string, unknown>).map(([k, v]) => (
                <StatCard key={k} label={k.replace(/_/g, ' ')} value={String(v ?? "—")} />
              ))}
            </div>
            <div>
              <h2 className="text-sm font-semibold text-slate-600 mb-2">Raw data</h2>
              <JsonTree data={analytics} />
            </div>
          </div>
        )}

        {tab === 'feedback' && (
          <div className="space-y-5">
            {/* Summary */}
            {feedback && (feedback.summary as Record<string, unknown>) && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <StatCard label="Total ratings" value={Number((feedback.summary as Record<string, unknown>).total ?? 0)} />
                <StatCard label="👍 Thumbs up" value={Number((feedback.summary as Record<string, unknown>).thumbs_up ?? 0)} />
                <StatCard label="👎 Thumbs down" value={Number((feedback.summary as Record<string, unknown>).thumbs_down ?? 0)} />
                <StatCard label="Positive %" value={`${(feedback.summary as Record<string, unknown>).positive_pct ?? 0}%`} />
              </div>
            )}

            {/* Entries */}
            <div>
              <h2 className="text-sm font-semibold text-slate-600 mb-3">Recent Feedback (last 50)</h2>
              {feedback && (feedback.entries as unknown[])?.length > 0 ? (
                <div className="space-y-2">
                  {(feedback.entries as Record<string, unknown>[]).map((e, i) => (
                    <div key={i} className="bg-white rounded-xl border border-slate-200 px-4 py-3 flex items-start gap-3">
                      <span className={cn(
                        'flex-shrink-0 text-lg mt-0.5',
                        e.rating === 1 ? 'text-emerald-500' : 'text-red-500'
                      )}>
                        {e.rating === 1 ? '👍' : '👎'}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-slate-800 truncate">
                          {String(e.query || '—')}
                        </p>
                        <p className="text-xs text-slate-400 mt-0.5">
                          {new Date(String(e.timestamp)).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-400">No feedback yet.</p>
              )}
            </div>
          </div>
        )}

        {tab === 'refresh' && (
          <div className="space-y-5">
            {/* Stats row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <StatCard label="DB chunks" value={refreshStatus?.chunks_indexed ?? 0} />
              <StatCard label="Files updated" value={refreshStatus?.files_updated ?? 0} />
              <StatCard label="Last run" value={refreshStatus?.last_run ? new Date(refreshStatus.last_run).toLocaleDateString() : 'Never'} />
              <StatCard label="Duration" value={refreshStatus?.last_run_duration_s ? `${refreshStatus.last_run_duration_s}s` : '—'} />
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-slate-700">Knowledge Base Sync</h2>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Syncs AdobeDocs GitHub repos → S3 → ChromaDB → S3 backup
                  </p>
                </div>
                <span className={cn(
                  'text-xs px-2.5 py-1 rounded-full font-medium',
                  rsState === 'running' ? 'bg-blue-50 text-blue-700 border border-blue-200' :
                  rsState === 'success' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                  rsState === 'failed' ? 'bg-red-50 text-red-700 border border-red-200' :
                  'bg-slate-50 text-slate-500 border border-slate-200'
                )}>
                  {rsState}
                </span>
              </div>

              {refreshStatus?.error && (
                <p className="text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2">
                  {refreshStatus.error}
                </p>
              )}

              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => handleRefresh(false)}
                  disabled={refreshing || rsRunning}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium
                    bg-blue-600 text-white hover:bg-blue-700
                    disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <RotateCcw className={cn('w-3.5 h-3.5', (refreshing || rsRunning) && 'animate-spin')} />
                  {rsRunning ? 'Running…' : 'Run on Server'}
                </button>
                <button
                  onClick={() => handleRefresh(true)}
                  disabled={refreshing || rsRunning}
                  className="px-4 py-2 rounded-lg text-sm font-medium border border-slate-200
                    text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Force Full Sync
                </button>
                <button
                  onClick={() => handleTriggerActions(false)}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium
                    bg-slate-800 text-white hover:bg-slate-900 transition-colors"
                  title="Trigger the weekly refresh GitHub Actions workflow"
                >
                  {actionsTriggered ? '✓ Triggered' : '⚡ Run via GitHub Actions'}
                </button>
              </div>
            </div>
            {refreshStatus?.log && refreshStatus.log.length > 0 && (
              <div>
                <h2 className="text-sm font-semibold text-slate-600 mb-2">Last Run Log</h2>
                <pre className="text-xs bg-slate-900 text-slate-100 rounded-xl p-4 overflow-auto max-h-80 leading-relaxed">
                  {refreshStatus.log.join('\n')}
                </pre>
              </div>
            )}
          </div>
        )}

        {loading && (
          <p className="text-sm text-slate-400">Loading…</p>
        )}
      </div>
    </div>
  )
}
