import { useState, useEffect } from 'react'
import { RotateCcw, Plus, Pencil, Eye, Trash2, X, ChevronLeft, ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { ArrowLeft, RefreshCw } from 'lucide-react'
import { useAdmin, type AdminUser } from '@/hooks/useAdmin'
import type { UsageLog } from '@/lib/api'
import { cn } from '@/lib/utils'

type Tab = 'status' | 'settings' | 'analytics' | 'feedback' | 'users' | 'refresh'

// ── User management sub-components ───────────────────────────────────────────

interface DrawerProps {
  open: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
}
function Drawer({ open, onClose, title, children }: DrawerProps) {
  return (
    <>
      {open && (
        <div
          className="fixed inset-0 bg-black/20 z-40"
          onClick={onClose}
        />
      )}
      <div className={cn(
        'fixed top-0 right-0 h-full w-96 bg-white shadow-xl z-50 flex flex-col transition-transform duration-200',
        open ? 'translate-x-0' : 'translate-x-full',
      )}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200">
          <h2 className="text-sm font-semibold text-slate-800">{title}</h2>
          <button onClick={onClose} className="p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-5">
          {children}
        </div>
      </div>
    </>
  )
}

interface UserFormValues {
  username: string
  password: string
  role: 'user' | 'demo'
  question_limit: string
  is_active: boolean
}

interface UserFormProps {
  initial?: UserFormValues
  editMode?: boolean
  onSubmit: (values: UserFormValues) => Promise<void>
  onCancel: () => void
  submitLabel: string
}
function UserForm({ initial, editMode, onSubmit, onCancel, submitLabel }: UserFormProps) {
  const [values, setValues] = useState<UserFormValues>(
    initial ?? { username: '', password: '', role: 'user', question_limit: '', is_active: true }
  )
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!values.username.trim()) { setFormError('Username is required'); return }
    if (!editMode && !values.password.trim()) { setFormError('Password is required'); return }
    setFormError(null)
    setSubmitting(true)
    try {
      await onSubmit(values)
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {formError && (
        <p className="text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2">{formError}</p>
      )}

      <div>
        <label className="block text-xs font-medium text-slate-600 mb-1">Username</label>
        <input
          type="text"
          value={values.username}
          onChange={(e) => setValues({ ...values, username: e.target.value })}
          disabled={editMode}
          className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400 disabled:bg-slate-50 disabled:text-slate-400"
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-slate-600 mb-1">
          Password{editMode && <span className="text-slate-400 font-normal"> (leave blank to keep current)</span>}
        </label>
        <input
          type="text"
          value={values.password}
          onChange={(e) => setValues({ ...values, password: e.target.value })}
          placeholder={editMode ? 'New password (optional)' : 'Password'}
          className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-slate-600 mb-1">Role</label>
        <select
          value={values.role}
          onChange={(e) => setValues({ ...values, role: e.target.value as 'user' | 'demo' })}
          className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:border-blue-400"
        >
          <option value="user">User</option>
          <option value="demo">Demo</option>
        </select>
      </div>

      <div>
        <label className="block text-xs font-medium text-slate-600 mb-1">
          Question Limit <span className="text-slate-400 font-normal">(empty = unlimited)</span>
        </label>
        <input
          type="number"
          min={1}
          value={values.question_limit}
          onChange={(e) => setValues({ ...values, question_limit: e.target.value })}
          placeholder="Unlimited"
          className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
        />
      </div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => setValues({ ...values, is_active: !values.is_active })}
          className={cn(
            'relative w-10 h-5 rounded-full transition-colors flex-shrink-0',
            values.is_active ? 'bg-emerald-500' : 'bg-slate-300',
          )}
        >
          <span className={cn(
            'absolute top-0.5 left-0 w-4 h-4 rounded-full bg-white shadow transition-transform',
            values.is_active ? 'translate-x-5' : 'translate-x-0.5',
          )} />
        </button>
        <span className="text-sm text-slate-600">{values.is_active ? 'Active' : 'Disabled'}</span>
      </div>

      <div className="flex gap-2 pt-2">
        <button
          type="submit"
          disabled={submitting}
          className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {submitting ? 'Saving…' : submitLabel}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="flex-1 border border-slate-200 text-slate-600 py-2 rounded-lg text-sm hover:bg-slate-50 transition-colors"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}

