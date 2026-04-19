import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Zap, RefreshCw, TrendingUp, Activity, Shield } from 'lucide-react';
import SearchBar from '../components/SearchBar';
import DailyChallenge from '../components/DailyChallenge';
import NarrativeFeedCard from '../components/NarrativeFeedCard';
import { useGamification } from '../contexts/GamificationContext';
import { fetchTrending, type TrendingItem } from '../services/analysisService';

const POPULAR_TICKERS = ['AAPL', 'TSLA', 'NVDA', 'GME', 'META'];

// ── Skeleton card for loading state ────────────────────────────────────────
function FeedSkeleton() {
  return (
    <div
      className="rounded-2xl p-5 animate-pulse"
      style={{
        background: '#1a1a1a',
        border: '1px solid rgba(255,255,255,0.05)',
        borderTopWidth: 2,
        borderTopColor: 'rgba(255,255,255,0.08)',
      }}
    >
      <div className="mb-3 flex items-start justify-between">
        <div className="flex items-center gap-2.5">
          <div className="h-3 w-3 rounded bg-white/10" />
          <div>
            <div className="h-4 w-12 rounded bg-white/10" />
            <div className="mt-1 h-2.5 w-24 rounded bg-white/[0.06]" />
          </div>
        </div>
        <div className="h-4 w-16 rounded-full bg-white/[0.06]" />
      </div>
      <div className="mb-3 flex items-center gap-2">
        <div className="h-5 w-5 rounded-md bg-white/[0.06]" />
        <div className="h-3 w-32 rounded bg-white/[0.06]" />
      </div>
      <div className="mb-3 h-px bg-white/[0.04]" />
      <div className="flex justify-between">
        <div className="h-3 w-20 rounded bg-white/[0.06]" />
        <div className="h-3 w-16 rounded bg-white/[0.06]" />
      </div>
      <div className="mt-3">
        <div className="h-1 w-full rounded-full bg-white/[0.04]" />
      </div>
    </div>
  );
}

