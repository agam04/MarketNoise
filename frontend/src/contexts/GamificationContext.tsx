import { createContext, useContext, useReducer, useCallback, useEffect, useState, type ReactNode } from 'react';
import { generateId } from '../utils/constants';

// ─── Types ───────────────────────────────────────────────────────────────────

export interface Mission {
  id: string;
  title: string;
  description: string;
  emoji: string;
  completed: boolean;
  xpReward: number;
}

export interface Badge {
  id: string;
  title: string;
  description: string;
  emoji: string;
  unlocked: boolean;
}

export interface XPToast {
  id: string;
  amount: number;
}

export interface BadgeToast {
  id: string;
  title: string;
  emoji: string;
}

interface GamificationState {
  xp: number;
  toasts: XPToast[];
  missions: Mission[];
  badges: Badge[];
  stocksViewed: string[];
  chatCount: number;
  newsCount: number;
  confetti: boolean;
  badgeToast: BadgeToast | null;
}

type ActionId = 'SEARCH_STOCK' | 'VIEW_STOCK' | 'CHANGE_RANGE' | 'SEND_CHAT' | 'CLICK_NEWS' | 'DAILY_CHALLENGE';

type GamificationAction =
  | { type: 'USER_ACTION'; actionId: ActionId; ticker?: string }
  | { type: 'DISMISS_TOAST'; id: string }
  | { type: 'DISMISS_BADGE_TOAST' }
  | { type: 'STOP_CONFETTI' };

// ─── Initial / persisted state ────────────────────────────────────────────────

const INITIAL_MISSIONS: Mission[] = [
  { id: 'first_search',  title: 'First Search',     description: 'Search for any stock',              emoji: '🔍', completed: false, xpReward: 10 },
  { id: 'view_stock',    title: 'Market Explorer',  description: 'Open a stock analysis page',        emoji: '📈', completed: false, xpReward: 15 },
  { id: 'change_range',  title: 'Chart Analyst',    description: 'Change the chart time range',       emoji: '📊', completed: false, xpReward: 5  },
  { id: 'send_chat',     title: 'Ask the AI',       description: 'Send a message to the AI analyst',  emoji: '🤖', completed: false, xpReward: 20 },
  { id: 'click_news',   title: 'News Reader',      description: 'Open a news article',               emoji: '📰', completed: false, xpReward: 10 },
];

const INITIAL_BADGES: Badge[] = [
  { id: 'explorer',     title: 'Stock Explorer', description: 'Visit 3 different stock pages',   emoji: '🗺️', unlocked: false },
  { id: 'ai_whisperer', title: 'AI Whisperer',   description: 'Send 5 chat messages',            emoji: '🧠', unlocked: false },
  { id: 'news_junkie',  title: 'News Junkie',    description: 'Read 5 news articles',            emoji: '📰', unlocked: false },
];

const INITIAL_STATE: GamificationState = {
  xp: 0,
  toasts: [],
  missions: INITIAL_MISSIONS,
  badges: INITIAL_BADGES,
  stocksViewed: [],
  chatCount: 0,
  newsCount: 0,
  confetti: false,
  badgeToast: null,
};

const STORAGE_KEY = 'mn_gamification_v1';
const GAME_MODE_KEY = 'mn_game_mode';

/** Load persisted XP progress from localStorage. Merges with latest mission/badge definitions. */
function loadState(): GamificationState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return INITIAL_STATE;
    const saved = JSON.parse(raw);
    return {
      ...INITIAL_STATE,
      xp: saved.xp ?? 0,
      stocksViewed: saved.stocksViewed ?? [],
      chatCount: saved.chatCount ?? 0,
      newsCount: saved.newsCount ?? 0,
      // Merge completion state onto latest mission definitions
      missions: INITIAL_MISSIONS.map(m => {
        const s = (saved.missions ?? []).find((x: Mission) => x.id === m.id);
        return s ? { ...m, completed: s.completed } : m;
      }),
      // Merge unlock state onto latest badge definitions
      badges: INITIAL_BADGES.map(b => {
        const s = (saved.badges ?? []).find((x: Badge) => x.id === b.id);
        return s ? { ...b, unlocked: s.unlocked } : b;
      }),
      // Never restore transient UI state
      toasts: [],
      confetti: false,
      badgeToast: null,
    };
  } catch {
    return INITIAL_STATE;
  }
}

