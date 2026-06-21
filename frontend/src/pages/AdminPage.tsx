import { useState, useEffect } from 'react'
import { RotateCcw, ChevronDown, ChevronUp, ChevronRight, Pencil, Check, X, Download, Moon, Sun } from 'lucide-react'
import { Link } from 'react-router-dom'
import { ArrowLeft, RefreshCw } from 'lucide-react'
import { useAdmin, type GoogleUser, type GoogleUserSummary } from '@/hooks/useAdmin'
import { useAdminTheme } from '@/hooks/useAdminTheme'
import type { PaginatedQueryLogs } from '@/lib/api'
import { cn } from '@/lib/utils'
import { adminUi as ui } from '@/pages/adminUi'
import {
  formatAdminValue,
  formatAdminDate,
  formatAdminDateShort,
  formatAdminTime,
  isDemoStatus,
  isFeedbackPayload,
  isRecord,
  SETTINGS_DISPLAY,
  componentDetails,
} from '@/pages/adminFormat'

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
  onSetMonthlyLimit: (userId: string, limit: number) => Promise<unknown>
}

function GoogleUsersTab({ users, summary, onRefresh, onSetAdmin, onSetDisabled, onSetLimit, onSetMonthlyLimit }: GoogleUsersTabProps) {
  const [search, setSearch] = useState('')
  const [sortField, setSortField] = useState<SortField>('last_seen')
  const [sortAsc, setSortAsc] = useState(false)
  // Daily limit edit state
  const [editingUserId, setEditingUserId] = useState<string | null>(null)
  const [editValue, setEditValue] = useState<number>(0)
  const [savingUserId, setSavingUserId] = useState<string | null>(null)
  const [savedUserId, setSavedUserId] = useState<string | null>(null)
  // Monthly limit edit state
  const [editingMonthlyUserId, setEditingMonthlyUserId] = useState<string | null>(null)
  const [editMonthlyValue, setEditMonthlyValue] = useState<number>(0)
  const [savingMonthlyUserId, setSavingMonthlyUserId] = useState<string | null>(null)
  const [savedMonthlyUserId, setSavedMonthlyUserId] = useState<string | null>(null)

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
      setEditingUserId(null)
    } finally {
      setSavingUserId(null)
    }
  }

  const startEditMonthly = (user: GoogleUser) => {
    setEditingMonthlyUserId(user.user_id)
    setEditMonthlyValue(user.monthly_query_limit ?? 20)
  }

  const cancelEditMonthly = () => setEditingMonthlyUserId(null)

  const saveMonthlyLimit = async (userId: string) => {
    setSavingMonthlyUserId(userId)
    try {
      await onSetMonthlyLimit(userId, editMonthlyValue)
      setSavedMonthlyUserId(userId)
      setEditingMonthlyUserId(null)
      setTimeout(() => setSavedMonthlyUserId(null), 1500)
    } catch {
      setEditingMonthlyUserId(null)
    } finally {
      setSavingMonthlyUserId(null)
    }
  }

  return (
    <div className="space-y-4">
      {/* Summary row */}
      {summary && (
        <div className="grid grid-cols-2 gap-3">
          <div className={cn(ui.card, 'p-4')}>
            <p className={ui.statLabel}>Registered users</p>
            <p className={ui.statValueLg}>{summary.total_users}</p>
          </div>
          <div className={cn(ui.card, 'p-4')}>
            <p className={ui.statLabel}>Total queries (all time)</p>
            <p className={ui.statValueLg}>{summary.total_queries_all_time.toLocaleString()}</p>
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
          className={cn(ui.input, 'w-52 focus:border-blue-400 dark:focus:border-blue-500')}
        />
        <button
          onClick={onRefresh}
          className={cn('flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-colors', ui.headerBtn)}
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
      </div>

      {/* Table — full width, compact columns so all fields fit without scrolling */}
      <div className={cn(ui.card, 'overflow-visible')}>
        <table className="w-full text-xs table-fixed">
          <thead>
            <tr className={ui.tableHead}>
              <th className={cn(ui.th, 'w-[12%]')}>Name</th>
              <th className={cn(ui.th, 'w-[14%]')}>Email</th>
              <th className={cn(ui.th, 'w-[7%]')}>First seen</th>
              <th
                className={cn(ui.thSort, 'w-[7%]')}
                onClick={() => toggleSort('last_seen')}
              >
                Last seen <SortIcon field="last_seen" />
              </th>
              <th
                className={cn(ui.thSort, 'w-[6%] text-right')}
                onClick={() => toggleSort('total_queries')}
              >
                Queries <SortIcon field="total_queries" />
              </th>
              <th className={cn(ui.th, 'w-[5%] text-center')}>Admin</th>
              <th className={cn(ui.th, 'w-[5%] text-center')}>Disabled</th>
              <th className={cn(ui.th, 'w-[8%] text-center')}>Daily Limit</th>
              <th className={cn(ui.th, 'w-[9%] text-center')}>Monthly Limit</th>
              <th className={cn(ui.th, 'w-[6%] text-center')}>Used Today</th>
              <th className={cn(ui.th, 'w-[7%] text-center')}>Resets At</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={11} className={ui.empty}>
                  {users.length === 0 ? 'No users have signed in yet.' : 'No users match your search.'}
                </td>
              </tr>
            ) : filtered.map((user, i) => (
              <tr key={user.user_id} className={cn(ui.tr, i === filtered.length - 1 && 'border-0')}>
                <td className="px-3 py-2.5">
                  <div className="flex items-center gap-1.5 min-w-0">
                    {user.picture ? (
                      <img src={user.picture} alt="" className="w-6 h-6 rounded-full flex-shrink-0" referrerPolicy="no-referrer" />
                    ) : (
                      <div className="w-6 h-6 rounded-full bg-slate-200 dark:bg-slate-700 flex items-center justify-center flex-shrink-0">
                        <span className="text-[10px] font-medium text-slate-500 dark:text-slate-300">{user.name.charAt(0).toUpperCase()}</span>
                      </div>
                    )}
                    <span className="font-medium text-slate-800 dark:text-slate-100 text-xs truncate">{user.name || '—'}</span>
                  </div>
                </td>
                <td className="px-3 py-2.5 text-slate-500 dark:text-slate-400 text-xs truncate" title={user.email}>{user.email}</td>
                <td className="px-3 py-2.5 text-slate-400 dark:text-slate-500 text-xs whitespace-nowrap">
                  {formatAdminDateShort(user.first_seen)}
                </td>
                <td className="px-3 py-2.5 text-slate-400 dark:text-slate-500 text-xs whitespace-nowrap">
                  {formatAdminDateShort(user.last_seen)}
                </td>
                <td className="px-3 py-2.5 text-right font-semibold text-slate-700 dark:text-slate-200">{user.total_queries.toLocaleString()}</td>
                <td className="px-3 py-2.5 text-center">
                  <button
                    onClick={() => onSetAdmin(user.user_id, !user.is_admin)}
                    title={user.is_admin ? 'Remove admin' : 'Grant admin'}
                    className={cn(
                      'relative w-9 h-5 rounded-full transition-colors flex-shrink-0',
                      user.is_admin ? 'bg-violet-500' : 'bg-slate-300 dark:bg-slate-600',
                    )}
                  >
                    <span className={cn(
                      'absolute top-0.5 left-0 w-4 h-4 rounded-full bg-white shadow transition-transform',
                      user.is_admin ? 'translate-x-4' : 'translate-x-0.5',
                    )} />
                  </button>
                </td>
                <td className="px-3 py-2.5 text-center">
                  <button
                    onClick={() => onSetDisabled(user.user_id, !user.is_disabled)}
                    title={user.is_disabled ? 'Re-enable access' : 'Disable access'}
                    className={cn(
                      'relative w-9 h-5 rounded-full transition-colors flex-shrink-0',
                      user.is_disabled ? 'bg-red-500' : 'bg-slate-300 dark:bg-slate-600',
                    )}
                  >
                    <span className={cn(
                      'absolute top-0.5 left-0 w-4 h-4 rounded-full bg-white shadow transition-transform',
                      user.is_disabled ? 'translate-x-4' : 'translate-x-0.5',
                    )} />
                  </button>
                </td>
                {/* Daily Limit — inline editable */}
                <td className="px-3 py-2.5 text-center">
                  {editingUserId === user.user_id ? (
                    <div className="flex items-center justify-center gap-1">
                      <input
                        type="number"
                        min={0}
                        max={999}
                        value={editValue}
                        onChange={(e) => setEditValue(Number(e.target.value))}
                        className="w-14 px-1 py-0.5 rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-xs text-center focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
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
                      <button onClick={cancelEdit} title="Cancel" className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300">
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ) : (
                    <div className={cn(
                      'flex items-center justify-center gap-1 group',
                      savedUserId === user.user_id && 'text-emerald-600 dark:text-emerald-400',
                    )}>
                      <span className="text-xs font-medium text-slate-700 dark:text-slate-200">
                        {user.daily_query_limit ?? 20}
                      </span>
                      <button
                        onClick={() => startEdit(user)}
                        title="Edit limit"
                        className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-blue-500 dark:hover:text-blue-400 transition-opacity"
                      >
                        <Pencil className="w-3 h-3" />
                      </button>
                    </div>
                  )}
                </td>
                {/* Monthly Limit — inline editable */}
                <td className="px-3 py-2.5 text-center">
                  {editingMonthlyUserId === user.user_id ? (
                    <div className="flex items-center justify-center gap-1">
                      <input
                        type="number"
                        min={0}
                        max={999999}
                        value={editMonthlyValue}
                        onChange={(e) => setEditMonthlyValue(Number(e.target.value))}
                        className="w-16 px-1 py-0.5 rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-xs text-center focus:outline-none focus:border-blue-400 dark:focus:border-blue-500"
                        autoFocus
                      />
                      <button
                        onClick={() => saveMonthlyLimit(user.user_id)}
                        disabled={savingMonthlyUserId === user.user_id}
                        title="Save"
                        className="text-emerald-600 hover:text-emerald-700 disabled:opacity-50"
                      >
                        <Check className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={cancelEditMonthly} title="Cancel" className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300">
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ) : (
                    <div className={cn(
                      'flex items-center justify-center gap-1 group',
                      savedMonthlyUserId === user.user_id && 'text-emerald-600 dark:text-emerald-400',
                    )}>
                      <span className="text-xs font-medium text-slate-700 dark:text-slate-200">
                        {(user.monthly_query_limit ?? 999999) >= 999999 ? '∞' : user.monthly_query_limit}
                      </span>
                      <button
                        onClick={() => startEditMonthly(user)}
                        title="Edit monthly limit"
                        className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-blue-500 dark:hover:text-blue-400 transition-opacity"
                      >
                        <Pencil className="w-3 h-3" />
                      </button>
                    </div>
                  )}
                </td>
                {/* Used Today */}
                <td className="px-3 py-2.5 text-center text-xs text-slate-600 dark:text-slate-300">
                  {user.daily_query_count ?? 0}
                </td>
                {/* Resets At */}
                <td className="px-3 py-2.5 text-center text-xs text-slate-400 dark:text-slate-500 whitespace-nowrap">
                  {formatAdminTime(user.daily_reset_at)}
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
        'px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider cursor-pointer select-none hover:text-slate-700 dark:text-slate-200',
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
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
          <p className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wider">Total queries</p>
          <p className="text-2xl font-semibold text-slate-800 dark:text-slate-100 mt-1">{pg ? pg.total_records.toLocaleString() : '—'}</p>
        </div>
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
          <p className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wider">Page cost</p>
          <p className="text-2xl font-semibold text-slate-800 dark:text-slate-100 mt-1">${totalCost.toFixed(4)}</p>
        </div>
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
          <p className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wider">Page avg cost</p>
          <p className="text-2xl font-semibold text-slate-800 dark:text-slate-100 mt-1">${logs.length ? (totalCost / logs.length).toFixed(5) : '0.00000'}</p>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        {/* Page size */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500 dark:text-slate-400">Rows per page:</span>
          {[25, 50, 100].map((s) => (
            <button
              key={s}
              onClick={() => handlePageSize(s)}
              className={cn(
                'px-2.5 py-1 rounded text-xs font-medium transition-colors',
                pageSize === s ? 'bg-blue-600 text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 hover:bg-slate-200',
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
                ? 'bg-slate-100 dark:bg-slate-800 text-slate-400 cursor-not-allowed'
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
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/80">
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
              <tr><td colSpan={9} className="px-4 py-8 text-center text-sm text-slate-400 dark:text-slate-500">Loading…</td></tr>
            ) : logs.length === 0 ? (
              <tr><td colSpan={9} className="px-4 py-8 text-center text-sm text-slate-400 dark:text-slate-500">No queries logged yet.</td></tr>
            ) : logs.map((log, i) => {
              const isExpanded = expanded.has(log.id)
              const isLast = i === logs.length - 1
              return (
                <>
                  <tr
                    key={log.id}
                    className={cn(
                      'border-b border-slate-100 dark:border-slate-800 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors',
                      isExpanded && 'bg-slate-50',
                      isLast && !isExpanded && 'border-0',
                    )}
                    onClick={() => toggle(log.id)}
                  >
                    <td className="w-8 px-3 py-2.5 text-slate-400">
                      {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                    </td>
                    <td className="px-4 py-2.5 text-slate-400 text-xs whitespace-nowrap">
                      {formatAdminDate(log.created_at)}
                    </td>
                    <td className="px-4 py-2.5 text-slate-500 text-xs max-w-[120px] truncate" title={log.email || undefined}>
                      {log.email || '—'}
                    </td>
                    <td className="px-4 py-2.5 text-slate-700 dark:text-slate-200 text-xs max-w-[260px]">
                      <span className={cn('block', isExpanded ? 'whitespace-normal' : 'truncate')}>
                        {log.query_text || '—'}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      {log.llm_model ? (
                        <span className={cn('text-[10px] font-semibold px-1.5 py-0.5 rounded border', modelBadge(log.llm_model))}>
                          {log.llm_model}
                        </span>
                      ) : (
                        <span className="text-slate-300 dark:text-slate-600 text-xs">—</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-right text-slate-500 text-xs">{(log.input_tokens ?? 0).toLocaleString()}</td>
                    <td className="px-4 py-2.5 text-right text-slate-500 text-xs">{(log.output_tokens ?? 0).toLocaleString()}</td>
                    <td className="px-4 py-2.5 text-right text-slate-600 text-xs font-mono">${(log.cost_usd ?? 0).toFixed(5)}</td>
                    <td className="px-4 py-2.5 text-center text-base">
                      {log.feedback_rating === 1 ? '👍' : log.feedback_rating === -1 ? '👎' : <span className="text-slate-300 text-xs">—</span>}
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr key={`${log.id}-exp`} className={cn('border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/80', isLast && 'border-0')}>
                      <td />
                      <td colSpan={8} className="px-4 pb-3 pt-0 space-y-2">
                        <p className="text-xs text-slate-700 dark:text-slate-200 leading-relaxed bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg p-3">{log.query_text}</p>
                        {log.feedback_rating != null && (
                          <p className="text-xs text-slate-600 px-1">
                            {log.feedback_rating === 1
                              ? '👍'
                              : log.feedback_comment
                                ? <>👎 Feedback: <span className="italic">"{log.feedback_comment}"</span></>
                                : '👎'}
                          </p>
                        )}
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
          <span className="text-xs text-slate-500 dark:text-slate-400">
            Showing {((pg.page - 1) * pg.page_size + 1).toLocaleString()}–{Math.min(pg.page * pg.page_size, pg.total_records).toLocaleString()} of {pg.total_records.toLocaleString()} records
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage(pg.page - 1)}
              disabled={!pg.has_prev || fetching}
              className="px-2.5 py-1 rounded text-xs text-slate-600 border border-slate-200 disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
            >← Prev</button>
            {pageNums().map((n, i) =>
              n === '…'
                ? <span key={`ellipsis-${i}`} className="px-1.5 text-xs text-slate-400 dark:text-slate-500">…</span>
                : <button
                    key={n}
                    onClick={() => setPage(n as number)}
                    disabled={fetching}
                    className={cn(
                      'w-7 h-7 rounded text-xs font-medium transition-colors',
                      n === pg.page ? 'bg-blue-600 text-white' : 'text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800 dark:bg-slate-800',
                    )}
                  >{n}</button>
            )}
            <button
              onClick={() => setPage(pg.page + 1)}
              disabled={!pg.has_next || fetching}
              className="px-2.5 py-1 rounded text-xs text-slate-600 border border-slate-200 disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
            >Next →</button>
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string | number | unknown }) {
  return (
    <div className={cn(ui.card, 'p-4')}>
      <p className={ui.statLabel}>{label}</p>
      <p className={ui.statValue}>{formatAdminValue(value)}</p>
    </div>
  )
}

function ThemeToggle({ isDark, onToggle }: { isDark: boolean; onToggle: () => void }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      className={cn('flex items-center gap-1.5', ui.headerBtn)}
    >
      {isDark ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
      {isDark ? 'Light' : 'Dark'}
    </button>
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
    defaultMonthlyLimit, updateUserMonthlyLimit, updateDefaultMonthlyLimit,
    loading, error,
  } = useAdmin()
  const { isDark, toggleTheme } = useAdminTheme()
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
  const [defaultMonthlyLimitInput, setDefaultMonthlyLimitInput] = useState<number>(defaultMonthlyLimit)
  const [savingDefaultMonthlyLimit, setSavingDefaultMonthlyLimit] = useState(false)

  const handleSaveDefaultLimit = async () => {
    setSavingDefaultLimit(true)
    try {
      await updateDefaultLimit(defaultLimitInput)
    } catch { /* ignore */ }
    setSavingDefaultLimit(false)
  }

  const handleSaveDefaultMonthlyLimit = async () => {
    setSavingDefaultMonthlyLimit(true)
    try {
      await updateDefaultMonthlyLimit(defaultMonthlyLimitInput)
    } catch { /* ignore */ }
    setSavingDefaultMonthlyLimit(false)
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
      <div className={cn(ui.page, 'flex items-center justify-center p-4', isDark && 'dark')}>
        <div className={ui.loginCard}>
          <div className="flex items-center justify-between gap-2 mb-6">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center">
                <span className="text-white text-xs font-bold">EL</span>
              </div>
              <h1 className={cn('font-semibold', ui.headerTitle)}>Admin Panel</h1>
            </div>
            <ThemeToggle isDark={isDark} onToggle={toggleTheme} />
          </div>

          {error && (
            <p className={ui.error}>{error}</p>
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
              className={ui.inputLg}
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
            <Link to="/" className={cn('text-xs', ui.headerLink)}>
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
    <div className={cn(ui.page, isDark && 'dark')}>
      <div className={ui.shell}>
      {/* Header */}
      <header className={cn(ui.header, 'w-full px-4 sm:px-6 py-3 flex items-center justify-between')}>
        <div className="flex items-center gap-3">
          <Link to="/" className={ui.headerLink}>
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <h1 className={ui.headerTitle}>Admin Panel</h1>
        </div>
        <div className="flex items-center gap-2">
          <ThemeToggle isDark={isDark} onToggle={toggleTheme} />
          <button
            onClick={refresh}
            disabled={loading}
            className={cn('flex items-center gap-1.5', ui.headerBtn)}
          >
            <RefreshCw className={cn('w-3.5 h-3.5', loading && 'animate-spin')} />
            Refresh
          </button>
          <button
            onClick={logout}
            className={ui.headerBtnDanger}
          >
            Sign out
          </button>
        </div>
      </header>

      {/* Tab nav */}
      <div className={cn(ui.tabNav, 'w-full px-4 sm:px-6')}>
        <nav className="flex gap-0">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={cn(
                'px-4 py-3 text-sm border-b-2 transition-colors',
                tab === t.id ? ui.tabActive : ui.tabInactive,
              )}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Content */}
      <div className="w-full px-4 sm:px-6 py-6">
        {tab === 'status' && status && (
          <div className="space-y-6">

            {/* Demo account */}
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Demo Account</h2>
                <span className="text-xs text-slate-400 dark:text-slate-500">demo / demo</span>
              </div>
              {isDemoStatus(demoStatus) ? (
                <div className="flex items-center gap-6">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <div className="flex-1 h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className={cn(
                            'h-2 rounded-full transition-all',
                            demoStatus.exhausted
                              ? 'bg-red-400'
                              : (demoStatus.questions_used as number) > 0
                              ? 'bg-amber-400'
                              : 'bg-emerald-400',
                          )}
                          style={{
                            width: `${Math.min(
                              100,
                              ((demoStatus.questions_used as number) / (demoStatus.questions_limit as number)) * 100,
                            )}%`,
                          }}
                        />
                      </div>
                      <span className="text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">
                        {demoStatus.questions_used as number} / {demoStatus.questions_limit as number} used
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 dark:text-slate-500">
                      {demoStatus.exhausted
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
                <p className="text-sm text-slate-400 dark:text-slate-500">Loading demo status…</p>
              )}
            </div>

            {/* Kill Switch */}
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
              <div className="flex items-center justify-between flex-wrap gap-3">
                <div>
                  <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">API Kill Switch</h2>
                  <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
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
                      <span className="text-xs text-slate-500 dark:text-slate-400">Are you sure?</span>
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
                        className="px-3 py-1.5 rounded-lg text-xs text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 dark:bg-slate-800 transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-slate-600 dark:text-slate-300">Components</h2>
                {status.environment != null && (
                  <span className="text-xs text-slate-500 dark:text-slate-400 capitalize">
                    {formatAdminValue(status.environment)}
                  </span>
                )}
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {Object.entries(status.components as Record<string, Record<string, unknown>>).map(
                  ([name, info]) => {
                    const details = componentDetails(name, info)
                    return (
                    <div
                      key={name}
                      className={cn(
                        'bg-white dark:bg-slate-900 rounded-xl border p-4',
                        info.healthy ? 'border-emerald-200 dark:border-emerald-900' : 'border-red-200 dark:border-red-900',
                      )}
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className={cn(
                            'w-2 h-2 rounded-full',
                            info.healthy ? 'bg-emerald-400' : 'bg-red-400',
                          )}
                        />
                        <p className="text-sm font-medium text-slate-700 dark:text-slate-200 capitalize">{name.replace(/_/g, ' ')}</p>
                      </div>
                      {details.map((line) => (
                        <p key={line} className="text-xs text-slate-400 dark:text-slate-500 mt-1 truncate" title={line}>
                          {line}
                        </p>
                      ))}
                    </div>
                    )
                  },
                )}
              </div>
            </div>

            {Boolean(status.knowledge_base) && (() => {
              type KbRow = { product: string; pages: number; chunks: number }
              const liveRows: KbRow[] = ((status.knowledge_base as Record<string, unknown>).product_breakdown as Array<Record<string, unknown>> ?? [])
                .map((r) => ({
                  product: String(r.product ?? 'Unknown'),
                  pages: Number(r.pages) || 0,
                  chunks: Number(r.chunks) || 0,
                }))
                .filter((r) => r.chunks > 0)
              const kb = status.knowledge_base as Record<string, unknown>
              return (
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h2 className="text-sm font-semibold text-slate-600 dark:text-slate-300">Knowledge Base</h2>
                    <span className="text-xs text-slate-400 dark:text-slate-500">
                      Last refreshed: {formatAdminDateShort(kb.last_refreshed)}
                    </span>
                  </div>
                  {liveRows.length === 0 ? (
                    <p className="text-sm text-slate-400 dark:text-slate-500">No indexed products yet.</p>
                  ) : (
                  <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/80">
                          <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Product</th>
                          <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Pages</th>
                          <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Chunks</th>
                        </tr>
                      </thead>
                      <tbody>
                        {liveRows.map((row, i) => (
                          <tr key={row.product} className={cn('border-b border-slate-100 dark:border-slate-800', i === liveRows.length - 1 && 'border-0')}>
                            <td className="px-4 py-2.5 text-slate-700 dark:text-slate-200 font-medium">
                              {row.product}
                            </td>
                            <td className="px-4 py-2.5 text-right text-slate-500">
                              {row.pages.toLocaleString()}
                            </td>
                            <td className="px-4 py-2.5 text-right text-slate-700 dark:text-slate-200 font-semibold">
                              {row.chunks.toLocaleString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot>
                        <tr className="bg-slate-50 dark:bg-slate-800/80 border-t border-slate-200 dark:border-slate-700">
                          <td className="px-4 py-2.5 text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider">Total</td>
                          <td className="px-4 py-2.5 text-right text-xs font-semibold text-slate-600 dark:text-slate-300">
                            {liveRows.reduce((s, r) => s + r.pages, 0).toLocaleString()}
                          </td>
                          <td className="px-4 py-2.5 text-right text-xs font-semibold text-slate-700 dark:text-slate-200">
                            {Number(kb.total_chunks ?? 0).toLocaleString()}
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                  )}
                </div>
              )
            })()}
          </div>
        )}

        {tab === 'settings' && settings && (
          <div className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {SETTINGS_DISPLAY.map(({ key, label }) => (
                <StatCard key={key} label={label} value={(settings as Record<string, unknown>)[key]} />
              ))}
            </div>

            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-5 space-y-4">
              <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Query Limits</h2>
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
                <label className="text-sm text-slate-600 w-48">Default monthly limit</label>
                <input
                  type="number"
                  min={1}
                  value={defaultMonthlyLimitInput}
                  onChange={(e) => setDefaultMonthlyLimitInput(Number(e.target.value))}
                  className="w-24 rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                />
                <button
                  onClick={handleSaveDefaultMonthlyLimit}
                  disabled={savingDefaultMonthlyLimit}
                  className="text-xs px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {savingDefaultMonthlyLimit ? 'Saving…' : 'Save'}
                </button>
                <span className="text-xs text-slate-400 dark:text-slate-500">For new signups only</span>
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
                      className="text-xs px-3 py-1.5 rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800"
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <button
                    onClick={() => setShowBulkConfirm(true)}
                    className="text-xs px-3 py-1.5 rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800"
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

        {tab === 'analytics' && analytics && (() => {
          const rateLimits = isRecord(analytics.rate_limits) ? analytics.rate_limits : null
          const topUser = rateLimits?.highest_usage_email
            ? `${rateLimits.highest_usage_email} (${formatAdminValue(rateLimits.highest_usage_count)})`
            : '—'
          const sessionMetrics = [
            { label: 'Active sessions', value: analytics.active_sessions },
            { label: 'Total turns', value: analytics.total_turns },
          ]
          const limitMetrics = rateLimits ? [
            { label: 'Users at daily limit', value: rateLimits.users_at_limit },
            { label: 'Users above 75% of limit', value: rateLimits.users_above_75pct },
            {
              label: 'Avg queries (active users)',
              value: typeof rateLimits.avg_queries_active_users === 'number'
                ? rateLimits.avg_queries_active_users.toFixed(1)
                : '—',
            },
            { label: 'Highest usage today', value: topUser },
          ] : []
          return (
          <div className="space-y-6">
            <div>
              <h2 className="text-sm font-semibold text-slate-600 dark:text-slate-300 mb-3">Sessions</h2>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {sessionMetrics.map(({ label, value }) => (
                  <StatCard key={label} label={label} value={value} />
                ))}
              </div>
            </div>
            {limitMetrics.length > 0 && (
              <div>
                <h2 className="text-sm font-semibold text-slate-600 dark:text-slate-300 mb-3">Daily query limits</h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {limitMetrics.map(({ label, value }) => (
                    <StatCard key={label} label={label} value={value} />
                  ))}
                </div>
              </div>
            )}
          </div>
          )
        })()}

        {tab === 'feedback' && (
          <div className="space-y-5">
            {/* Summary */}
            {isFeedbackPayload(feedback) && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <StatCard label="Total ratings" value={feedback.summary.total} />
                <StatCard label="👍 Thumbs up" value={feedback.summary.thumbs_up} />
                <StatCard label="👎 Thumbs down" value={feedback.summary.thumbs_down} />
                <StatCard label="Positive %" value={`${feedback.summary.positive_pct ?? 0}%`} />
              </div>
            )}

            {/* Entries */}
            <div>
              <h2 className="text-sm font-semibold text-slate-600 dark:text-slate-300 mb-3">Recent Feedback (last 50)</h2>
              {isFeedbackPayload(feedback) && feedback.entries.length > 0 ? (
                <div className="space-y-2">
                  {feedback.entries.map((entry, i) => {
                    if (!isRecord(entry)) return null
                    const queryText = String(entry.query_text || entry.query || '—')
                    const comment = String(entry.comment || '').trim()
                    return (
                    <div key={i} className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 px-4 py-3 flex items-start gap-3">
                      <span className={cn(
                        'flex-shrink-0 text-lg mt-0.5',
                        entry.rating === 1 ? 'text-emerald-500' : 'text-red-500'
                      )}>
                        {entry.rating === 1 ? '👍' : '👎'}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-800 dark:text-slate-100 break-words">
                          {queryText}
                        </p>
                        {comment && (
                          <p className="text-sm text-slate-600 dark:text-slate-300 mt-1.5 break-words">
                            <span className="text-slate-500 dark:text-slate-400 font-medium">Comment: </span>
                            {comment}
                          </p>
                        )}
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                          {entry.email ? `${String(entry.email)} · ` : ''}
                          {formatAdminDate(entry.created_at || entry.timestamp)}
                        </p>
                      </div>
                    </div>
                    )
                  })}
                </div>
              ) : (
                <p className="text-sm text-slate-400 dark:text-slate-500">No feedback yet.</p>
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
              <StatCard label="Last run" value={refreshStatus?.last_run ? formatAdminDateShort(refreshStatus.last_run) : 'Never'} />
              <StatCard label="Duration" value={refreshStatus?.last_run_duration_s ? `${refreshStatus.last_run_duration_s}s` : '—'} />
            </div>

            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Knowledge Base Sync</h2>
                  <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
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
                    text-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed"
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
                <h2 className="text-sm font-semibold text-slate-600 dark:text-slate-300 mb-2">Last Run Log</h2>
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
            onSetMonthlyLimit={updateUserMonthlyLimit}
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
          <p className={ui.loading}>Loading…</p>
        )}
      </div>
      </div>
    </div>
  )
}