// ── Empty state when no scraped data exists yet ────────────────────────────
function FeedEmptyState({ onSearch }: { onSearch: (t: string) => void }) {
  return (
    <div
      className="col-span-full flex flex-col items-center justify-center gap-5 rounded-2xl py-16 text-center"
      style={{
        background: 'rgba(26,26,26,0.5)',
        border: '1px dashed rgba(255,255,255,0.08)',
      }}
    >
      <div
        className="flex h-14 w-14 items-center justify-center rounded-2xl"
        style={{
          background: 'rgba(34,197,94,0.06)',
          border: '1px solid rgba(34,197,94,0.15)',
        }}
      >
        <Zap className="h-6 w-6 text-brand-500" />
      </div>
      <div>
        <p className="text-sm font-semibold text-white/70">Feed populating…</p>
        <p className="mt-1 max-w-xs text-xs text-white/30 leading-relaxed">
          Search for a stock to run analysis. Once data accumulates the live feed
          will appear here automatically.
        </p>
      </div>
      <div className="flex flex-wrap justify-center gap-2">
        {POPULAR_TICKERS.map((t) => (
          <button
            key={t}
            onClick={() => onSearch(t)}
            className="rounded-full px-3 py-1 text-xs font-medium text-neutral-400 transition-all duration-200 hover:text-brand-400"
            style={{
              background: 'rgba(26,26,26,0.8)',
              border: '1px solid rgba(255,255,255,0.06)',
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLElement).style.borderColor = 'rgba(34,197,94,0.4)';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.06)';
            }}
          >
            {t}
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────
export default function HomePage() {
  const navigate = useNavigate();
  const { gamificationEnabled } = useGamification();
  const [feed, setFeed]       = useState<TrendingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const loadFeed = () => {
    setLoading(true);
    fetchTrending()
      .then((data) => {
        setFeed(data);
        setLastUpdated(new Date());
      })
      .catch(() => setFeed([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadFeed();
  }, []);

  const features = [
    { icon: TrendingUp, title: 'Sentiment',        description: 'FinBERT-scored news headlines — bullish, bearish, or mixed.' },
    { icon: Activity,   title: 'Narrative Velocity', description: 'Detect attention spikes before they mislead you.' },
    { icon: Shield,     title: 'Hype Detection',   description: 'Info-driven vs hype-driven coverage, scored 0-100.' },
  ];

  return (
    <div>

      {/* ── Full-width hero — flush against navbar ──────────────────────── */}
      <section
        className="relative flex flex-col items-center overflow-hidden px-4 pb-12 pt-16 text-center"
        style={{ borderBottom: '1px solid rgba(34,197,94,0.08)' }}
      >
        {/* Background layers */}
        <div className="pointer-events-none absolute inset-0 hero-grid opacity-50" />
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            background: 'radial-gradient(ellipse 70% 100% at 50% 0%, rgba(34,197,94,0.06), transparent)',
          }}
        />

        {/* Headline — value prop, not brand repeat */}
        <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-brand-500">
          Real-time narrative intelligence
        </p>
        <h1 className="mb-4 text-4xl font-extrabold tracking-tight text-white sm:text-5xl">
          Cut through the noise.
        </h1>
        <p className="mb-8 max-w-md text-sm leading-relaxed text-neutral-500">
          Sentiment, velocity &amp; hype analysis for any US stock — powered by FinBERT.
          Know if attention is information-driven or just noise.
        </p>

        {/* Search */}
        <div className="relative z-10 w-full max-w-lg">
          <SearchBar large />
        </div>

        {/* Feature pills */}
        <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
          {features.map(({ icon: Icon, title, description }) => (
            <div
              key={title}
              className="flex items-center gap-2 rounded-full px-3 py-1.5"
              style={{
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.06)',
              }}
              title={description}
            >
              <Icon className="h-3.5 w-3.5 text-brand-500" />
              <span className="text-xs text-neutral-400">{title}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ── Daily Challenge — only shown when game mode is on ───────────── */}
      {gamificationEnabled && (
        <div className="mx-auto max-w-lg px-4 pt-8 sm:px-6">
          <DailyChallenge />
        </div>
      )}

      {/* ── Live narrative feed ─────────────────────────────────────────── */}
      <div className="w-full px-4 pt-8 pb-10 sm:px-8 lg:px-12">
      <section>
        {/* Section header */}
        <div className="mb-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className="flex h-8 w-8 items-center justify-center rounded-lg"
              style={{
                background: 'radial-gradient(circle at 30% 30%, rgba(34,197,94,0.2), rgba(34,197,94,0.04))',
                border: '1px solid rgba(34,197,94,0.15)',
              }}
            >
              <Zap size={14} className="text-brand-400" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-white">Market Pulse</h2>
              <p className="text-[11px] text-white/30">
                {feed.length > 0
                  ? `${feed.length} active narrative${feed.length !== 1 ? 's' : ''} tracked`
                  : 'Live narrative dynamics'}
              </p>
            </div>
          </div>

          {/* Refresh + last updated */}
          <div className="flex items-center gap-3">
            {lastUpdated && !loading && (
              <span className="text-[10px] text-white/20">
                updated {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
            <button
              onClick={loadFeed}
              disabled={loading}
              className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-neutral-500 transition-all hover:text-white disabled:opacity-40"
              style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)' }}
            >
              <RefreshCw size={11} className={loading ? 'animate-spin' : ''} />
              Refresh
            </button>
          </div>
        </div>

        {/* Feed grid */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {loading ? (
            Array.from({ length: 8 }).map((_, i) => <FeedSkeleton key={i} />)
          ) : feed.length === 0 ? (
            <FeedEmptyState onSearch={(t) => navigate(`/stock/${t}`)} />
          ) : (
            feed.map((item, i) => (
              <NarrativeFeedCard key={item.ticker} item={item} rank={i + 1} />
            ))
          )}
        </div>
      </section>
      </div>
    </div>
  );
}