/** Persist the parts of state worth saving (not transient UI). */
function saveState(s: GamificationState) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      xp: s.xp,
      stocksViewed: s.stocksViewed,
      chatCount: s.chatCount,
      newsCount: s.newsCount,
      missions: s.missions.map(({ id, completed }) => ({ id, completed })),
      badges:   s.badges.map(({ id, unlocked })   => ({ id, unlocked })),
    }));
  } catch { /* ignore quota errors */ }
}

// ─── XP / action constants ────────────────────────────────────────────────────

const XP_MAP: Record<ActionId, number> = {
  SEARCH_STOCK:     10,
  VIEW_STOCK:       15,
  CHANGE_RANGE:     5,
  SEND_CHAT:        20,
  CLICK_NEWS:       10,
  DAILY_CHALLENGE:  50,
};

const MISSION_MAP: Partial<Record<ActionId, string>> = {
  SEARCH_STOCK:  'first_search',
  VIEW_STOCK:    'view_stock',
  CHANGE_RANGE:  'change_range',
  SEND_CHAT:     'send_chat',
  CLICK_NEWS:    'click_news',
};

// ─── Reducer ─────────────────────────────────────────────────────────────────

function reducer(state: GamificationState, action: GamificationAction): GamificationState {
  switch (action.type) {
    case 'USER_ACTION': {
      const { actionId, ticker } = action;
      let s = { ...state };

      const isNewStock = actionId === 'VIEW_STOCK' && ticker && !s.stocksViewed.includes(ticker);
      if (actionId === 'VIEW_STOCK' && !isNewStock && ticker) {
        const toastId = generateId();
        return { ...s, xp: s.xp + 3, toasts: [...s.toasts, { id: toastId, amount: 3 }] };
      }

      if (isNewStock && ticker)    s = { ...s, stocksViewed: [...s.stocksViewed, ticker] };
      if (actionId === 'SEND_CHAT')  s = { ...s, chatCount: s.chatCount + 1 };
      if (actionId === 'CLICK_NEWS') s = { ...s, newsCount: s.newsCount + 1 };

      const xpGained = XP_MAP[actionId];
      const newXp = s.xp + xpGained;
      const toastId = generateId();
      s = { ...s, xp: newXp, toasts: [...s.toasts, { id: toastId, amount: xpGained }] };

      const missionId = MISSION_MAP[actionId];
      if (missionId) {
        s = {
          ...s,
          missions: s.missions.map(m =>
            m.id === missionId && !m.completed ? { ...m, completed: true } : m
          ),
        };
      }

      let badgeToast: BadgeToast | null = null;
      let newBadges = [...s.badges];
      const checkBadge = (id: string, condition: boolean) => {
        const b = newBadges.find(b => b.id === id);
        if (b && !b.unlocked && condition) {
          newBadges = newBadges.map(b => b.id === id ? { ...b, unlocked: true } : b);
          badgeToast = { id, title: b.title, emoji: b.emoji };
        }
      };
      checkBadge('explorer',     s.stocksViewed.length >= 3);
      checkBadge('ai_whisperer', s.chatCount >= 5);
      checkBadge('news_junkie',  s.newsCount >= 5);

      s = { ...s, badges: newBadges };
      if (badgeToast) s = { ...s, badgeToast };

      const allDone = s.missions.every(m => m.completed);
      const prevAllDone = state.missions.every(m => m.completed);
      const prevMilestone = Math.floor(state.xp / 100);
      const newMilestone = Math.floor(newXp / 100);
      if (!!badgeToast || (allDone && !prevAllDone) || newMilestone > prevMilestone) {
        s = { ...s, confetti: true };
      }

      return s;
    }

    case 'DISMISS_TOAST':
      return { ...state, toasts: state.toasts.filter(t => t.id !== action.id) };

    case 'DISMISS_BADGE_TOAST':
      return { ...state, badgeToast: null };

    case 'STOP_CONFETTI':
      return { ...state, confetti: false };

    default:
      return state;
  }
}

