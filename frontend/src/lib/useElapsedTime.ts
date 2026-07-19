import { useEffect, useState } from 'react'

function formatElapsed(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000))
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

/**
 * mm:ss elapsed since `createdAt`, ticking every second. Computed from the
 * server-provided timestamp (not a client-only start-time counter), so it
 * stays correct across component remounts within the same session. Stops
 * ticking once `frozen` is true (phase === 'complete') — the debrief screen
 * shouldn't show a live-updating timer.
 */
export function useElapsedTime(createdAt: string | null, frozen: boolean): string {
  const [display, setDisplay] = useState('0:00')

  useEffect(() => {
    if (!createdAt) {
      setDisplay('0:00')
      return
    }
    const startMs = new Date(createdAt).getTime()
    setDisplay(formatElapsed(Date.now() - startMs))

    if (frozen) return // debrief screen: don't keep ticking

    const id = window.setInterval(() => {
      setDisplay(formatElapsed(Date.now() - startMs))
    }, 1000)
    return () => window.clearInterval(id)
  }, [createdAt, frozen])

  return display
}
