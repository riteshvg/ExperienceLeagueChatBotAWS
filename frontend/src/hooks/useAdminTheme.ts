import { useCallback, useEffect, useState } from 'react'

const STORAGE_KEY = 'rovr-admin-theme'

export type AdminTheme = 'light' | 'dark'

function readStoredTheme(): AdminTheme {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === 'dark' || stored === 'light') return stored
  } catch {
    /* ignore */
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function useAdminTheme() {
  const [theme, setTheme] = useState<AdminTheme>(() => readStoredTheme())

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, theme)
    } catch {
      /* ignore */
    }
  }, [theme])

  const toggleTheme = useCallback(() => {
    setTheme((t) => (t === 'dark' ? 'light' : 'dark'))
  }, [])

  return { theme, isDark: theme === 'dark', setTheme, toggleTheme }
}
