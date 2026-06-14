/**
 * usePageView — fires a page_view analytics event on every route change.
 *
 * Must be rendered inside a React Router <BrowserRouter> / <Router> context.
 * Mount it once near the root of the app (inside the router, outside any Route).
 *
 * @example
 *   // In a component inside <BrowserRouter>:
 *   function RouterAnalytics() {
 *     usePageView()
 *     return null
 *   }
 */

import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { trackPageView } from './events'

/** Map a React Router pathname to a human-readable Adobe Analytics page name. */
function toPageName(pathname: string): string {
  const clean = pathname.replace(/\/$/, '') || '/'
  if (clean === '/') return 'rovr:chat'
  if (clean === '/admin') return 'rovr:admin'
  if (clean === '/login') return 'rovr:login'
  if (clean === '/callback') return 'rovr:callback'
  // Fallback: convert /foo/bar → rovr:foo:bar
  return `rovr:${clean.replace(/^\//, '').replace(/\//g, ':')}`
}

/**
 * Hook that fires trackPageView() on mount and on every pathname change.
 * Has no visible return value — use it in a render-null component.
 */
export function usePageView(): void {
  const location = useLocation()

  useEffect(() => {
    trackPageView(toPageName(location.pathname))
    // Only re-fire on actual path changes, not hash/search changes
  }, [location.pathname]) // eslint-disable-line react-hooks/exhaustive-deps
}
