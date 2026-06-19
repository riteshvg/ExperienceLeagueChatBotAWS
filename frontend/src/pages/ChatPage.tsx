import { useEffect, useRef, useState, useCallback } from 'react';
import { Menu, Ban, Clock, WifiOff, CalendarX } from 'lucide-react';
import { useChatStore } from '@/store/chatStore';
import { useAuthStore } from '@/store/authStore';
import { useQuotaStore } from '@/store/quotaStore';
import { useEducatorStore } from '@/store/educatorStore';
import { ChatInput, type ChatInputHandle } from '@/components/ChatInput';
import { ChatMessage } from '@/components/ChatMessage';
import { Sidebar } from '@/components/Sidebar';
import { EducatorModeChip } from '@/components/EducatorModeChip';
import { ExamSelectorModal } from '@/components/ExamSelectorModal';
import { ScoreReport } from '@/components/ScoreReport';
import { getMe, fetchMaintenanceStatus, isApiDisabled } from '@/lib/api';
import { cn } from '@/lib/utils';
import { parseQuestionFromMessage } from '@/lib/educator-parse';
import { trackSessionStart, trackSessionEnd } from '@/analytics';

const WELCOME_KEY = 'rovr_welcome_dismissed';

type Category =
  | 'All'
  | 'Analytics'
  | 'CJA'
  | 'AEP'
  | 'Target'
  | 'AJO'
  | 'Cross-Product';

const QUESTION_BANK: Record<Exclude<Category, 'All'>, string[]> = {
  Analytics: [
    'How do I create a segment in Adobe Analytics?',
    'What is the difference between eVars and props in Adobe Analytics?',
    'How do I set up processing rules in Adobe Analytics?',
    'How do I configure marketing channel rules in Adobe Analytics?',
  ],
  CJA: [
    'What is a Data View in Customer Journey Analytics?',
    'How do I create a calculated metric in CJA?',
    'What is the difference between Adobe Analytics and Customer Journey Analytics?',
    'How does stitching work in Customer Journey Analytics?',
  ],
  AEP: [
    'What are the different ways to ingest data into Adobe Experience Platform?',
    'How do I create an XDM schema in Adobe Experience Platform?',
    'What is Real-Time CDP and how does it work with AEP profiles?',
    'How do I set up identity resolution in Adobe Experience Platform?',
  ],
  Target: [
    'How do I create an A/B test in Adobe Target?',
    'What is the difference between A/B testing and multivariate testing in Target?',
    'How do I set up Experience Targeting activities in Adobe Target?',
    'How do I use Recommendations in Adobe Target?',
  ],
  AJO: [
    'What is Adobe Journey Optimizer and how does it differ from Adobe Campaign?',
    'How do I create a journey in Adobe Journey Optimizer?',
    'What is decision management in Adobe Journey Optimizer?',
    'How do I set up frequency capping rules in Adobe Journey Optimizer?',
  ],
  'Cross-Product': [
    'How do I use AEP audiences in Adobe Target for personalisation?',
    'How does data flow from Adobe Analytics to Customer Journey Analytics?',
    'How do I connect an Adobe Analytics report suite to CJA?',
    'What is the difference between Adobe Analytics and Real-Time CDP for audience building?',
    'How do server-side forwarding and the Experience Platform Web SDK compare for sending data to AEP?',
  ],
};

const CATEGORIES: Category[] = [
  'All',
  'Analytics',
  'CJA',
  'AEP',
  'Target',
  'AJO',
  'Cross-Product',
];

const CATEGORY_COLORS: Record<Exclude<Category, 'All'>, string> = {
  Analytics: 'bg-orange-50 text-orange-700 border-orange-200',
  CJA: 'bg-violet-50 text-violet-700 border-violet-200',
  AEP: 'bg-blue-50 text-blue-700 border-blue-200',
  Target: 'bg-red-50 text-red-700 border-red-200',
  AJO: 'bg-green-50 text-green-700 border-green-200',
  'Cross-Product': 'bg-teal-50 text-teal-700 border-teal-200',
};

