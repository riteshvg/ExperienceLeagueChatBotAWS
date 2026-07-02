import { useEffect, useRef, useState } from 'react';
import { CalendarX, ChevronDown, Clock, LogOut, Menu, Ban, Plus, WifiOff } from 'lucide-react';
import { ThemeToggle } from '@/components/ThemeToggle';
import { useChatStore } from '@/store/chatStore';
import { useAuthStore } from '@/store/authStore';
import { useQuotaStore } from '@/store/quotaStore';
import { ChatInput, type ChatInputHandle } from '@/components/ChatInput';
import { ChatMessage } from '@/components/ChatMessage';
import { StatusIndicator } from '@/components/StatusIndicator';
import { Sidebar } from '@/components/Sidebar';
import { LandingPanel } from '@/components/LandingPanel';
import { getMe, fetchMaintenanceStatus, isApiDisabled } from '@/lib/api';
import { cn } from '@/lib/utils';
import { PRODUCT_PILL_STYLES, type TickerQuestion } from '@/config/questions';
import {
  hasAnalyticsSession,
  trackQuestionAsked,
  trackQuerySent,
  trackSessionEnd,
  trackSessionStart,
  trackSuggestedPromptClick,
} from '@/analytics';

const WELCOME_KEY = 'rovr_welcome_dismissed';