// ─── Context ─────────────────────────────────────────────────────────────────

interface GamificationContextValue {
  state: GamificationState;
  gamificationEnabled: boolean;
  toggleGameMode: () => void;
  onSearchStock: () => void;
  onViewStock: (ticker: string) => void;
  onChangeChartRange: () => void;
  onSendChatMessage: () => void;
  onClickNews: () => void;
  onCompleteChallenge: () => void;
  dismissToast: (id: string) => void;
  dismissBadgeToast: () => void;
  stopConfetti: () => void;
}

const GamificationContext = createContext<GamificationContextValue | null>(null);

export function GamificationProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, undefined, loadState);

  const [gamificationEnabled, setGameMode] = useState<boolean>(() => {
    try { return localStorage.getItem(GAME_MODE_KEY) !== 'false'; }
    catch { return true; }
  });

  // Persist XP state on every change
  useEffect(() => { saveState(state); }, [state]);

  // Persist game mode preference
  const toggleGameMode = useCallback(() => {
    setGameMode(v => {
      const next = !v;
      try { localStorage.setItem(GAME_MODE_KEY, String(next)); } catch { /**/ }
      return next;
    });
  }, []);

  // Actions are no-ops when game mode is disabled
  const dispatchIfEnabled = useCallback(
    (action: GamificationAction) => { if (gamificationEnabled) dispatch(action); },
    [gamificationEnabled]
  );

  const onSearchStock      = useCallback(() => dispatchIfEnabled({ type: 'USER_ACTION', actionId: 'SEARCH_STOCK'   }), [dispatchIfEnabled]);
  const onViewStock        = useCallback((ticker: string) => dispatchIfEnabled({ type: 'USER_ACTION', actionId: 'VIEW_STOCK', ticker }), [dispatchIfEnabled]);
  const onChangeChartRange = useCallback(() => dispatchIfEnabled({ type: 'USER_ACTION', actionId: 'CHANGE_RANGE'   }), [dispatchIfEnabled]);
  const onSendChatMessage  = useCallback(() => dispatchIfEnabled({ type: 'USER_ACTION', actionId: 'SEND_CHAT'      }), [dispatchIfEnabled]);
  const onClickNews        = useCallback(() => dispatchIfEnabled({ type: 'USER_ACTION', actionId: 'CLICK_NEWS'     }), [dispatchIfEnabled]);
  const onCompleteChallenge= useCallback(() => dispatchIfEnabled({ type: 'USER_ACTION', actionId: 'DAILY_CHALLENGE' }), [dispatchIfEnabled]);
  const dismissToast       = useCallback((id: string) => dispatch({ type: 'DISMISS_TOAST', id }), []);
  const dismissBadgeToast  = useCallback(() => dispatch({ type: 'DISMISS_BADGE_TOAST' }), []);
  const stopConfetti       = useCallback(() => dispatch({ type: 'STOP_CONFETTI' }), []);

  return (
    <GamificationContext.Provider
      value={{ state, gamificationEnabled, toggleGameMode, onSearchStock, onViewStock, onChangeChartRange, onSendChatMessage, onClickNews, onCompleteChallenge, dismissToast, dismissBadgeToast, stopConfetti }}
    >
      {children}
    </GamificationContext.Provider>
  );
}

export function useGamification() {
  const ctx = useContext(GamificationContext);
  if (!ctx) throw new Error('useGamification must be used inside GamificationProvider');
  return ctx;
}

export const XP_PER_LEVEL = 100;
