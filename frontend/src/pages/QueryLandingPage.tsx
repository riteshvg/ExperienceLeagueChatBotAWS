import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowRight, MessageCircleQuestion } from 'lucide-react';
import { ChatMessage } from '@/components/ChatMessage';
import { getLandingBySlug, type LandingBySlug, type Message } from '@/lib/api';

type Status = 'loading' | 'found' | 'not_found';

function toMessages(data: LandingBySlug): Message[] {
  return [
    { id: 'landing-query', role: 'user', content: data.query },
    {
      id: 'landing-answer',
      role: 'assistant',
      content: data.answer,
      citations: data.citations,
      evidence: data.evidence ?? undefined,
      model: 'landing',
      streaming: false,
    },
  ];
}

export function QueryLandingPage() {
  const { slug = '' } = useParams();
  const [status, setStatus] = useState<Status>('loading');
  const [data, setData] = useState<LandingBySlug | null>(null);

  useEffect(() => {
    let cancelled = false;
    setStatus('loading');
    getLandingBySlug(slug).then((result) => {
      if (cancelled) return;
      setData(result);
      setStatus(result ? 'found' : 'not_found');
    });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  useEffect(() => {
    document.title = data ? `${data.query.slice(0, 60)} — Rovr` : 'Rovr';
    return () => {
      document.title = 'Rovr';
    };
  }, [data]);

  return (
    <main className="flex min-h-screen w-full flex-col bg-slate-50 dark:bg-slate-950">
      <header className="flex flex-shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900">
        <img
          src={`${import.meta.env.BASE_URL}rovrlogo.png`}
          alt="Rovr"
          className="h-8 w-auto"
        />
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-600 no-underline transition-colors hover:border-emerald-300 hover:text-[#14532D] dark:border-slate-700 dark:text-slate-300 dark:hover:border-emerald-700 dark:hover:text-emerald-300"
        >
          Open Rovr
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </header>

      <div className="mx-auto w-full max-w-4xl flex-1 px-4 py-4">
        <p className="mb-6 text-sm leading-relaxed text-slate-500 dark:text-slate-400">
          Rovr is an AI assistant for exploring Adobe Experience League
          documentation — ask a question, get a grounded answer with sources,
          and jump to the official docs when you need more detail. It's an
          independent learning project, not affiliated with Adobe. For more
          details, you can reach out to the developer at ritesh [at]
          thelearningproject.in
        </p>

        {status === 'loading' && (
          <p className="text-sm text-slate-500 dark:text-slate-400">Loading…</p>
        )}

        {status === 'not_found' && (
          <div className="flex flex-col items-center gap-4 py-16 text-center">
            <MessageCircleQuestion className="h-10 w-10 text-slate-400" />
            <h1 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
              This question isn't available
            </h1>
            <p className="max-w-sm text-sm text-slate-500 dark:text-slate-400">
              It may have been removed, or the link is incorrect.
            </p>
            <Link
              to="/"
              className="mt-2 inline-flex items-center gap-2 rounded-lg bg-[#14532D] px-4 py-2 text-sm font-medium text-white no-underline transition-colors hover:bg-[#10B981]"
            >
              Ask Rovr a question
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        )}

        {status === 'found' && data && (
          <div className="flex flex-col gap-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700 dark:text-emerald-300">
              Answered by Rovr
            </p>

            <div className="space-y-4">
              {toMessages(data).map((message) => (
                <ChatMessage
                  key={message.id}
                  message={message}
                  onFollowUpClick={() => {}}
                  hideFeedback
                />
              ))}
            </div>

            <p className="text-xs text-slate-400 dark:text-slate-500">
              AI-generated — grounded in Adobe Experience League documentation.
              Please validate answers before sharing or acting on them.
            </p>

            <Link
              to="/"
              className="inline-flex w-fit items-center gap-2 rounded-lg bg-[#14532D] px-4 py-2 text-sm font-medium text-white no-underline transition-colors hover:bg-[#10B981]"
            >
              Continue in Rovr
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        )}
      </div>
    </main>
  );
}
