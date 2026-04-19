import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bookmark, TrendingUp, TrendingDown, Minus, Zap, ArrowRight, Loader2 } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { getWatchlist, type WatchlistItem } from '../services/watchlistService';

const HYPE_COLOR: Record<string, string> = {
  extreme: '#f87171',
  high:    '#fbbf24',
  moderate:'#93c5fd',
  low:     '#86efac',
};

const SENTIMENT_GRADIENT: Record<string, string> = {
  positive: 'linear-gradient(135deg, #4ade80, #22c55e)',
  negative: 'linear-gradient(135deg, #f87171, #ef4444)',
  neutral:  'linear-gradient(135deg, #a3a3a3, #737373)',
};

function WatchlistRow({ item }: { item: WatchlistItem }) {
  const sentDisplay =
    item.sentiment_label === 'positive' ? 'Bullish'
    : item.sentiment_label === 'negative' ? 'Bearish'
    : item.sentiment_label === 'neutral' ? 'Neutral'
    : '—';

  const VelIcon =
    item.velocity_trend === 'accelerating' ? TrendingUp
    : item.velocity_trend === 'decelerating' ? TrendingDown
    : Minus;

  const velColor =
    item.velocity_trend === 'accelerating' ? '#fbbf24'
    : item.velocity_trend === 'decelerating' ? '#4ade80'
    : '#6b7280';

  return (
    <Link
      to={`/stock/${item.ticker}`}
      className="group flex items-center justify-between gap-4 rounded-xl px-4 py-3.5 no-underline transition-all duration-200 hover:-translate-y-px"
      style={{
        background: '#1a1a1a',
        border: '1px solid rgba(255,255,255,0.06)',
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.1)';
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.06)';
      }}
    >
      {/* Ticker + name */}
      <div className="min-w-[80px]">
        <p className="text-sm font-bold text-white">{item.ticker}</p>
        <p className="text-[11px] text-white/30 truncate max-w-[140px]">{item.name}</p>
      </div>

      {/* Sentiment */}
      <div className="hidden sm:block min-w-[80px]">
        {item.sentiment_label ? (
          <span
            className="text-xs font-semibold"
            style={{
              background: SENTIMENT_GRADIENT[item.sentiment_label] ?? SENTIMENT_GRADIENT.neutral,
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            {sentDisplay}
          </span>
        ) : (
          <span className="text-xs text-white/20">No data</span>
        )}
        {item.compound !== null && (
          <p className="text-[10px] text-white/25 tabular-nums">
            {item.compound >= 0 ? '+' : ''}{item.compound.toFixed(3)}
          </p>
        )}
      </div>

      {/* Velocity */}
      <div className="hidden md:flex items-center gap-1.5 min-w-[110px]">
        {item.velocity_trend ? (
          <>
            <VelIcon size={12} style={{ color: velColor }} />
            <span className="text-xs capitalize" style={{ color: velColor }}>
              {item.velocity_trend}
            </span>
          </>
        ) : (
          <span className="text-xs text-white/20">—</span>
        )}
      </div>

      {/* Hype */}
      <div className="min-w-[90px]">
        {item.hype_score !== null && item.hype_level ? (
          <div className="flex items-center gap-1.5">
            <Zap size={11} style={{ color: HYPE_COLOR[item.hype_level] ?? '#86efac' }} />
            <span className="text-xs font-semibold tabular-nums"
              style={{ color: HYPE_COLOR[item.hype_level] ?? '#86efac' }}>
              {item.hype_score.toFixed(0)}/100
            </span>
            <span className="text-[10px] text-white/30 capitalize">({item.hype_level})</span>
          </div>
        ) : (
          <span className="text-xs text-white/20">Run analysis</span>
        )}
      </div>

      <ArrowRight size={14} className="text-white/20 group-hover:text-white/50 transition-colors shrink-0" />
    </Link>
  );
}

export default function WatchlistPage() {
  const { getAccessToken, isAuthenticated } = useAuth();

  const [items, setItems]     = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated) { setLoading(false); return; }
    getAccessToken().then((token) => {
      if (!token) { setLoading(false); return; }
      getWatchlist(token)
        .then(setItems)
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false));
    });
  }, [isAuthenticated]);

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      {/* Header */}
      <div className="mb-6 flex items-center gap-3">
        <div
          className="flex h-9 w-9 items-center justify-center rounded-xl"
          style={{
            background: 'radial-gradient(circle at 30% 30%, rgba(34,197,94,0.2), rgba(34,197,94,0.04))',
            border: '1px solid rgba(34,197,94,0.2)',
          }}
        >
          <Bookmark size={16} className="text-brand-400" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-white">Watchlist</h1>
          <p className="text-xs text-white/30">
            {items.length > 0 ? `${items.length} ticker${items.length !== 1 ? 's' : ''} saved` : 'Your saved tickers'}
          </p>
        </div>
      </div>

      {/* Column headers */}
      {items.length > 0 && (
        <div className="mb-2 flex items-center justify-between gap-4 px-4 text-[10px] font-medium uppercase tracking-widest text-white/20">
          <span className="min-w-[80px]">Ticker</span>
          <span className="hidden sm:block min-w-[80px]">Sentiment</span>
          <span className="hidden md:block min-w-[110px]">Velocity</span>
          <span className="min-w-[90px]">Hype</span>
          <span className="w-4" />
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="flex h-40 items-center justify-center">
          <Loader2 size={20} className="animate-spin text-white/20" />
        </div>
      ) : error ? (
        <div className="rounded-xl p-6 text-center text-sm text-danger-400"
          style={{ background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.15)' }}>
          {error}
        </div>
      ) : items.length === 0 ? (
        <div
          className="flex flex-col items-center justify-center gap-4 rounded-2xl py-16 text-center"
          style={{ background: 'rgba(26,26,26,0.5)', border: '1px dashed rgba(255,255,255,0.08)' }}
        >
          <div className="rounded-full border border-white/[0.06] bg-white/[0.03] p-4">
            <Bookmark size={22} className="text-white/20" />
          </div>
          <div>
            <p className="text-sm font-medium text-white/50">Nothing saved yet</p>
            <p className="mt-1 text-xs text-white/25">
              Hit the <strong className="text-white/40">Watch</strong> button on any stock page to save it here.
            </p>
          </div>
          <Link
            to="/"
            className="rounded-lg px-4 py-2 text-xs font-medium text-brand-400 no-underline transition-all hover:text-brand-300"
            style={{ background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.2)' }}
          >
            Browse market feed
          </Link>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {items.map((item) => <WatchlistRow key={item.ticker} item={item} />)}
        </div>
      )}
    </div>
  );
}
