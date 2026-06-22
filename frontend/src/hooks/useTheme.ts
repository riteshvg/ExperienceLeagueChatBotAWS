import { useCallback, useEffect, useState } from 'react'

const STORAGE_KEY = 'rovr-theme'
const LEGACY_ADMIN_KEY = 'rovr-admin-theme'

export type AppTheme = 'light' | 'dark'

function readStoredTheme(): AppTheme {
  try {
    let stored = localStorage.getItem(STORAGE_KEY)
    if (!stored) {
      const legacy = localStorage.getItem(LEGACY_ADMIN_KEY)
      if (legacy === 'dark' || legacy === 'light') {
        stored = legacy
        localStorage.setItem(STORAGE_KEY, legacy)
      }
    }
    if (stored === 'dark' || stored === 'light') return stored
  } catch {
    /* ignore */
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

/** Apply theme class before React mounts to avoid flash of wrong theme. */
export function initTheme(): AppTheme {
  const theme = readStoredTheme()
  document.documentElement.classList.toggle('dark', theme === 'dark')
  return theme
}

export function useTheme() {
  const [theme, setThemeState] = useState<AppTheme>(() =>
    document.documentElement.classList.contains('dark') ? 'dark' : 'light',
  )

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    try {
      localStorage.setItem(STORAGE_KEY, theme)
    } catch {
      /* ignore */
    }
  }, [theme])

  const setTheme = useCallback((next: AppTheme) => setThemeState(next), [])
  const toggleTheme = useCallback(() => {
    setThemeState((t) => (t === 'dark' ? 'light' : 'dark'))
  }, [])

  return { theme, isDark: theme === 'dark', setTheme, toggleTheme }
}
