import { create } from 'zustand'
import {
  fetchConversations,
  fetchConversationMessages,
  type ConversationSummary,
  type Message,
} from '@/lib/api'
import { useChatStore } from './chatStore'

export interface ConversationGroup {
  label: string
  items: ConversationSummary[]
}

const DAY_MS = 86_400_000
const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

function startOfDay(d: Date): number {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
}

/**
 * Buckets: Today, Yesterday, Previous 7 days, then by calendar month (most
 * recent first). Boundaries are local calendar days, not rolling 24h windows —
 * a conversation from exactly 7 days ago lands in "Previous 7 days", not the
 * month bucket, matching the Today/Yesterday cutoffs also being day-aligned.
 */
export function groupConversationsByDate(
  conversations: ConversationSummary[],
  now: Date = new Date(),
): ConversationGroup[] {
  const todayStart = startOfDay(now)
  const yesterdayStart = todayStart - DAY_MS
  const sevenDaysAgoStart = todayStart - 7 * DAY_MS

  const today: ConversationSummary[] = []
  const yesterday: ConversationSummary[] = []
  const previous7: ConversationSummary[] = []
  const byMonth = new Map<string, ConversationSummary[]>()

  for (const c of conversations) {
    const created = new Date(c.created_at)
    const dayStart = startOfDay(created)
    if (dayStart === todayStart) {
      today.push(c)
    } else if (dayStart === yesterdayStart) {
      yesterday.push(c)
    } else if (dayStart >= sevenDaysAgoStart) {
      previous7.push(c)
    } else {
      const key = `${created.getFullYear()}-${String(created.getMonth() + 1).padStart(2, '0')}`
      if (!byMonth.has(key)) byMonth.set(key, [])
      byMonth.get(key)!.push(c)
    }
  }

  const groups: ConversationGroup[] = []
  if (today.length) groups.push({ label: 'Today', items: today })
  if (yesterday.length) groups.push({ label: 'Yesterday', items: yesterday })
  if (previous7.length) groups.push({ label: 'Previous 7 days', items: previous7 })

  // "YYYY-MM" sorts lexically in chronological order — reverse for most-recent-first
  const monthKeys = Array.from(byMonth.keys()).sort().reverse()
  for (const key of monthKeys) {
    const [yr, mo] = key.split('-').map(Number)
    const label = now.getFullYear() === yr ? MONTH_NAMES[mo - 1] : `${MONTH_NAMES[mo - 1]} ${yr}`
    groups.push({ label, items: byMonth.get(key)! })
  }
  return groups
}

interface HistoryState {
  conversations: ConversationSummary[]
  loading: boolean
  messagesLoading: boolean
  currentConversationId: string | null
  error: string | null
  fetchConversations: () => Promise<void>
  loadConversation: (id: string) => Promise<void>
  reset: () => void
}

export const useHistoryStore = create<HistoryState>()((set, get) => ({
  conversations: [],
  loading: false,
  messagesLoading: false,
  currentConversationId: null,
  error: null,

  fetchConversations: async () => {
    set({ loading: true, error: null })
    try {
      const conversations = await fetchConversations()
      set({ conversations, loading: false })
    } catch (err) {
      set({ loading: false, error: err instanceof Error ? err.message : String(err) })
    }
  },

  // Pure database read — never resubmits the original query to the chat pipeline.
  loadConversation: async (id: string) => {
    if (get().messagesLoading || useChatStore.getState().isStreaming) return
    set({ messagesLoading: true, currentConversationId: id, error: null })
    try {
      const rows = await fetchConversationMessages(id)
      const title = get().conversations.find((c) => c.id === id)?.title ?? 'Conversation'
      const messages: Message[] = rows.map((m) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        citations: m.citations ?? undefined,
        streaming: false,
      }))
      useChatStore.getState().loadHistoricalSession(id, title, messages)
      set({ messagesLoading: false })
    } catch (err) {
      set({ messagesLoading: false, error: err instanceof Error ? err.message : String(err) })
    }
  },

  reset: () => set({ conversations: [], currentConversationId: null, loading: false, messagesLoading: false, error: null }),
}))
