import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { BarChart3, Zap, RefreshCw, TrendingUp, Activity, Shield } from 'lucide-react';
import SearchBar from '../components/SearchBar';
import DailyChallenge from '../components/DailyChallenge';
import NarrativeFeedCard from '../components/NarrativeFeedCard';
import { useGamification } from '../contexts/GamificationContext';
import { fetchTrending, type TrendingItem } from '../services/analysisService';

const POPULAR_TICKERS = ['AAPL', 'TSLA', 'NVDA', 'GME', 'META'];

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

const FEATURES = [
  { icon: TrendingUp, title: 'Sentiment',          description: 'FinBERT-scored news headlines — bullish, bearish, or mixed.' },
  { icon: Activity,   title: 'Narrative Velocity', description: 'Detect attention spikes before they mislead you.' },
  { icon: Shield,     title: 'Hype Detection',     description: 'Info-driven vs hype-driven coverage, scored 0–100.' },
];

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

  return (
    <div className="flex min-h-[calc(100vh-4rem)] flex-col">

      {/* ── Hero — vertically centered ──────────────────────────────────── */}
      <section className="relative flex flex-1 flex-col items-center justify-center overflow-hidden px-4 py-24">
        {/* Background layers */}
        <div className="pointer-events-none absolute inset-0 hero-grid" />
        <div className="pointer-events-none absolute inset-0 hero-spotlight" />
        <div
          className="pointer-events-none absolute -left-32 top-1/4 h-64 w-64 rounded-full opacity-20"
          style={{ background: 'radial-gradient(circle, #22c55e 0%, transparent 70%)', filter: 'blur(60px)' }}
        />
        <div
          className="pointer-events-none absolute -right-32 bottom-1/4 h-48 w-48 rounded-full opacity-15"
          style={{ background: 'radial-gradient(circle, #22c55e 0%, transparent 70%)', filter: 'blur(50px)' }}
        />

        {/* Logo + Wordmark */}
        <div className="relative mb-8 flex flex-col items-center gap-5">
          <div className="relative" style={{ animation: 'float 4s ease-in-out infinite' }}>
            <div
              className="absolute inset-0 rounded-2xl"
              style={{
                background: 'radial-gradient(circle, rgba(34,197,94,0.3), transparent)',
                filter: 'blur(16px)',
                animation: 'glow-pulse 3s ease-in-out infinite',
              }}
            />
            <div
              className="relative flex h-16 w-16 items-center justify-center rounded-2xl"
              style={{
                background: 'rgba(5,46,22,0.6)',
                border: '1px solid rgba(34,197,94,0.3)',
                boxShadow: '0 0 24px rgba(34,197,94,0.15)',
              }}
            >
              <BarChart3 className="h-8 w-8 text-brand-400" />
            </div>
          </div>

          <h1 className="text-5xl font-extrabold tracking-tight sm:text-6xl">
            <span
              style={{
                background: 'linear-gradient(135deg, #4ade80 0%, #22c55e 60%, #16a34a 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              Market
            </span>
            <span
              style={{
                background: 'linear-gradient(135deg, #4ade80 0%, #22c55e 60%, #16a34a 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              Noise
            </span>
          </h1>
        </div>

        {/* Tagline */}
        <div className="mb-10 text-center">
          <p className="text-xl font-medium text-neutral-300 sm:text-2xl">
            Cut through the noise.
          </p>
          <p className="mt-1 text-base text-neutral-500">
            Sentiment, velocity &amp; hype analysis for any US stock — powered by FinBERT.
          </p>
        </div>

        {/* Search */}
        <div className="relative z-10 w-full max-w-xl">
          <SearchBar large />
        </div>

        {/* Popular tickers */}
        <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
          <span className="text-xs text-neutral-600">Try:</span>
          {POPULAR_TICKERS.map((t) => (
            <button
              key={t}
              onClick={() => navigate(`/stock/${t}`)}
              className="rounded-full px-3 py-1 text-xs font-medium text-neutral-400 transition-all duration-200 hover:text-brand-400"
              style={{
                background: 'rgba(26,26,26,0.8)',
                border: '1px solid rgba(255,255,255,0.06)',
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = 'rgba(34,197,94,0.4)';
                (e.currentTarget as HTMLElement).style.boxShadow = '0 0 12px rgba(34,197,94,0.1)';
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.06)';
                (e.currentTarget as HTMLElement).style.boxShadow = 'none';
              }}
            >
              {t}
            </button>
          ))}
        </div>

        {/* Feature pills */}
        <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
          {FEATURES.map(({ icon: Icon, title, description }) => (
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

      {/* ── Daily Challenge ─────────────────────────────────────────────── */}
      {gamificationEnabled && (
        <section className="w-full px-4 pb-8 sm:px-8 lg:px-12">
          <div className="mx-auto max-w-lg">
            <DailyChallenge />
          </div>
        </section>
      )}

      {/* ── Live narrative feed ─────────────────────────────────────────── */}
      <section className="w-full px-4 pb-20 sm:px-8 lg:px-12">
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
  );
}
