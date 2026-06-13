import { useState, useEffect } from 'react'
import { RotateCcw, ChevronDown, ChevronUp, ChevronRight, Pencil, Check, X, Download } from 'lucide-react'
import { Link } from 'react-router-dom'
import { ArrowLeft, RefreshCw } from 'lucide-react'
import { useAdmin, type GoogleUser, type GoogleUserSummary } from '@/hooks/useAdmin'
import type { PaginatedQueryLogs } from '@/lib/api'
import { cn } from '@/lib/utils'

type Tab = 'status' | 'settings' | 'analytics' | 'feedback' | 'users' | 'queries' | 'refresh'

// ── Google users tab ──────────────────────────────────────────────────────────

type SortField = 'last_seen' | 'total_queries'

interface GoogleUsersTabProps {
  users: GoogleUser[]
  summary: GoogleUserSummary | null
  onRefresh: () => void
  onSetAdmin: (userId: string, isAdmin: boolean) => Promise<unknown>
  onSetDisabled: (userId: string, isDisabled: boolean) => Promise<unknown>
  onSetLimit: (userId: string, limit: number) => Promise<unknown>
}

function GoogleUsersTab({ users, summary, onRefresh, onSetAdmin, onSetDisabled, onSetLimit }: GoogleUsersTabProps) {
  const [search, setSearch] = useState('')
  const [sortField, setSortField] = useState<SortField>('last_seen')
  const [sortAsc, setSortAsc] = useState(false)
  const [editingUserId, setEditingUserId] = useState<string | null>(null)
  const [editValue, setEditValue] = useState<number>(0)
  const [savingUserId, setSavingUserId] = useState<string | null>(null)
  const [savedUserId, setSavedUserId] = useState<string | null>(null)

  const toggleSort = (field: SortField) => {
    if (sortField === field) setSortAsc((v) => !v)
    else { setSortField(field); setSortAsc(false) }
  }

  const filtered = users
    .filter((u) => !search || u.name.toLowerCase().includes(search.toLowerCase()) || u.email.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => {
      let diff = 0
      if (sortField === 'last_seen') {
        diff = (a.last_seen ?? '').localeCompare(b.last_seen ?? '')
      } else {
        diff = a.total_queries - b.total_queries
      }
      return sortAsc ? diff : -diff
    })

  const SortIcon = ({ field }: { field: SortField }) => (
    sortField === field
      ? sortAsc ? <ChevronUp className="w-3 h-3 inline ml-0.5" /> : <ChevronDown className="w-3 h-3 inline ml-0.5" />
      : null
  )

  const startEdit = (user: GoogleUser) => {
    setEditingUserId(user.user_id)
    setEditValue(user.daily_query_limit ?? 20)
  }

  const cancelEdit = () => {
    setEditingUserId(null)
  }

  const saveLimit = async (userId: string) => {
    setSavingUserId(userId)
    try {
      await onSetLimit(userId, editValue)
      setSavedUserId(userId)
      setEditingUserId(null)
      setTimeout(() => setSavedUserId(null), 1500)
    } catch {
      // revert on error
      setEditingUserId(null)
    } finally {
      setSavingUserId(null)
    }
  }

  return (
    <div className="space-y-4">
      {/* Summary row */}
      {summary && (
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wider">Registered users</p>
            <p className="text-2xl font-semibold text-slate-800 mt-1">{summary.total_users}</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wider">Total queries (all time)</p>
            <p className="text-2xl font-semibold text-slate-800 mt-1">{summary.total_queries_all_time.toLocaleString()}</p>
          </div>
        </div>
      )}

      {/* Toolbar */}
      <div className="flex items-center gap-2 justify-between">
        <input
          type="text"
          placeholder="Search name or email…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="px-3 py-1.5 rounded-lg border border-slate-200 text-xs w-52 focus:outline-none focus:border-blue-400"
        />
        <button
          onClick={onRefresh}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50">
              <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Name</th>
              <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Email</th>
              <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">First seen</th>
              <th
                className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider cursor-pointer select-none hover:text-slate-700"
                onClick={() => toggleSort('last_seen')}
              >
                Last seen <SortIcon field="last_seen" />
              </th>
              <th
                className="text-right px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider cursor-pointer select-none hover:text-slate-700"
                onClick={() => toggleSort('total_queries')}
              >
                Queries <SortIcon field="total_queries" />
              </th>
              <th className="text-center px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Admin</th>
              <th className="text-center px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Disabled</th>
              <th className="text-center px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Daily Limit</th>
              <th className="text-center px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Used Today</th>
              <th className="text-center px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Resets At</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={10} className="px-4 py-8 text-center text-sm text-slate-400">
                  {users.length === 0 ? 'No users have signed in yet.' : 'No users match your search.'}
                </td>
              </tr>
            ) : filtered.map((user, i) => (
              <tr key={user.user_id} className={cn('border-b border-slate-100', i === filtered.length - 1 && 'border-0')}>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    {user.picture ? (
                      <img src={user.picture} alt="" className="w-7 h-7 rounded-full flex-shrink-0" referrerPolicy="no-referrer" />
                    ) : (
                      <div className="w-7 h-7 rounded-full bg-slate-200 flex items-center justify-center flex-shrink-0">
                        <span className="text-xs font-medium text-slate-500">{user.name.charAt(0).toUpperCase()}</span>
                      </div>
                    )}
                    <span className="font-medium text-slate-800 text-sm">{user.name || '—'}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-slate-500 text-xs">{user.email}</td>
                <td className="px-4 py-3 text-slate-400 text-xs whitespace-nowrap">
                  {user.first_seen ? new Date(user.first_seen).toLocaleDateString() : '—'}
                </td>
                <td className="px-4 py-3 text-slate-400 text-xs whitespace-nowrap">
                  {user.last_seen ? new Date(user.last_seen).toLocaleDateString() : '—'}
                </td>
                <td className="px-4 py-3 text-right font-semibold text-slate-700">{user.total_queries.toLocaleString()}</td>
                <td className="px-4 py-3 text-center">
                  <button
                    onClick={() => onSetAdmin(user.user_id, !user.is_admin)}
                    title={user.is_admin ? 'Remove admin' : 'Grant admin'}
                    className={cn(
                      'relative w-9 h-5 rounded-full transition-colors flex-shrink-0',
                      user.is_admin ? 'bg-violet-500' : 'bg-slate-300',
                    )}
                  >
                    <span className={cn(
                      'absolute top-0.5 left-0 w-4 h-4 rounded-full bg-white shadow transition-transform',
                      user.is_admin ? 'translate-x-4' : 'translate-x-0.5',
                    )} />
                  </button>
                </td>
                <td className="px-4 py-3 text-center">
                  <button
                    onClick={() => onSetDisabled(user.user_id, !user.is_disabled)}
                    title={user.is_disabled ? 'Re-enable access' : 'Disable access'}
                    className={cn(
                      'relative w-9 h-5 rounded-full transition-colors flex-shrink-0',
                      user.is_disabled ? 'bg-red-500' : 'bg-slate-300',
                    )}
                  >
                    <span className={cn(
                      'absolute top-0.5 left-0 w-4 h-4 rounded-full bg-white shadow transition-transform',
                      user.is_disabled ? 'translate-x-4' : 'translate-x-0.5',
                    )} />
                  </button>
                </td>
                {/* Daily Limit — inline editable */}
                <td className="px-4 py-3 text-center">
                  {editingUserId === user.user_id ? (
                    <div className="flex items-center justify-center gap-1">
                      <input
                        type="number"
                        min={0}
                        max={999}
                        value={editValue}
                        onChange={(e) => setEditValue(Number(e.target.value))}
                        className="w-16 px-1.5 py-1 rounded border border-slate-300 text-xs text-center focus:outline-none focus:border-blue-400"
                        autoFocus
                      />
                      <button
                        onClick={() => saveLimit(user.user_id)}
                        disabled={savingUserId === user.user_id}
                        title="Save"
                        className="text-emerald-600 hover:text-emerald-700 disabled:opacity-50"
                      >
                        <Check className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={cancelEdit} title="Cancel" className="text-slate-400 hover:text-slate-600">
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ) : (
                    <div className={cn(
                      'flex items-center justify-center gap-1 group',
                      savedUserId === user.user_id && 'text-emerald-600',
                    )}>
                      <span className="text-sm font-medium text-slate-700">
                        {user.daily_query_limit ?? 20}
                      </span>
                      <button
                        onClick={() => startEdit(user)}
                        title="Edit limit"
                        className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-blue-500 transition-opacity"
                      >
                        <Pencil className="w-3 h-3" />
                      </button>
                    </div>
                  )}
                </td>
                {/* Used Today */}
                <td className="px-4 py-3 text-center text-sm text-slate-600">
                  {user.daily_query_count ?? 0}
                </td>
                {/* Resets At */}
                <td className="px-4 py-3 text-center text-xs text-slate-400 whitespace-nowrap">
                  {user.daily_reset_at
                    ? new Date(user.daily_reset_at).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
                    : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

type SortCol = 'created_at' | 'email' | 'llm_model' | 'input_tokens' | 'output_tokens' | 'cost_usd'

interface QueryLogsTabProps {
  paginatedData: PaginatedQueryLogs | null
  onFetchPage: (page: number, pageSize: number, sortBy: string, sortOrder: string) => Promise<void>
  onExport: () => Promise<void>
  exporting: boolean
}

function QueryLogsTab({ paginatedData, onFetchPage, onExport, exporting }: QueryLogsTabProps) {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [sortBy, setSortBy] = useState<SortCol>('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [expanded, setExpanded] = useState<Set<number>>(new Set())
  const [exportError, setExportError] = useState(false)
  const [fetching, setFetching] = useState(false)

  const loadPage = (p: number, ps: number, sb: string, so: string) => {
    setFetching(true)
    onFetchPage(p, ps, sb, so).finally(() => setFetching(false))
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { loadPage(page, pageSize, sortBy, sortOrder) }, [page, pageSize, sortBy, sortOrder])

  const handleSort = (col: SortCol) => {
    if (col === sortBy) {
      const next = sortOrder === 'desc' ? 'asc' : 'desc'
      setSortOrder(next)
    } else {
      setSortBy(col)
      setSortOrder('desc')
    }
    setPage(1)
  }

  const handlePageSize = (ps: number) => { setPageSize(ps); setPage(1) }

  const handleExport = async () => {
    setExportError(false)
    try { await onExport() } catch { setExportError(true); setTimeout(() => setExportError(false), 4000) }
  }

  const toggle = (id: number) =>
    setExpanded((prev) => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n })

  const modelBadge = (model: string) => {
    const m = model.toLowerCase()
    if (m === 'haiku') return 'bg-orange-50 text-orange-700 border-orange-200'
    if (m === 'sonnet') return 'bg-violet-50 text-violet-700 border-violet-200'
    return 'bg-slate-50 text-slate-500 border-slate-200'
  }

  const SortIcon = ({ col }: { col: SortCol }) => {
    if (col !== sortBy) return <ChevronDown className="w-3 h-3 text-slate-300 ml-0.5" />
    return sortOrder === 'desc'
      ? <ChevronDown className="w-3 h-3 text-blue-500 ml-0.5" />
      : <ChevronUp className="w-3 h-3 text-blue-500 ml-0.5" />
  }

  const thSort = (col: SortCol, label: string, align = 'left') => (
    <th
      className={cn(
        'px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider cursor-pointer select-none hover:text-slate-700',
        align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left',
      )}
      onClick={() => handleSort(col)}
    >
      <span className="inline-flex items-center gap-0.5">
        {label}<SortIcon col={col} />
      </span>
    </th>
  )

  const logs = paginatedData?.data ?? []
  const pg = paginatedData?.pagination
  const totalCost = logs.reduce((s, l) => s + l.cost_usd, 0)

  // Page number list with ellipsis
  const pageNums = (): (number | '…')[] => {
    if (!pg) return []
    const t = pg.total_pages, c = pg.page
    if (t <= 7) return Array.from({ length: t }, (_, i) => i + 1)
    if (c <= 3) return [1, 2, 3, 4, '…', t]
    if (c >= t - 2) return [1, '…', t - 3, t - 2, t - 1, t]
    return [1, '…', c - 1, c, c + 1, '…', t]
  }

  return (
    <div className="space-y-4">
      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <p className="text-xs text-slate-500 uppercase tracking-wider">Total queries</p>
          <p className="text-2xl font-semibold text-slate-800 mt-1">{pg ? pg.total_records.toLocaleString() : '—'}</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <p className="text-xs text-slate-500 uppercase tracking-wider">Page cost</p>
          <p className="text-2xl font-semibold text-slate-800 mt-1">${totalCost.toFixed(4)}</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <p className="text-xs text-slate-500 uppercase tracking-wider">Page avg cost</p>
          <p className="text-2xl font-semibold text-slate-800 mt-1">${logs.length ? (totalCost / logs.length).toFixed(5) : '0.00000'}</p>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        {/* Page size */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">Rows per page:</span>
          {[25, 50, 100].map((s) => (
            <button
              key={s}
              onClick={() => handlePageSize(s)}
              className={cn(
                'px-2.5 py-1 rounded text-xs font-medium transition-colors',
                pageSize === s ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200',
              )}
            >{s}</button>
          ))}
        </div>

        {/* Export */}
        <div className="flex flex-col items-end gap-0.5">
          <button
            onClick={handleExport}
            disabled={exporting}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
              exporting
                ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                : 'bg-emerald-600 text-white hover:bg-emerald-700',
            )}
          >
            {exporting
              ? <><RefreshCw className="w-3.5 h-3.5 animate-spin" /> Exporting…</>
              : <><Download className="w-3.5 h-3.5" /> Export to Excel</>}
          </button>
          <span className="text-[10px] text-slate-400">Exports all query records</span>
          {exportError && <span className="text-[10px] text-red-500">Export failed. Please try again.</span>}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50">
              <th className="w-8 px-3 py-2.5" />
              {thSort('created_at', 'Time')}
              {thSort('email', 'User')}
              <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Query</th>
              {thSort('llm_model', 'Model', 'center')}
              {thSort('input_tokens', 'In', 'right')}
              {thSort('output_tokens', 'Out', 'right')}
              {thSort('cost_usd', 'Cost', 'right')}
              <th className="text-center px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">FB</th>
            </tr>
          </thead>
          <tbody>
            {fetching && logs.length === 0 ? (
              <tr><td colSpan={9} className="px-4 py-8 text-center text-sm text-slate-400">Loading…</td></tr>
            ) : logs.length === 0 ? (
              <tr><td colSpan={9} className="px-4 py-8 text-center text-sm text-slate-400">No queries logged yet.</td></tr>
            ) : logs.map((log, i) => {
              const isExpanded = expanded.has(log.id)
              const isLast = i === logs.length - 1
              return (
                <>
                  <tr
                    key={log.id}
                    className={cn(
                      'border-b border-slate-100 cursor-pointer hover:bg-slate-50 transition-colors',
                      isExpanded && 'bg-slate-50',
                      isLast && !isExpanded && 'border-0',
                    )}
                    onClick={() => toggle(log.id)}
                  >
                    <td className="w-8 px-3 py-2.5 text-slate-400">
                      {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                    </td>
                    <td className="px-4 py-2.5 text-slate-400 text-xs whitespace-nowrap">
                      {new Date(log.created_at).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })}
                    </td>
                    <td className="px-4 py-2.5 text-slate-500 text-xs max-w-[120px] truncate" title={log.email}>{log.email}</td>
                    <td className="px-4 py-2.5 text-slate-700 text-xs max-w-[260px]">
                      <span className={cn('block', isExpanded ? 'whitespace-normal' : 'truncate')}>{log.query_text}</span>
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      <span className={cn('text-[10px] font-semibold px-1.5 py-0.5 rounded border', modelBadge(log.llm_model))}>
                        {log.llm_model || '—'}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-right text-slate-500 text-xs">{log.input_tokens.toLocaleString()}</td>
                    <td className="px-4 py-2.5 text-right text-slate-500 text-xs">{log.output_tokens.toLocaleString()}</td>
                    <td className="px-4 py-2.5 text-right text-slate-600 text-xs font-mono">${log.cost_usd.toFixed(5)}</td>
                    <td className="px-4 py-2.5 text-center text-base">
                      {log.feedback_rating === 1 ? '👍' : log.feedback_rating === -1 ? '👎' : <span className="text-slate-300 text-xs">—</span>}
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr key={`${log.id}-exp`} className={cn('border-b border-slate-100 bg-slate-50', isLast && 'border-0')}>
                      <td />
                      <td colSpan={8} className="px-4 pb-3 pt-0">
                        <p className="text-xs text-slate-700 leading-relaxed bg-white border border-slate-200 rounded-lg p-3">{log.query_text}</p>
                      </td>
                    </tr>
                  )}
                </>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination footer */}
      {pg && pg.total_pages > 1 && (
        <div className="flex items-center justify-between flex-wrap gap-3">
          <span className="text-xs text-slate-500">
            Showing {((pg.page - 1) * pg.page_size + 1).toLocaleString()}–{Math.min(pg.page * pg.page_size, pg.total_records).toLocaleString()} of {pg.total_records.toLocaleString()} records
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage(pg.page - 1)}
              disabled={!pg.has_prev || fetching}
              className="px-2.5 py-1 rounded text-xs text-slate-600 border border-slate-200 disabled:opacity-40 hover:bg-slate-50 transition-colors"
            >← Prev</button>
            {pageNums().map((n, i) =>
              n === '…'
                ? <span key={`ellipsis-${i}`} className="px-1.5 text-xs text-slate-400">…</span>
                : <button
                    key={n}
                    onClick={() => setPage(n as number)}
                    disabled={fetching}
                    className={cn(
                      'w-7 h-7 rounded text-xs font-medium transition-colors',
                      n === pg.page ? 'bg-blue-600 text-white' : 'text-slate-600 hover:bg-slate-100',
                    )}
                  >{n}</button>
            )}
            <button
              onClick={() => setPage(pg.page + 1)}
              disabled={!pg.has_next || fetching}
              className="px-2.5 py-1 rounded text-xs text-slate-600 border border-slate-200 disabled:opacity-40 hover:bg-slate-50 transition-colors"
            >Next →</button>
          </div>
        </div>
      )}
    </div>
  )
}

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
  const {
    isAuthenticated, login, logout, refresh, resetDemo,
    triggerRefresh, triggerGitHubActions,
    status, settings, analytics, demoStatus, feedback, refreshStatus,
    googleUsers, googleUserSummary, queryLogs, refreshGoogleUsers,
    fetchQueryPage, exportQueries, exporting,
    setGoogleUserAdmin, setUserDisabled,
    killSwitchEnabled, toggleKillSwitch,
    defaultDailyLimit, updateUserDailyLimit, updateDefaultLimit, bulkApplyDefaultLimit,
    loading, error,
  } = useAdmin()
  const [refreshing, setRefreshing] = useState(false)
  const [actionsTriggered, setActionsTriggered] = useState(false)
  const [killSwitchConfirm, setKillSwitchConfirm] = useState(false)
  const [killSwitchPending, setKillSwitchPending] = useState(false)

  // Query Limits settings state
  const [defaultLimitInput, setDefaultLimitInput] = useState<number>(defaultDailyLimit)
  const [savingDefaultLimit, setSavingDefaultLimit] = useState(false)
  const [showBulkConfirm, setShowBulkConfirm] = useState(false)
  const [applyingBulk, setApplyingBulk] = useState(false)
  const [bulkApplyResult, setBulkApplyResult] = useState<string | null>(null)

  const handleSaveDefaultLimit = async () => {
    setSavingDefaultLimit(true)
    try {
      await updateDefaultLimit(defaultLimitInput)
    } catch { /* ignore */ }
    setSavingDefaultLimit(false)
  }

  const handleBulkApply = async () => {
    setApplyingBulk(true)
    try {
      const result = await bulkApplyDefaultLimit()
      setBulkApplyResult(`Updated ${result.users_updated} users to ${result.applied_limit} queries/day.`)
      setTimeout(() => setBulkApplyResult(null), 5000)
      setShowBulkConfirm(false)
      await refreshGoogleUsers()
    } catch { /* ignore */ }
    setApplyingBulk(false)
  }

  const handleKillSwitch = async (enable: boolean) => {
    setKillSwitchPending(true)
    await toggleKillSwitch(enable).catch(() => {})
    setKillSwitchPending(false)
    setKillSwitchConfirm(false)
  }

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
    { id: 'users', label: 'Users' },
    { id: 'queries', label: 'Queries' },
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

            {/* Kill Switch */}
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <div className="flex items-center justify-between flex-wrap gap-3">
                <div>
                  <h2 className="text-sm font-semibold text-slate-700">API Kill Switch</h2>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Disable all chat API calls globally. Auth and admin endpoints stay active.
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className={cn(
                    'text-xs px-2.5 py-1 rounded-full font-medium border',
                    killSwitchEnabled
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      : 'bg-red-50 text-red-700 border-red-200'
                  )}>
                    {killSwitchEnabled ? '● Live' : '● Disabled'}
                  </span>
                  {!killSwitchConfirm ? (
                    <button
                      onClick={() => setKillSwitchConfirm(true)}
                      disabled={killSwitchPending}
                      className={cn(
                        'px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50',
                        killSwitchEnabled
                          ? 'bg-red-100 text-red-700 hover:bg-red-200'
                          : 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200'
                      )}
                    >
                      {killSwitchEnabled ? 'Disable API' : 'Enable API'}
                    </button>
                  ) : (
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-500">Are you sure?</span>
                      <button
                        onClick={() => handleKillSwitch(!killSwitchEnabled)}
                        disabled={killSwitchPending}
                        className={cn(
                          'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                          killSwitchEnabled
                            ? 'bg-red-600 text-white hover:bg-red-700'
                            : 'bg-emerald-600 text-white hover:bg-emerald-700'
                        )}
                      >
                        {killSwitchPending ? 'Updating…' : 'Confirm'}
                      </button>
                      <button
                        onClick={() => setKillSwitchConfirm(false)}
                        className="px-3 py-1.5 rounded-lg text-xs text-slate-500 hover:bg-slate-100 transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  )}
                </div>
              </div>
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
                'Adobe Journey Optimizer',
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

            <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
              <h2 className="text-sm font-semibold text-slate-700">Query Limits</h2>
              <div className="flex items-center gap-3">
                <label className="text-sm text-slate-600 w-48">Default daily limit</label>
                <input
                  type="number"
                  min={1}
                  value={defaultLimitInput}
                  onChange={(e) => setDefaultLimitInput(Number(e.target.value))}
                  className="w-24 rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
                <button
                  onClick={handleSaveDefaultLimit}
                  disabled={savingDefaultLimit}
                  className="text-xs px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {savingDefaultLimit ? 'Saving…' : 'Save'}
                </button>
              </div>
              <div className="flex items-center gap-3">
                {showBulkConfirm ? (
                  <>
                    <span className="text-sm text-amber-700">Apply {defaultLimitInput} to all users?</span>
                    <button
                      onClick={handleBulkApply}
                      disabled={applyingBulk}
                      className="text-xs px-3 py-1.5 rounded-lg bg-amber-600 text-white hover:bg-amber-700 disabled:opacity-50"
                    >
                      {applyingBulk ? 'Applying…' : 'Confirm'}
                    </button>
                    <button
                      onClick={() => setShowBulkConfirm(false)}
                      className="text-xs px-3 py-1.5 rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-50"
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <button
                    onClick={() => setShowBulkConfirm(true)}
                    className="text-xs px-3 py-1.5 rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-50"
                  >
                    Apply default to all users
                  </button>
                )}
              </div>
              {bulkApplyResult && (
                <p className="text-sm text-emerald-700">{bulkApplyResult}</p>
              )}
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
                        <p className="text-sm text-slate-800 break-words">
                          {String(e.query_text || e.query || '—')}
                        </p>
                        <p className="text-xs text-slate-400 mt-0.5">
                          {e.email ? `${String(e.email)} · ` : ''}
                          {new Date(String(e.created_at || e.timestamp)).toLocaleString()}
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

        {tab === 'users' && (
          <GoogleUsersTab
            users={googleUsers}
            summary={googleUserSummary}
            onRefresh={refreshGoogleUsers}
            onSetAdmin={setGoogleUserAdmin}
            onSetDisabled={setUserDisabled}
            onSetLimit={updateUserDailyLimit}
          />
        )}

        {tab === 'queries' && (
          <QueryLogsTab
            paginatedData={queryLogs}
            onFetchPage={fetchQueryPage}
            onExport={exportQueries}
            exporting={exporting}
          />
        )}

        {loading && (
          <p className="text-sm text-slate-400">Loading…</p>
        )}
      </div>
    </div>
  )
}
