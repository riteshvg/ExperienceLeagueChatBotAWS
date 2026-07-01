import { useEffect, useMemo, useState } from 'react'
import { useAuthStore } from '@/store/authStore'
import { ThemeToggle } from '@/components/ThemeToggle'
import { PROMPT_LIBRARY } from '@/lib/prompts'

const VALUE_PROPS = [
  {
    title: 'Grounded answers',
    body: 'Responses drawn from Adobe Experience League documentation.',
  },
  {
    title: 'Multi-product',
    body: 'Analytics, CJA, AEP, Target, and Journey Optimizer in one place.',
  },
  {
    title: 'Built for learning',
    body: 'For exploration and study — verify against official Adobe docs.',
  },
] as const

const SLIDE_MS = 700
const MIN_HOLD_MS = 2200
const MAX_HOLD_MS = 4000
const MS_PER_CHAR = 28

function getHoldMs(text: string) {
  return Math.min(MAX_HOLD_MS, Math.max(MIN_HOLD_MS, text.length * MS_PER_CHAR))
}

function pickRandomIndex(exclude: number, length: number) {
  if (length <= 1) return 0
  let next = exclude
  while (next === exclude) {
    next = Math.floor(Math.random() * length)
  }
  return next
}

function RotatingPromptBox() {
  const prompts = useMemo(
    () => PROMPT_LIBRARY.flatMap((category) => category.prompts.map((p) => p.text)),
    [],
  )
  const [index, setIndex] = useState(0)
  const [upcomingIndex, setUpcomingIndex] = useState(0)
  const [trackY, setTrackY] = useState(0)
  const [animated, setAnimated] = useState(false)

  useEffect(() => {
    if (prompts.length === 0) return

    let cancelled = false
    const timers: number[] = []

    const schedule = (fn: () => void, ms: number) => {
      timers.push(
        window.setTimeout(() => {
          if (!cancelled) fn()
        }, ms),
      )
    }

    const advance = (currentIndex: number, nextIndex: number) => {
      schedule(() => {
        setAnimated(true)
        setTrackY(-48)

        schedule(() => {
          const followingIndex = pickRandomIndex(nextIndex, prompts.length)
          setAnimated(false)
          setTrackY(0)
          setIndex(nextIndex)
          setUpcomingIndex(followingIndex)
          schedule(
            () => advance(nextIndex, followingIndex),
            getHoldMs(prompts[nextIndex]!),
          )
        }, SLIDE_MS)
      }, getHoldMs(prompts[currentIndex]!))
    }

    const startIndex = Math.floor(Math.random() * prompts.length)
    const firstUpcoming = pickRandomIndex(startIndex, prompts.length)
    setIndex(startIndex)
    setUpcomingIndex(firstUpcoming)
    schedule(() => advance(startIndex, firstUpcoming), getHoldMs(prompts[startIndex]!))

    return () => {
      cancelled = true
      timers.forEach((timer) => window.clearTimeout(timer))
    }
  }, [prompts])

  if (prompts.length === 0) return null

  return (
    <div className="mt-6 w-full text-left">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400 mb-2">
        Ask questions like
      </p>
      <div className="rounded-xl border border-emerald-200 dark:border-emerald-800 bg-white dark:bg-slate-900 px-4 py-2 shadow-sm">
        <div className="relative h-12 overflow-hidden" aria-live="polite">
          <div
            className="will-change-transform"
            style={{
              transform: `translateY(${trackY}px)`,
              transition: animated ? `transform ${SLIDE_MS}ms ease-in-out` : 'none',
            }}
          >
            <p className="h-12 flex items-center text-sm text-slate-700 dark:text-slate-200 leading-snug line-clamp-2">
              &ldquo;{prompts[index]}&rdquo;
            </p>
            <p className="h-12 flex items-center text-sm text-slate-700 dark:text-slate-200 leading-snug line-clamp-2">
              &ldquo;{prompts[upcomingIndex]}&rdquo;
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export function LoginPage() {
  const { initiateGoogleLogin, initiateGitHubLogin, isAuthenticated } = useAuthStore()

  const params = new URLSearchParams(window.location.search)
  const oauthError = params.get('error')

  useEffect(() => {
    if (isAuthenticated) {
      window.location.replace(
        import.meta.env.BASE_URL?.replace(/\/$/, '') || '/'
      )
    }
  }, [isAuthenticated])

  return (
    <div className="min-h-screen w-full flex-1 flex flex-col bg-[#F8FAF9] dark:bg-slate-950">
      <header
        className="flex items-center justify-between gap-4 px-6 h-14 shrink-0 border-b border-[#0F3D24] w-full"
        style={{ backgroundColor: '#14532D' }}
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <img
            src={`${import.meta.env.BASE_URL}rovrlogo.png`}
            alt="Rovr"
            className="h-7 w-auto shrink-0"
          />
          <span className="text-white font-semibold text-sm tracking-wide">Rovr</span>
        </div>
        <div className="flex items-center gap-4 sm:gap-6 shrink-0">
          <ThemeToggle variant="brand" showLabel={false} />
          <a
            href="https://thelearningproject.in"
            className="text-xs sm:text-sm text-white/80 hover:text-white transition-colors whitespace-nowrap"
          >
            The Learning Project
          </a>
          <a
            href="https://experienceleague.adobe.com/docs"
            className="text-xs sm:text-sm text-white/80 hover:text-white transition-colors whitespace-nowrap"
          >
            Experience League docs
          </a>
        </div>
      </header>

      <main className="flex-1 w-full flex items-stretch">
        <div className="w-full grid grid-cols-1 md:grid-cols-2 md:min-h-0">
          {/* Sign in — left on desktop */}
          <section className="order-2 md:order-1 flex flex-col items-center justify-center px-6 py-10 md:px-10 lg:px-16 md:py-12 text-center md:border-r border-emerald-200/80 dark:border-emerald-900/50">
            <div className="w-full max-w-sm mx-auto">
              <img
                src={`${import.meta.env.BASE_URL}rovrlogo.png`}
                alt="Rovr"
                className="h-12 w-auto mx-auto mb-4"
              />
              <h1 className="text-xl lg:text-2xl font-semibold text-[#14532D] tracking-tight">
                Sign in to Rovr
              </h1>
            <p className="mt-4 text-sm lg:text-base text-slate-500 leading-relaxed max-w-sm">
              Use your preferred account to get started. Sign-in helps us manage
              fair-use limits and prevent abuse.
            </p>

            {oauthError && (
              <p className="mt-4 text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2 max-w-sm w-full">
                Sign-in failed ({oauthError.replace(/_/g, ' ')}). Please try again.
              </p>
            )}

            <div className="mt-8 flex flex-col gap-3">
              <button
                onClick={initiateGoogleLogin}
                className="inline-flex items-center justify-center gap-3 px-6 py-3 rounded-full
                  bg-[#14532D] text-white text-sm font-medium
                  hover:bg-[#10B981] transition-colors shadow-sm"
              >
                <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
                  <path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.615z"/>
                  <path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.258c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z"/>
                  <path fill="#FBBC05" d="M3.964 10.707A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.707V4.961H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.039l3.007-2.332z"/>
                  <path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.961L3.964 7.293C4.672 5.163 6.656 3.58 9 3.58z"/>
                </svg>
                Sign in with Google
              </button>

              <button
                onClick={initiateGitHubLogin}
                className="inline-flex items-center justify-center gap-3 px-6 py-3 rounded-full
                  border border-slate-300 bg-white text-slate-800 text-sm font-medium
                  hover:border-slate-400 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900
                  dark:text-slate-100 dark:hover:bg-slate-800 transition-colors shadow-sm"
              >
                <svg width="18" height="18" viewBox="0 0 16 16" aria-hidden="true" className="fill-current">
                  <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82A7.6 7.6 0 0 1 8 3.87c.68 0 1.36.09 2 .26 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
                </svg>
                Sign in with GitHub
              </button>
            </div>

            <p className="mt-10 text-xs text-slate-400 leading-relaxed">
              Your profile is used only for authentication. Questions are
              processed by Claude (Anthropic) — do not share sensitive information.
            </p>
            </div>
          </section>

          {/* Ask — right on desktop */}
          <section className="order-1 md:order-2 flex flex-col items-center justify-center px-6 py-10 md:px-10 lg:px-16 md:py-12 text-center border-b md:border-b-0 border-emerald-200/80 dark:border-emerald-900/50">
            <div className="w-full max-w-lg mx-auto">
            <h1 className="text-3xl lg:text-4xl font-semibold text-[#14532D] dark:text-emerald-300 tracking-tight">
              Ask about Adobe Experience League docs
            </h1>
            <p className="mt-4 text-sm lg:text-base text-slate-500 dark:text-slate-400 leading-relaxed">
              Your AI powered guide for questions on Analytics, CJA, Experience
              Platform, Target, and Journey Optimizer.
            </p>

            <RotatingPromptBox />

            <ul className="mt-8 space-y-4 text-left">
              {VALUE_PROPS.map(({ title, body }) => (
                <li key={title} className="flex gap-3">
                  <span
                    className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full"
                    style={{ backgroundColor: '#10B981' }}
                    aria-hidden="true"
                  />
                  <div>
                    <p className="text-sm font-medium text-slate-700 dark:text-slate-200">{title}</p>
                    <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">{body}</p>
                  </div>
                </li>
              ))}
            </ul>
            </div>
          </section>
        </div>
      </main>

      <footer className="shrink-0 px-6 py-4 text-center border-t border-emerald-100 dark:border-emerald-900/50">
        <p className="text-xs text-slate-400 dark:text-slate-500">
          Built for learning purposes only. Not affiliated with or endorsed by Adobe.
        </p>
      </footer>
    </div>
  )
}