export function ChatPage() {
  const {
    sessions,
    activeSessionId,
    isStreaming,
    sendMessage: sendStandardMessage,
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
    monthlyLimit,
    monthlyUsed,
    monthlyRemaining,
    resetDate,
    isNewUser,
    isExhausted,
    fetchQuota,
  } = useQuotaStore();
  const {
    mode: rovrMode,
    featureAvailable,
    exams,
    exam,
    init: initEducator,
    startExam,
    exitEducatorMode,
    sendMessage: sendEducatorMessage,
    submitAnswer,
    requestHint,
    requestDoc,
    skipQuestion,
    deepen,
    getQuestionForMessage,
    isStreaming: educatorStreaming,
    scoreReport,
    showScorePanel,
    dismissScorePanel,
    getStartupMessage,
  } = useEducatorStore();

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [examModalOpen, setExamModalOpen] = useState(false);
  const [activeCategory, setActiveCategory] = useState<Category>('All');
  const [welcomeDismissed, setWelcomeDismissed] = useState(
    () => !!localStorage.getItem(WELCOME_KEY),
  );
  const messages = sessions[activeSessionId]?.messages ?? [];
  const streaming = isStreaming || educatorStreaming;
  const showEducatorChip = featureAvailable;

  const patchMessages = useCallback(
    (updater: (msgs: typeof messages) => typeof messages) => {
      useChatStore.setState((s) => {
        const session = s.sessions[s.activeSessionId];
        if (!session) return s;
        const updated = updater(session.messages);
        const title =
          updated.find((m) => m.role === 'user')?.content.slice(0, 45) ?? 'New chat';
        return {
          ...s,
          sessions: {
            ...s.sessions,
            [s.activeSessionId]: {
              ...session,
              messages: updated,
              title: title + (title.length >= 45 ? '…' : ''),
            },
          },
        };
      });
    },
    [],
  );

  const getMessages = useCallback(
    () => useChatStore.getState().sessions[activeSessionId]?.messages ?? [],
    [activeSessionId],
  );

  const handleSend = useCallback(
    async (query: string) => {
      if (rovrMode === 'educator') {
        await sendEducatorMessage(query, activeSessionId, patchMessages, getMessages);
      } else {
        await sendStandardMessage(query);
      }
    },
    [rovrMode, sendEducatorMessage, sendStandardMessage, activeSessionId, patchMessages, getMessages],
  );

  const handleEducatorAnswer = useCallback(
    async (answer: string) => {
      await submitAnswer(`I choose ${answer}`, activeSessionId, patchMessages, getMessages);
    },
    [submitAnswer, activeSessionId, patchMessages, getMessages],
  );

  const educatorActions = useCallback(
    () => ({ chatSessionId: activeSessionId, patch: patchMessages, getMsgs: getMessages }),
    [activeSessionId, patchMessages, getMessages],
  );

  const handleModeChange = useCallback(
    (mode: 'standard' | 'educator') => {
      if (mode === 'standard') {
        exitEducatorMode();
        return;
      }
      setExamModalOpen(true);
    },
    [exitEducatorMode],
  );

  const handleExamSelected = useCallback(
    async (examId: string) => {
      setExamModalOpen(false);
      await startExam(examId);
      const startup = getStartupMessage();
      await submitAnswer(startup, activeSessionId, patchMessages, getMessages);
    },
    [startExam, getStartupMessage, submitAnswer, activeSessionId, patchMessages, getMessages],
  );

  const visibleQuestions =
    activeCategory === 'All'
      ? Object.entries(QUESTION_BANK).flatMap(([cat, qs]) =>
          qs
            .slice(0, 1)
            .map((q) => ({ q, cat: cat as Exclude<Category, 'All'> })),
        )
      : QUESTION_BANK[activeCategory].map((q) => ({
          q,
          cat: activeCategory as Exclude<Category, 'All'>,
        }));

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

    initEducator().then(() => {
      const params = new URLSearchParams(window.location.search);
      const examParam = params.get('exam');
      if (params.get('mode') === 'educator' && examParam) {
        handleExamSelected(examParam);
      }
    });

    return () => clearInterval(interval);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Re-fetch quota after each message completes
  useEffect(() => {
    if (!streaming && messages.length > 0) fetchQuota();
  }, [streaming]); // eslint-disable-line react-hooks/exhaustive-deps

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
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (!streaming && messages.length > 0) {
      inputRef.current?.focus();
    }
  }, [streaming, messages.length]);

  const handleSelectPrompt = (text: string) => {
    inputRef.current?.fill(text);
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
          <div className="flex items-center gap-3 min-w-0">
            <h1 className="text-sm font-semibold text-slate-700">Rovr</h1>
            {rovrMode === 'educator' && exam && (
              <span className="hidden sm:inline text-xs text-violet-600 truncate">
                Educator · {exam.id}
              </span>
            )}
          </div>
          {showEducatorChip && (
            <EducatorModeChip mode={rovrMode} onModeChange={handleModeChange} />
          )}
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

          {messages.length === 0 && rovrMode === 'standard' && (
            <div className="min-h-full flex flex-col items-center justify-center px-4 py-8 md:py-12">
              <img
                src={`${import.meta.env.BASE_URL}rovrlogo.png`}
                alt="Rovr"
                className="h-12 w-auto mb-4"
              />
              <h2 className="text-lg font-semibold text-slate-700 mb-1 text-center">
                Ask about Adobe Experience League docs
              </h2>
              <p className="text-sm text-slate-400 max-w-md text-center mb-5">
                Analytics · CJA · Experience Platform · Target · Adobe Journey
                Optimizer
              </p>

              {/* First-time welcome card */}
              {isNewUser &&
                monthlyRemaining > 0 &&
                !welcomeDismissed &&
                monthlyLimit < 9999 && (
                  <div className="w-full max-w-md mb-5 px-5 py-4 rounded-xl bg-emerald-50 border border-emerald-200 text-left">
                    <h3 className="text-sm font-semibold text-emerald-800 mb-1">
                      Welcome to Rovr
                    </h3>
                    <p className="text-xs text-emerald-700 leading-relaxed">
                      You have {monthlyLimit} free queries this month to explore
                      Adobe Experience Cloud documentation. Your quota resets on
                      the 1st of each month. An administrator can adjust your
                      limit if you need more.
                    </p>
                    <button
                      onClick={() => {
                        localStorage.setItem(WELCOME_KEY, 'true');
                        setWelcomeDismissed(true);
                      }}
                      className="mt-3 px-3 py-1.5 rounded-lg bg-[#14532D] text-white text-xs font-medium hover:bg-[#10B981] transition-colors"
                    >
                      Got it
                    </button>
                  </div>
                )}

              {/* Category filter chips */}
              <div className="flex flex-wrap justify-center gap-1.5 mb-4 max-w-lg">
                {CATEGORIES.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setActiveCategory(cat)}
                    className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                      activeCategory === cat
                        ? 'bg-[#10B981] text-white border-[#10B981]'
                        : 'bg-white text-slate-500 border-slate-200 hover:border-[#10B981] hover:text-[#10B981]'
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>

              {/* Question cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-2xl">
                {visibleQuestions.map(({ q, cat }) => (
                  <button
                    key={q}
                    onClick={() => handleSend(q)}
                    className="group text-left px-4 py-3 rounded-xl border border-slate-200 bg-white
                      hover:border-indigo-300 hover:shadow-sm transition-all"
                  >
                    <span
                      className={`inline-block text-[10px] font-semibold px-1.5 py-0.5 rounded border mb-1.5 ${CATEGORY_COLORS[cat]}`}
                    >
                      {cat}
                    </span>
                    <p className="text-sm text-slate-600 group-hover:text-[#14532D] leading-snug">
                      {q}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.length === 0 && rovrMode === 'educator' && exam && (
            <div className="min-h-full flex flex-col items-center justify-center px-4 py-8 text-center">
              <p className="text-sm text-violet-700 font-medium mb-1">
                Educator mode · {exam.name}
              </p>
              <p className="text-xs text-slate-500 max-w-md">
                Your guide, not an examiner. Use hint or doc buttons before answering.
                Commands: /hint · /doc · /skip · /score · /revisit · /quit
              </p>
            </div>
          )}

          {(() => {
            let userTurn = 0;
            return messages.map((msg) => {
              if (msg.role === 'user') userTurn++;
              const turn = userTurn;
              const qRecord = getQuestionForMessage(msg.id);
              const hasQuestion =
                rovrMode === 'educator' &&
                msg.role === 'assistant' &&
                !msg.streaming &&
                !!parseQuestionFromMessage(msg.content);
              const { chatSessionId, patch, getMsgs } = educatorActions();
              return (
                <ChatMessage
                  key={msg.id}
                  message={msg}
                  onFollowUpClick={handleSelectPrompt}
                  turnNumber={turn}
                  educatorActive={rovrMode === 'educator'}
                  educatorDisabled={streaming}
                  questionRecord={qRecord}
                  onEducatorAnswer={hasQuestion ? handleEducatorAnswer : undefined}
                  onEducatorHint={
                    hasQuestion
                      ? () => requestHint(chatSessionId, patch, getMsgs)
                      : undefined
                  }
                  onEducatorDoc={
                    hasQuestion ? () => requestDoc(chatSessionId, patch, getMsgs) : undefined
                  }
                  onEducatorSkip={
                    hasQuestion
                      ? () => skipQuestion(chatSessionId, patch, getMsgs)
                      : undefined
                  }
                  onEducatorDeepen={(action) => deepen(action, chatSessionId, patch, getMsgs)}
                />
              );
            });
          })()}

          {error && (
            <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2">
              {error}
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
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
          <ChatInput
            ref={inputRef}
            onSend={handleSend}
            disabled={
              streaming ||
              apiDisabled ||
              knowledgeBankUpdating ||
              isExhausted ||
              monthlyExhausted
            }
            placeholder={
              rovrMode === 'educator'
                ? 'Answer or use /hint · /doc · /skip · /score · /revisit · /quit'
                : knowledgeBankUpdating
                  ? 'Knowledge bank is updating — please check back shortly…'
                  : undefined
            }
          />
          <div className="mt-2 flex flex-col items-center gap-0.5">
            <p className="text-center text-xs text-slate-400">
              Answers are grounded in Adobe Experience League documentation
            </p>
            <p className="text-center text-xs text-slate-400">
              AI-generated — please validate answers before sharing or acting on them
            </p>
            {monthlyLimit < 9999 ? (
              <p
                className={cn(
                  'text-xs mt-0.5',
                  isExhausted || monthlyExhausted
                    ? 'text-red-500 font-medium'
                    : monthlyRemaining <= 5
                      ? 'text-amber-500'
                      : 'text-slate-400',
                )}
              >
                {isExhausted || monthlyExhausted ? monthlyLimit : monthlyUsed} / {monthlyLimit} queries used this month
                {' '}· {isExhausted || monthlyExhausted ? 0 : monthlyRemaining} remaining
              </p>
            ) : queriesRemaining !== null ? (
              <p
                className={cn(
                  'text-xs mt-0.5',
                  queriesRemaining === 0
                    ? 'text-red-500 font-medium'
                    : queriesRemaining <= queriesLimit * 0.25
                      ? 'text-amber-500'
                      : 'text-slate-400',
                )}
              >
                {queriesUsed} / {queriesLimit} queries used this month
                {' '}· {queriesRemaining} remaining
              </p>
            ) : null}
          </div>
        </div>
      </main>

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

      <ExamSelectorModal
        exams={exams}
        open={examModalOpen}
        onClose={() => setExamModalOpen(false)}
        onSelect={handleExamSelected}
      />

      {showScorePanel && scoreReport && (
        <ScoreReport
          report={scoreReport}
          examName={exam?.name}
          onClose={dismissScorePanel}
          onRevisit={(prompt) => handleSend(prompt)}
        />
      )}
    </div>
  );
}
