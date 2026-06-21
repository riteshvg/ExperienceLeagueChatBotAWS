import { useEffect, useRef, useState } from 'react';
import { Menu, Ban, Clock, WifiOff, CalendarX } from 'lucide-react';
import { useChatStore } from '@/store/chatStore';
import { useAuthStore } from '@/store/authStore';
import { useQuotaStore } from '@/store/quotaStore';
import { useInterviewerStore } from '@/store/interviewerStore';
import { ChatInput, type ChatInputHandle } from '@/components/ChatInput';
import { ChatMessage } from '@/components/ChatMessage';
import { InterviewWorkspace } from '@/components/InterviewWorkspace';
import { InterviewerModeChip } from '@/components/InterviewerModeChip';
import { InterviewSetupModal } from '@/components/InterviewSetupModal';
import { Sidebar } from '@/components/Sidebar';
import { LandingPanel } from '@/components/LandingPanel';
import { getMe, fetchMaintenanceStatus, isApiDisabled } from '@/lib/api';
import { cn } from '@/lib/utils';
import { trackSessionStart, trackSessionEnd } from '@/analytics';

const WELCOME_KEY = 'rovr_welcome_dismissed';

export function ChatPage() {
  const {
    sessions,
    activeSessionId,
    isStreaming,
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
  } = useChatStore();
  const { logout } = useAuthStore();
  const {
    active: interviewerActive,
    featureAvailable: interviewerAvailable,
    adminOnly: interviewerAdminOnly,
    profiles: interviewerProfiles,
    isStreaming: interviewerStreaming,
    error: interviewerError,
    setupOpen: interviewerSetupOpen,
    completed: interviewerCompleted,
    profileLabel: interviewerProfileLabel,
    phase: interviewerPhase,
    questionIndex: interviewerQuestionIndex,
    totalQuestions: interviewerTotalQuestions,
    init: initInterviewer,
    toggle: toggleInterviewer,
    closeSetup: closeInterviewerSetup,
    startSession: startInterviewerSession,
  } = useInterviewerStore();
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
  const [welcomeDismissed, setWelcomeDismissed] = useState(
    () => !!localStorage.getItem(WELCOME_KEY),
  );
  const messages = sessions[activeSessionId]?.messages ?? [];
  const isLanding = messages.length === 0 && !interviewerActive;
  const displayStreaming = interviewerActive ? interviewerStreaming : isStreaming;

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
    initInterviewer();
    return () => clearInterval(interval);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Re-fetch quota after each message completes
  useEffect(() => {
    if (!isStreaming && messages.length > 0) fetchQuota();
  }, [isStreaming]); // eslint-disable-line react-hooks/exhaustive-deps

  // Analytics: fire session_start on page load for fresh sessions
  useEffect(() => {
    if (messages.length === 0) {
      trackSessionStart('page_load');
    }
    // Register beforeunload to track session_end when the tab closes
    const handleUnload = () => {
      const totalTurns = messages.filter((m) => m.role === 'user').length;
      trackSessionEnd(totalTurns);
    };
    window.addEventListener('beforeunload', handleUnload);
    return () => window.removeEventListener('beforeunload', handleUnload);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: displayStreaming ? 'auto' : 'smooth',
      block: 'end',
    });
  }, [messages, displayStreaming]);

  useEffect(() => {
    if (!displayStreaming && messages.length > 0) {
      inputRef.current?.focus();
    }
  }, [displayStreaming, messages.length]);

  const handleSelectPrompt = (text: string) => {
    inputRef.current?.fill(text);
  };

  const handleSend = (text: string) => {
    sendMessage(text);
  };

  const dismissWelcome = () => {
    localStorage.setItem(WELCOME_KEY, 'true');
    setWelcomeDismissed(true);
  };

  if (accessDenied) {
    return (
      <div className="flex w-full h-screen items-center justify-center bg-slate-50 p-6">
        <div className="flex flex-col items-center gap-4 max-w-sm text-center">
          <div className="w-14 h-14 rounded-full bg-red-100 flex items-center justify-center">
            <Ban className="w-7 h-7 text-red-500" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-800 mb-1">
              Account Disabled
            </h2>
            <p className="text-sm text-slate-500">
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
      <div className="flex w-full h-screen items-center justify-center bg-slate-50 p-6">
        <div className="flex flex-col items-center gap-4 max-w-sm text-center">
          <div className="w-14 h-14 rounded-full bg-amber-100 flex items-center justify-center">
            <Clock className="w-7 h-7 text-amber-500" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-800 mb-1">
              Daily Limit Reached
            </h2>
            <p className="text-sm text-slate-500">
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
        onSelectPrompt={handleSelectPrompt}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <main className="flex-1 flex flex-col min-w-0 bg-slate-50">
        {/* Header */}
        <header className="flex-shrink-0 h-12 bg-white border-b border-slate-200 flex items-center justify-between px-4">
          {/* Hamburger — mobile only */}
          <button
            onClick={() => setSidebarOpen(true)}
            className="md:hidden p-1.5 rounded-lg text-slate-500 hover:bg-slate-100 mr-2"
          >
            <Menu className="w-4 h-4" />
          </button>
          <h1 className="text-sm font-semibold text-slate-700">Rovr</h1>
          <InterviewerModeChip
            active={interviewerActive}
            available={interviewerAvailable}
            adminOnly={interviewerAdminOnly}
            onClick={toggleInterviewer}
          />
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {/* Kill switch banner */}
          {apiDisabled && (
            <div className="flex items-start gap-3 px-4 py-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-800">
              <WifiOff className="w-4 h-4 flex-shrink-0 mt-0.5 text-amber-600" />
              <p className="text-sm">
                Rovr is temporarily unavailable. The administrator has disabled
                the API. Please check back shortly.
              </p>
            </div>
          )}

          {/* Monthly quota exhausted banner */}
          {(isExhausted || monthlyExhausted) && !apiDisabled && (
            <div className="flex items-start gap-3 px-4 py-3 rounded-xl bg-blue-50 border border-blue-200 text-blue-800">
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

          {interviewerActive && interviewerProfileLabel && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-sm">
              <span className="font-medium">Interview prep</span>
              <span className="text-emerald-700/80">· {interviewerProfileLabel}</span>
              {interviewerTotalQuestions > 0 && (
                <span className="text-xs text-emerald-700/70 ml-auto">
              {interviewerPhase === 'review'
                ? 'Review'
                : interviewerCompleted
                  ? 'Complete'
                  : `Q${Math.min(interviewerQuestionIndex + 1, interviewerTotalQuestions)} / ${interviewerTotalQuestions}`}
                </span>
              )}
            </div>
          )}

          {!interviewerActive && isLanding && (
            <LandingPanel
              sessionId={activeSessionId}
              onSelectPrompt={handleSelectPrompt}
              isNewUser={isNewUser}
              monthlyRemaining={monthlyRemaining}
              monthlyLimit={monthlyLimit}
              welcomeDismissed={welcomeDismissed}
              onDismissWelcome={dismissWelcome}
            />
          )}

          {interviewerActive && !interviewerSetupOpen && (
            <InterviewWorkspace />
          )}

          {!interviewerActive && (() => {
            let userTurn = 0;
            return messages.map((msg) => {
              if (msg.role === 'user') userTurn++;
              const turn = userTurn;
              return (
                <ChatMessage
                  key={msg.id}
                  message={msg}
                  onFollowUpClick={handleSelectPrompt}
                  turnNumber={turn}
                />
              );
            });
          })()}

          {(error || interviewerError) && (
            <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2">
              {interviewerError ?? error}
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input — hidden during interview prep (Q&A workspace has its own editor) */}
        <div className="flex-shrink-0 px-4 py-3 bg-slate-50 border-t border-slate-200">
          {knowledgeBankUpdating && !apiDisabled && (
            <div
              role="status"
              className="flex items-start gap-3 px-4 py-3 mb-3 rounded-xl bg-violet-50 border border-violet-200 text-violet-900"
            >
              <Clock className="w-4 h-4 shrink-0 mt-0.5 text-violet-600" />
              <p className="text-sm leading-relaxed">
                {knowledgeBankMessage ??
                  'The application knowledge bank is being updated. Please check back shortly.'}
              </p>
            </div>
          )}
          {!interviewerActive && (
            <ChatInput
              ref={inputRef}
              onSend={handleSend}
              disabled={
                displayStreaming ||
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
          )}
          {interviewerActive && interviewerCompleted && (
            <p className="text-center text-sm text-slate-500 py-1">
              Session complete — toggle off Interview prep to return to Rovr chat.
            </p>
          )}
          <p className="mt-2 text-center text-xs text-slate-400">
            <span>Answers are grounded in Adobe Experience League documentation</span>
            <span aria-hidden="true"> · </span>
            <span>AI-generated — please validate answers before sharing or acting on them</span>
            {monthlyLimit < 9999 ? (
              <>
                <span aria-hidden="true"> · </span>
                <span
                  className={cn(
                    isExhausted || monthlyExhausted
                      ? 'text-red-500 font-medium'
                      : monthlyRemaining <= 5
                        ? 'text-amber-500'
                        : undefined,
                  )}
                >
                  {isExhausted || monthlyExhausted ? monthlyLimit : monthlyUsed} / {monthlyLimit} queries
                  used this month · {isExhausted || monthlyExhausted ? 0 : monthlyRemaining} remaining
                </span>
              </>
            ) : queriesRemaining !== null ? (
              <>
                <span aria-hidden="true"> · </span>
                <span
                  className={cn(
                    queriesRemaining === 0
                      ? 'text-red-500 font-medium'
                      : queriesRemaining <= queriesLimit * 0.25
                        ? 'text-amber-500'
                        : undefined,
                  )}
                >
                  {queriesUsed} / {queriesLimit} queries used this month · {queriesRemaining} remaining
                </span>
              </>
            ) : null}
          </p>
        </div>
      </main>

      <InterviewSetupModal
        open={interviewerSetupOpen}
        profiles={interviewerProfiles}
        onClose={closeInterviewerSetup}
        onStart={startInterviewerSession}
        loading={interviewerStreaming}
      />

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