export function ChatPage() {
  const {
    sessions,
    activeSessionId,
    isStreaming,
    currentStage,
    stageStalled,
    sendMessage,
    error,
    accessDenied,
    rateLimited,
    rateLimitMessage,
    apiDisabled,
    knowledgeBankUpdating,
    knowledgeBankMessage,
    monthlyExhausted,
    queriesUsed,
    queriesRemaining,
    queriesLimit,
    feedbackToast,
    dismissFeedbackToast,
    setUsage,
    setApiDisabled,
    setKnowledgeBankMaintenance,
    startNewChat,
  } = useChatStore();
  const { logout, session } = useAuthStore();
  const {
    monthlyLimit,
    monthlyUsed,
    monthlyRemaining,
    resetDate,
    isNewUser,
    isExhausted,
    fetchQuota,
  } = useQuotaStore();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [userPanelOpen, setUserPanelOpen] = useState(false);
  const [welcomeDismissed, setWelcomeDismissed] = useState(
    () => !!localStorage.getItem(WELCOME_KEY),
  );
  const messages = sessions[activeSessionId]?.messages ?? [];
  const isLanding = messages.length === 0;
  const canStartNewChat = !isStreaming && messages.length > 0;

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<ChatInputHandle>(null);

  useEffect(() => {
    if (!feedbackToast) return
    const t = setTimeout(dismissFeedbackToast, 3000)
    return () => clearTimeout(t)
  }, [feedbackToast, dismissFeedbackToast])

  useEffect(() => {
    getMe().then((usage) =>
      setUsage(
        usage.queries_used,
        usage.queries_remaining,
        usage.queries_limit,
      ),
    );
    fetchQuota();
    isApiDisabled().then((disabled) => {
      if (disabled) setApiDisabled(true);
    });

    const pollHealth = async () => {
      const status = await fetchMaintenanceStatus();
      setKnowledgeBankMaintenance(
        status.updating,
        status.message,
        status.checkBackAt,
      );
    };

    pollHealth();
    const interval = setInterval(pollHealth, 10_000);
    return () => clearInterval(interval);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Re-fetch quota after each message completes
  useEffect(() => {
    if (!isStreaming && messages.length > 0) fetchQuota();
  }, [isStreaming]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (messages.some((m) => m.role === 'user') && !hasAnalyticsSession()) {
      trackSessionStart('resume_chat');
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Analytics: best-effort session_end when the tab closes.
  useEffect(() => {
    const handlePageHide = () => {
      const state = useChatStore.getState();
      const currentMessages = state.sessions[state.activeSessionId]?.messages ?? [];
      const totalTurns = currentMessages.filter((m) => m.role === 'user').length;
      if (totalTurns === 0) return;
      trackSessionEnd(totalTurns);
    };
    window.addEventListener('pagehide', handlePageHide);
    return () => window.removeEventListener('pagehide', handlePageHide);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: isStreaming ? 'auto' : 'smooth',
      block: 'end',
    });
  }, [messages, isStreaming]);

  useEffect(() => {
    if (!isStreaming && messages.length > 0) {
      inputRef.current?.focus();
    }
  }, [isStreaming, messages.length]);

  useEffect(() => {
    if (!userPanelOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setUserPanelOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [userPanelOpen]);

  type PromptSource = 'center_popular_questions' | 'sidebar_prompt_library' | 'followup_question';

  const handleSelectPrompt = (text: string, promptSource?: PromptSource) => {
    inputRef.current?.fill(text, promptSource);
  };

  const handleSidebarPromptSelect = (
    text: string,
    meta?: { title?: string; category?: string },
  ) => {
    trackSuggestedPromptClick({
      promptText: text,
      promptSource: 'sidebar_prompt_library',
      promptTitle: meta?.title,
      promptCategory: meta?.category,
    });
    handleSelectPrompt(text, 'sidebar_prompt_library');
  };

  const handlePopularQuestionSelect = (question: TickerQuestion) => {
    trackSuggestedPromptClick({
      promptText: question.text,
      promptSource: 'center_popular_questions',
      promptCategory: PRODUCT_PILL_STYLES[question.product].label,
      timesAsked: question.asked,
    });
    handleSelectPrompt(question.text, 'center_popular_questions');
  };

  const handleFollowUpPromptSelect = (text: string) => {
    trackSuggestedPromptClick({
      promptText: text,
      promptSource: 'followup_question',
    });
    handleSelectPrompt(text, 'followup_question');
  };

  const getNextTurnNumber = () =>
    messages.filter((m) => m.role === 'user').length + 1;

  const ensureChatSessionStarted = () => {
    if (!hasAnalyticsSession()) trackSessionStart('first_query');
  };

  const handleQuestionAsked = (query: string, promptSource?: PromptSource) => {
    ensureChatSessionStarted();
    trackQuestionAsked(query, getNextTurnNumber(), 'uncategorised', promptSource);
  };

  const handleSubmitQuery = (query: string, promptSource?: PromptSource) => {
    ensureChatSessionStarted();
    trackQuerySent(query, getNextTurnNumber(), 'unknown', 'uncategorised', promptSource);
  };

  const dismissWelcome = () => {
    localStorage.setItem(WELCOME_KEY, 'true');
    setWelcomeDismissed(true);
  };

  const handleLogout = async () => {
    setUserPanelOpen(false);
    await logout();
  };

  if (accessDenied) {
    return (
      <div className="flex w-full h-screen items-center justify-center bg-slate-50 dark:bg-slate-950 p-6">
        <div className="flex flex-col items-center gap-4 max-w-sm text-center">
          <div className="w-14 h-14 rounded-full bg-red-100 dark:bg-red-950/50 flex items-center justify-center">
            <Ban className="w-7 h-7 text-red-500" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-1">
              Account Disabled
            </h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Your access to Rovr has been disabled. If you believe this is an
              error, please contact the administrator.
            </p>
          </div>
          <button
            onClick={() => logout()}
            className="mt-2 px-5 py-2 rounded-lg bg-slate-800 text-white text-sm font-medium hover:bg-slate-900 transition-colors"
          >
            Sign out
          </button>
        </div>
      </div>
    );
  }

  if (rateLimited) {
    return (
      <div className="flex w-full h-screen items-center justify-center bg-slate-50 dark:bg-slate-950 p-6">
        <div className="flex flex-col items-center gap-4 max-w-sm text-center">
          <div className="w-14 h-14 rounded-full bg-amber-100 dark:bg-amber-950/50 flex items-center justify-center">
            <Clock className="w-7 h-7 text-amber-500" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-1">
              Daily Limit Reached
            </h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {rateLimitMessage ||
                'Your daily query limit has been reached. Resets at midnight UTC.'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex w-full h-screen overflow-hidden">
      <Sidebar
        onSelectPrompt={handleSidebarPromptSelect}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <main className="flex-1 flex flex-col min-w-0 bg-slate-50 dark:bg-slate-950">
        {/* Header */}
        <header className="flex-shrink-0 h-12 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-4">
          {/* Hamburger — mobile only */}
          <button
            onClick={() => setSidebarOpen(true)}
            className="md:hidden p-1.5 rounded-lg text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 mr-2"
          >
            <Menu className="w-4 h-4" />
          </button>
          <h1 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Rovr</h1>
          <div className="relative ml-auto">
            <button
              type="button"
              onClick={() => setUserPanelOpen((open) => !open)}
              className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-sm text-slate-700 transition-colors hover:border-emerald-300 hover:text-[#14532D] dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:border-emerald-700 dark:hover:text-emerald-300"
              aria-expanded={userPanelOpen}
              aria-haspopup="menu"
            >
              {session?.picture ? (
                <img
                  src={session.picture}
                  alt={session.name || session.email}
                  className="h-6 w-6 rounded-full"
                  referrerPolicy="no-referrer"
                />
              ) : (
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100 text-xs font-semibold text-[#14532D] dark:bg-emerald-950 dark:text-emerald-300">
                  {(session?.name || session?.email || 'U').charAt(0).toUpperCase()}
                </span>
              )}
              <span className="hidden max-w-36 truncate sm:inline">{session?.name || session?.email || 'Account'}</span>
              <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
            </button>

            {userPanelOpen && (
              <div
                role="menu"
                className="absolute right-0 top-full z-40 mt-2 w-72 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg dark:border-slate-700 dark:bg-slate-900"
              >
                <div className="border-b border-slate-100 px-4 py-3 dark:border-slate-800">
                  <p className="truncate text-sm font-semibold text-slate-800 dark:text-slate-100">
                    {session?.name || 'Rovr user'}
                  </p>
                  <p className="truncate text-xs text-slate-500 dark:text-slate-400">{session?.email}</p>
                </div>

                {monthlyLimit < 9999 ? (
                  <div className="border-b border-slate-100 px-4 py-3 dark:border-slate-800">
                    <div className="mb-1 flex items-center justify-between text-xs">
                      <span className="font-medium text-slate-600 dark:text-slate-300">Questions remaining</span>
                      <span
                        className={cn(
                          'font-semibold',
                          isExhausted || monthlyExhausted
                            ? 'text-red-500'
                            : monthlyRemaining <= 5
                              ? 'text-amber-500'
                              : 'text-emerald-600 dark:text-emerald-400',
                        )}
                      >
                        {isExhausted || monthlyExhausted ? 0 : monthlyRemaining}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {monthlyUsed} of {monthlyLimit} used this month
                    </p>
                  </div>
                ) : queriesRemaining !== null ? (
                  <div className="border-b border-slate-100 px-4 py-3 dark:border-slate-800">
                    <div className="mb-1 flex items-center justify-between text-xs">
                      <span className="font-medium text-slate-600 dark:text-slate-300">Questions remaining</span>
                      <span
                        className={cn(
                          'font-semibold',
                          queriesRemaining === 0
                            ? 'text-red-500'
                            : queriesRemaining <= queriesLimit * 0.25
                              ? 'text-amber-500'
                              : 'text-emerald-600 dark:text-emerald-400',
                        )}
                      >
                        {queriesRemaining}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {queriesUsed} of {queriesLimit} used this month
                    </p>
                  </div>
                ) : null}

                <div className="p-2">
                  <ThemeToggle
                    showLabel
                    className="w-full justify-start px-2.5 py-2 text-sm"
                  />
                  <button
                    type="button"
                    onClick={handleLogout}
                    className="mt-1 flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm text-slate-600 transition-colors hover:bg-red-50 hover:text-red-600 dark:text-slate-300 dark:hover:bg-red-950/30 dark:hover:text-red-300"
                  >
                    <LogOut className="h-4 w-4" />
                    Sign out
                  </button>
                </div>
              </div>
            )}
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {/* Kill switch banner */}
          {apiDisabled && (
            <div className="flex items-start gap-3 px-4 py-3 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900 text-amber-800 dark:text-amber-200">
              <WifiOff className="w-4 h-4 flex-shrink-0 mt-0.5 text-amber-600" />
              <p className="text-sm">
                Rovr is temporarily unavailable. The administrator has disabled
                the API. Please check back shortly.
              </p>
            </div>
          )}

          {/* Monthly quota exhausted banner */}
          {(isExhausted || monthlyExhausted) && !apiDisabled && (
            <div className="flex items-start gap-3 px-4 py-3 rounded-xl bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900 text-blue-800 dark:text-blue-200">
              <CalendarX className="w-4 h-4 flex-shrink-0 mt-0.5 text-blue-600" />
              <p className="text-sm">
                You've used all {monthlyLimit} queries for this month.{' '}
                {resetDate
                  ? `Your quota resets on ${new Date(resetDate + 'T00:00:00Z').toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' })}.`
                  : 'Your quota resets at the start of next month.'}{' '}
                Contact your administrator if you need additional access.
              </p>
            </div>
          )}

          {isLanding && (
            <LandingPanel
              sessionId={activeSessionId}
              onSelectPrompt={handlePopularQuestionSelect}
              isNewUser={isNewUser}
              monthlyRemaining={monthlyRemaining}
              monthlyLimit={monthlyLimit}
              welcomeDismissed={welcomeDismissed}
              onDismissWelcome={dismissWelcome}
            />
          )}

          {(() => {
            let userTurn = 0;
            return messages.map((msg) => {
              if (msg.role === 'user') userTurn++;
              const turn = userTurn;
              // Real-time pipeline status replaces the empty streaming bubble;
              // it steps aside the instant the first token lands (content becomes non-empty)
              // or the turn ends for any reason (streaming flips false).
              if (msg.role === 'assistant' && msg.streaming && !msg.content.trim()) {
                return <StatusIndicator key={msg.id} stage={currentStage} stalled={stageStalled} />;
              }
              return (
                <ChatMessage
                  key={msg.id}
                  message={msg}
                  onFollowUpClick={handleFollowUpPromptSelect}
                  turnNumber={turn}
                />
              );
            });
          })()}

          {error && (
            <div className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 rounded-lg px-4 py-2">
              {error}
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="flex-shrink-0 px-4 py-3 bg-slate-50 dark:bg-slate-950 border-t border-slate-200 dark:border-slate-800">
          {knowledgeBankUpdating && !apiDisabled && (
            <div
              role="status"
              className="flex items-start gap-3 px-4 py-3 mb-3 rounded-xl bg-violet-50 dark:bg-violet-950/40 border border-violet-200 dark:border-violet-900 text-violet-900 dark:text-violet-200"
            >
              <Clock className="w-4 h-4 shrink-0 mt-0.5 text-violet-600" />
              <p className="text-sm leading-relaxed">
                {knowledgeBankMessage ??
                  'The application knowledge bank is being updated. Please check back shortly.'}
              </p>
            </div>
          )}
          <ChatInput
            ref={inputRef}
            onSend={sendMessage}
            onQuestionAsked={handleQuestionAsked}
            onSubmitQuery={handleSubmitQuery}
            disabled={
              isStreaming ||
              apiDisabled ||
              knowledgeBankUpdating ||
              isExhausted ||
              monthlyExhausted
            }
            placeholder={
              knowledgeBankUpdating
                ? 'Knowledge bank is updating — please check back shortly…'
                : isLanding
                  ? 'Or type your own question…'
                  : undefined
            }
          />
          <p className="mt-2 text-center text-xs text-slate-400 dark:text-slate-500">
            <span>Answers are grounded in Adobe Experience League documentation</span>
            <span aria-hidden="true"> · </span>
            <span>AI-generated — please validate answers before sharing or acting on them</span>
          </p>
        </div>
      </main>

      <button
        type="button"
        onClick={startNewChat}
        disabled={!canStartNewChat}
        title="New chat"
        aria-label="New chat"
        className={cn(
          'fixed bottom-28 right-5 z-30 flex h-12 w-12 items-center justify-center rounded-full shadow-lg transition-all md:right-7',
          canStartNewChat
            ? 'bg-[#14532D] text-white hover:bg-[#10B981] hover:shadow-xl'
            : 'cursor-not-allowed bg-slate-200 text-slate-400 opacity-80 shadow-sm dark:bg-slate-800 dark:text-slate-600',
        )}
      >
        <Plus className="h-5 w-5" />
      </button>

      {/* Feedback thank-you toast */}
      <div
        className={cn(
          'fixed bottom-6 left-1/2 -translate-x-1/2 z-50',
          'flex items-center gap-2 px-4 py-2.5 rounded-full',
          'bg-[#14532D] text-white text-sm font-medium shadow-lg',
          'transition-all duration-300',
          feedbackToast ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3 pointer-events-none',
        )}
      >
        <span className="text-base leading-none">👍</span>
        Thank you for your feedback
      </div>
    </div>
  );
}
