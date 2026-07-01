import { Link } from 'react-router-dom'
import { ArrowLeft, BookOpen, Info, ShieldCheck } from 'lucide-react'

const sections = [
  {
    icon: Info,
    title: 'Independent learning tool',
    body:
      'Rovr is not affiliated with, endorsed by, sponsored by, or officially associated with Adobe. Adobe, Adobe Experience Cloud, Adobe Experience Platform, Adobe Analytics, Customer Journey Analytics, Adobe Target, Adobe Journey Optimizer, and related product names are trademarks or registered trademarks of Adobe and are used here only to describe the documentation topics Rovr helps people learn.',
  },
  {
    icon: BookOpen,
    title: 'Why Rovr exists',
    body:
      'Adobe Experience League is deep, useful, and constantly expanding. Rovr was built to make that knowledge easier to explore: ask a practical question, get a grounded answer, and jump back to the source documentation when you need the official details. The goal is to reduce the friction between having a question and finding the right starting point.',
  },
  {
    icon: ShieldCheck,
    title: 'Use it responsibly',
    body:
      'Rovr uses AI to summarize and navigate documentation, so answers can be incomplete, outdated, or wrong. Treat responses as learning aids, not official guidance. Always verify important implementation, legal, security, privacy, or business decisions against official Adobe documentation and your organization’s policies.',
  },
]

export function AboutPage() {
  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-slate-100">
      <div className="mx-auto flex min-h-screen w-full max-w-4xl flex-col px-5 py-6 sm:px-8">
        <div className="mb-8 flex items-center justify-between gap-3">
          <Link
            to="/"
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-600 no-underline transition-colors hover:border-emerald-300 hover:text-[#14532D] dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-emerald-700 dark:hover:text-emerald-300"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Rovr
          </Link>
        </div>

        <section className="mb-8">
          <img
            src={`${import.meta.env.BASE_URL}rovrlogo.png`}
            alt="Rovr"
            className="mb-4 h-12 w-auto"
          />
          <p className="mb-2 text-sm font-semibold uppercase text-emerald-700 dark:text-emerald-300">
            About Rovr
          </p>
          <h1 className="mb-4 text-3xl font-semibold tracking-normal text-slate-900 dark:text-white sm:text-4xl">
            A companion for exploring Adobe Experience League documentation.
          </h1>
          <p className="max-w-3xl text-base leading-7 text-slate-600 dark:text-slate-300">
            Rovr helps learners, practitioners, and implementation teams move from broad documentation
            libraries to concrete answers faster, while keeping the official sources close.
          </p>
        </section>

        <div className="grid gap-4">
          {sections.map(({ icon: Icon, title, body }) => (
            <section
              key={title}
              className="rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900"
            >
              <div className="mb-3 flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-50 text-[#14532D] dark:bg-emerald-950/50 dark:text-emerald-300">
                  <Icon className="h-4 w-4" />
                </div>
                <h2 className="text-lg font-semibold text-slate-900 dark:text-white">{title}</h2>
              </div>
              <p className="text-sm leading-7 text-slate-600 dark:text-slate-300">{body}</p>
            </section>
          ))}
        </div>

        <section className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-5 dark:border-amber-900/70 dark:bg-amber-950/30">
          <h2 className="mb-2 text-sm font-semibold text-amber-900 dark:text-amber-100">
            No replacement for official documentation
          </h2>
          <p className="text-sm leading-7 text-amber-900/80 dark:text-amber-100/80">
            Rovr is built for learning and exploration. The official Adobe documentation remains the
            authoritative source for product behavior, configuration, limits, and supportable guidance.
          </p>
        </section>
      </div>
    </main>
  )
}
