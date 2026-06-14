import { create } from 'zustand'
import { getUserQuota } from '@/lib/api'

interface QuotaState {
  monthlyLimit: number
  monthlyUsed: number
  monthlyRemaining: number
  resetDate: string | null
  isNewUser: boolean
  isExhausted: boolean
  fetchQuota: () => Promise<void>
}

export const useQuotaStore = create<QuotaState>()((set) => ({
  monthlyLimit: 999999,
  monthlyUsed: 0,
  monthlyRemaining: 999999,
  resetDate: null,
  isNewUser: false,
  isExhausted: false,

  fetchQuota: async () => {
    try {
      const q = await getUserQuota()
      set({
        monthlyLimit: q.monthly_limit,
        monthlyUsed: q.monthly_used,
        monthlyRemaining: q.monthly_remaining,
        resetDate: q.reset_date,
        isNewUser: q.is_new_user,
        isExhausted: q.monthly_remaining <= 0 && q.monthly_limit < 999999,
      })
    } catch {
      // silent — don't break the app if quota fetch fails
    }
  },
}))