// ── User detail panel ─────────────────────────────────────────────────────────

const USAGE_PAGE_SIZE = 20

interface UserDetailProps {
  user: AdminUser
  fetchUsage: (id: number) => Promise<unknown>
  fetchFeedback: (id: number) => Promise<unknown>
  onBack: () => void
}
function UserDetail({ user, fetchUsage, fetchFeedback, onBack }: UserDetailProps) {
  const [usageLogs, setUsageLogs] = useState<UsageLog[]>([])
  const [feedbackEntries, setFeedbackEntries] = useState<Record<string, unknown>[]>([])
  const [page, setPage] = useState(0)
  const [expandedLog, setExpandedLog] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.all([fetchUsage(user.id), fetchFeedback(user.id)]).then(([u, f]) => {
      setUsageLogs(((u as Record<string, unknown>)?.logs as UsageLog[]) ?? [])
      setFeedbackEntries(((f as Record<string, unknown>)?.entries as Record<string, unknown>[]) ?? [])
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [user.id, fetchUsage, fetchFeedback])

  const totalCost = usageLogs.reduce((s, l) => s + l.total_cost_usd, 0)
  const avgCost = usageLogs.length ? totalCost / usageLogs.length : 0
  const pageCount = Math.ceil(usageLogs.length / USAGE_PAGE_SIZE)
  const pageSlice = usageLogs.slice(page * USAGE_PAGE_SIZE, (page + 1) * USAGE_PAGE_SIZE)

  return (
    <div className="space-y-5">
      {/* Back + header */}
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700"
        >
          <ChevronLeft className="w-3.5 h-3.5" /> Back to list
        </button>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-base font-semibold text-slate-800">{user.username}</h2>
            <div className="flex items-center gap-2 mt-1">
              <span className={cn(
                'text-xs px-2 py-0.5 rounded-full font-medium border',
                user.role === 'demo'
                  ? 'bg-amber-50 text-amber-700 border-amber-200'
                  : 'bg-blue-50 text-blue-700 border-blue-200',
              )}>
                {user.role}
              </span>
              <span className={cn(
                'text-xs px-2 py-0.5 rounded-full font-medium border',
                user.is_active
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-red-50 text-red-600 border-red-200',
              )}>
                {user.is_active ? 'Active' : 'Disabled'}
              </span>
            </div>
          </div>
          <span className="text-xs text-slate-400">
            Created {new Date(user.created_at).toLocaleDateString()}
          </span>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <p className="text-xs text-slate-500 uppercase tracking-wider">Questions</p>
          <p className="text-lg font-semibold text-slate-800 mt-1">{user.question_count}</p>
          {user.question_limit != null && (
            <p className="text-xs text-slate-400">of {user.question_limit} limit</p>
          )}
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <p className="text-xs text-slate-500 uppercase tracking-wider">Total Cost</p>
          <p className="text-lg font-semibold text-slate-800 mt-1">${totalCost.toFixed(4)}</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <p className="text-xs text-slate-500 uppercase tracking-wider">Avg/Question</p>
          <p className="text-lg font-semibold text-slate-800 mt-1">${avgCost.toFixed(4)}</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <p className="text-xs text-slate-500 uppercase tracking-wider">Last Active</p>
          <p className="text-sm font-semibold text-slate-800 mt-1 break-all">
            {user.last_seen_at ? new Date(user.last_seen_at).toLocaleDateString() : '—'}
          </p>
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-slate-400">Loading usage…</p>
      ) : (
        <>
          {/* Usage logs — expandable cards */}
          <div>
            <h3 className="text-sm font-semibold text-slate-600 mb-2">
              Usage Logs ({usageLogs.length})
            </h3>
            {usageLogs.length === 0 ? (
              <p className="text-sm text-slate-400">No usage logged yet.</p>
            ) : (
              <>
                <div className="space-y-2">
                  {pageSlice.map((log) => {
                    const isExpanded = expandedLog === log.id
                    return (
                      <div
                        key={log.id}
                        className="bg-white rounded-xl border border-slate-200 overflow-hidden"
                      >
                        {/* Summary row — always visible, click to expand */}
                        <button
                          onClick={() => setExpandedLog(isExpanded ? null : log.id)}
                          className="w-full text-left px-4 py-3 flex items-center gap-3 hover:bg-slate-50 transition-colors"
                        >
                          <ChevronRight className={cn(
                            'w-3.5 h-3.5 text-slate-400 flex-shrink-0 transition-transform',
                            isExpanded && 'rotate-90',
                          )} />
                          <span className="text-xs text-slate-400 whitespace-nowrap w-16 flex-shrink-0">
                            {new Date(log.created_at).toLocaleDateString()}
                          </span>
                          <span className="flex-1 text-sm text-slate-700 text-left">
                            {log.question_text ?? '—'}
                          </span>
                          <span className="text-xs text-slate-400 flex-shrink-0 ml-2">{log.model ?? '—'}</span>
                          <span className="text-xs text-slate-400 flex-shrink-0 ml-3 hidden sm:block">
                            {log.prompt_tokens.toLocaleString()} / {log.completion_tokens.toLocaleString()} tok
                          </span>
                          <span className="text-xs font-semibold text-slate-700 flex-shrink-0 ml-3">
                            ${log.total_cost_usd.toFixed(4)}
                          </span>
                        </button>

                        {/* Expanded detail */}
                        {isExpanded && (
                          <div className="border-t border-slate-100 px-4 py-4 space-y-4 bg-slate-50">
                            <div>
                              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Question</p>
                              <p className="text-sm text-slate-800 leading-relaxed bg-white rounded-lg border border-slate-200 px-3 py-2.5">
                                {log.question_text ?? '—'}
                              </p>
                            </div>
                            <div>
                              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Answer</p>
                              <div className="text-sm text-slate-700 leading-relaxed bg-white rounded-lg border border-slate-200 px-3 py-2.5 whitespace-pre-wrap max-h-80 overflow-y-auto">
                                {log.answer_text || <span className="text-slate-400 italic">No answer recorded</span>}
                              </div>
                            </div>
                            <div className="flex gap-4 text-xs text-slate-500">
                              <span>Model: <strong className="text-slate-700">{log.model ?? '—'}</strong></span>
                              <span>Input tokens: <strong className="text-slate-700">{log.prompt_tokens.toLocaleString()}</strong></span>
                              <span>Output tokens: <strong className="text-slate-700">{log.completion_tokens.toLocaleString()}</strong></span>
                              <span>Cost: <strong className="text-slate-700">${log.total_cost_usd.toFixed(4)}</strong></span>
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
                {pageCount > 1 && (
                  <div className="flex items-center justify-between mt-3 px-1">
                    <span className="text-xs text-slate-400">Page {page + 1} of {pageCount}</span>
                    <div className="flex gap-1">
                      <button
                        onClick={() => setPage((p) => Math.max(0, p - 1))}
                        disabled={page === 0}
                        className="p-1 rounded disabled:opacity-30 hover:bg-slate-100"
                      >
                        <ChevronLeft className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
                        disabled={page >= pageCount - 1}
                        className="p-1 rounded disabled:opacity-30 hover:bg-slate-100"
                      >
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Feedback table */}
          <div>
            <h3 className="text-sm font-semibold text-slate-600 mb-2">
              Feedback ({feedbackEntries.length})
            </h3>
            {feedbackEntries.length === 0 ? (
              <p className="text-sm text-slate-400">No feedback submitted yet.</p>
            ) : (
              <div className="space-y-2">
                {feedbackEntries.slice(0, 20).map((e, i) => (
                  <div key={i} className="bg-white rounded-xl border border-slate-200 px-4 py-3 flex items-start gap-3">
                    <span className={cn('text-lg flex-shrink-0', e.rating === 1 ? 'text-emerald-500' : 'text-red-500')}>
                      {e.rating === 1 ? '👍' : '👎'}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-slate-800 truncate">{String(e.query ?? '—')}</p>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {new Date(String(e.timestamp)).toLocaleString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}

// ── User list panel ───────────────────────────────────────────────────────────

interface UsersTabProps {
  users: AdminUser[]
  onRefresh: () => void
  onAdd: (values: UserFormValues) => Promise<void>
  onEdit: (id: number, values: UserFormValues) => Promise<void>
  onToggleActive: (user: AdminUser) => Promise<void>
  onDelete: (id: number) => Promise<void>
  fetchUsage: (id: number) => Promise<unknown>
  fetchFeedback: (id: number) => Promise<unknown>
}

function UsersTab({
  users, onRefresh, onAdd, onEdit, onToggleActive, onDelete,
  fetchUsage, fetchFeedback,
}: UsersTabProps) {
  const [view, setView] = useState<'list' | 'detail'>('list')
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [drawerMode, setDrawerMode] = useState<'add' | 'edit'>('add')
  const [editTarget, setEditTarget] = useState<AdminUser | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null)
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState<'all' | 'user' | 'demo'>('all')
  const [activeFilter, setActiveFilter] = useState<'all' | 'active' | 'disabled'>('all')

  const filtered = users.filter((u) => {
    if (search && !u.username.toLowerCase().includes(search.toLowerCase())) return false
    if (roleFilter !== 'all' && u.role !== roleFilter) return false
    if (activeFilter === 'active' && !u.is_active) return false
    if (activeFilter === 'disabled' && u.is_active) return false
    return true
  })

  if (view === 'detail' && selectedUser) {
    return (
      <UserDetail
        user={selectedUser}
        fetchUsage={fetchUsage}
        fetchFeedback={fetchFeedback}
        onBack={() => { setView('list'); setSelectedUser(null) }}
      />
    )
  }

  const openAdd = () => {
    setDrawerMode('add')
    setEditTarget(null)
    setDrawerOpen(true)
  }

  const openEdit = (user: AdminUser) => {
    setDrawerMode('edit')
    setEditTarget(user)
    setDrawerOpen(true)
  }

  const handleFormSubmit = async (values: UserFormValues) => {
    const payload = {
      username: values.username,
      password: values.password,
      role: values.role,
      question_limit: values.question_limit ? parseInt(values.question_limit, 10) : null,
      is_active: values.is_active,
    }
    if (drawerMode === 'add') {
      await onAdd(values)
    } else if (editTarget) {
      const editPayload: Record<string, unknown> = {
        role: values.role,
        is_active: values.is_active,
        question_limit: values.question_limit ? parseInt(values.question_limit, 10) : null,
      }
      if (values.password) editPayload.password = values.password
      await onEdit(editTarget.id, values)
    }
    setDrawerOpen(false)
  }

  return (
    <>
      <div className="space-y-4">
        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-2 justify-between">
          <div className="flex items-center gap-2 flex-wrap">
            <input
              type="text"
              placeholder="Search username…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="px-3 py-1.5 rounded-lg border border-slate-200 text-xs w-44 focus:outline-none focus:border-blue-400"
            />
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value as typeof roleFilter)}
              className="px-2 py-1.5 rounded-lg border border-slate-200 text-xs focus:outline-none"
            >
              <option value="all">All roles</option>
              <option value="user">User</option>
              <option value="demo">Demo</option>
            </select>
            <select
              value={activeFilter}
              onChange={(e) => setActiveFilter(e.target.value as typeof activeFilter)}
              className="px-2 py-1.5 rounded-lg border border-slate-200 text-xs focus:outline-none"
            >
              <option value="all">All statuses</option>
              <option value="active">Active</option>
              <option value="disabled">Disabled</option>
            </select>
          </div>
          <button
            onClick={openAdd}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" /> Add User
          </button>
        </div>

        {/* Table */}
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Username</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Role</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
                <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Questions</th>
                <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Cost</th>
                <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Limit</th>
                <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Last Seen</th>
                <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-6 text-center text-sm text-slate-400">
                    No users found.
                  </td>
                </tr>
              ) : filtered.map((user, i) => (
                <tr key={user.id} className={cn('border-b border-slate-100', i === filtered.length - 1 && 'border-0')}>
                  <td className="px-4 py-3 font-medium text-slate-800">{user.username}</td>
                  <td className="px-4 py-3">
                    <span className={cn(
                      'text-xs px-2 py-0.5 rounded-full border font-medium',
                      user.role === 'demo'
                        ? 'bg-amber-50 text-amber-700 border-amber-200'
                        : 'bg-blue-50 text-blue-700 border-blue-200',
                    )}>
                      {user.role}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => onToggleActive(user)}
                      title={user.is_active ? 'Click to disable' : 'Click to enable'}
                      className={cn(
                        'relative w-9 h-5 rounded-full transition-colors flex-shrink-0',
                        user.is_active ? 'bg-emerald-500' : 'bg-slate-300',
                      )}
                    >
                      <span className={cn(
                        'absolute top-0.5 left-0 w-4 h-4 rounded-full bg-white shadow transition-transform',
                        user.is_active ? 'translate-x-4' : 'translate-x-0.5',
                      )} />
                    </button>
                  </td>
                  <td className="px-4 py-3 text-right text-slate-600">{user.question_count}</td>
                  <td className="px-4 py-3 text-right text-slate-600">${user.total_cost_usd.toFixed(4)}</td>
                  <td className="px-4 py-3 text-right text-slate-500">
                    {user.question_limit ?? '∞'}
                  </td>
                  <td className="px-4 py-3 text-right text-slate-400 text-xs">
                    {user.last_seen_at ? new Date(user.last_seen_at).toLocaleDateString() : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => { setSelectedUser(user); setView('detail') }}
                        title="View details"
                        className="p-1.5 rounded-lg text-slate-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => openEdit(user)}
                        title="Edit user"
                        className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => setDeleteConfirm(user.id)}
                        title="Delete user"
                        className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Delete confirm */}
        {deleteConfirm !== null && (
          <div className="fixed inset-0 bg-black/20 z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl border border-slate-200 shadow-xl p-6 w-full max-w-sm">
              <h3 className="text-sm font-semibold text-slate-800 mb-2">Delete user?</h3>
              <p className="text-xs text-slate-500 mb-4">
                This will permanently delete the user and all their usage logs.
              </p>
              <div className="flex gap-2">
                <button
                  onClick={async () => { await onDelete(deleteConfirm); setDeleteConfirm(null) }}
                  className="flex-1 bg-red-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-red-700 transition-colors"
                >
                  Delete
                </button>
                <button
                  onClick={() => setDeleteConfirm(null)}
                  className="flex-1 border border-slate-200 text-slate-600 py-2 rounded-lg text-sm hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Drawer */}
      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={drawerMode === 'add' ? 'Add User' : 'Edit User'}
      >
        <UserForm
          editMode={drawerMode === 'edit'}
          initial={editTarget ? {
            username: editTarget.username,
            password: '',
            role: editTarget.role,
            question_limit: editTarget.question_limit != null ? String(editTarget.question_limit) : '',
            is_active: Boolean(editTarget.is_active),
          } : undefined}
          onSubmit={handleFormSubmit}
          onCancel={() => setDrawerOpen(false)}
          submitLabel={drawerMode === 'add' ? 'Create User' : 'Save Changes'}
        />
      </Drawer>
    </>
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
    users, addUser, editUser, removeUser, fetchUserUsage, fetchUserFeedback,
    loading, error,
  } = useAdmin()
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
    { id: 'users', label: 'Users' },
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

        {tab === 'users' && (
          <UsersTab
            users={users}
            onRefresh={refresh}
            onAdd={async (values) => {
              await addUser({
                username: values.username,
                password: values.password,
                role: values.role,
                question_limit: values.question_limit ? parseInt(values.question_limit, 10) : null,
                is_active: values.is_active,
              })
            }}
            onEdit={async (id, values) => {
              const payload: Record<string, unknown> = {
                role: values.role,
                is_active: values.is_active,
                question_limit: values.question_limit ? parseInt(values.question_limit, 10) : null,
              }
              if (values.password) payload.password = values.password
              await editUser(id, payload as Parameters<typeof editUser>[1])
            }}
            onToggleActive={async (user) => {
              await editUser(user.id, { is_active: !user.is_active })
            }}
            onDelete={removeUser}
            fetchUsage={fetchUserUsage}
            fetchFeedback={fetchUserFeedback}
          />
        )}

        {loading && (
          <p className="text-sm text-slate-400">Loading…</p>
        )}
      </div>
    </div>
  )
}
