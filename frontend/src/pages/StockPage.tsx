import { useParams, Link } from 'react-router-dom';
import { useState, useEffect, useCallback, useRef } from 'react';
import { ArrowLeft, TrendingUp, TrendingDown, Loader2 } from 'lucide-react';
import { fetchChartData, type QuoteResult } from '../services/stockService';
import SearchBar from '../components/SearchBar';
import PriceChart, { type PriceChange } from '../components/PriceChart';
import AnalysisSection from '../components/AnalysisSection';
import NarrativeTimeline from '../components/NarrativeTimeline';
import ChatPanel from '../components/ChatPanel';
import NewsSection from '../components/NewsSection';
import NarrativeSummaryCard from '../components/NarrativeSummaryCard';
import WatchButton from '../components/WatchButton';
import type { PricePoint } from '../types/stock';
import { useGamification } from '../contexts/GamificationContext';

export default function StockPage() {
  const { ticker: rawTicker } = useParams<{ ticker: string }>();
  const ticker = rawTicker?.toUpperCase() || '';
  const { onViewStock, onChangeChartRange } = useGamification();
  const initialRangeFiredRef = useRef(false);

  const [quote, setQuote] = useState<QuoteResult | null>(null);
  const [chartPoints, setChartPoints] = useState<PricePoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [priceChange, setPriceChange] = useState<PriceChange | null>(null);

  const companyName = quote?.shortName || ticker;

  // Award XP on page visit
  useEffect(() => {
    if (!ticker) return;
    onViewStock(ticker);
  }, [ticker, onViewStock]);

  const handleRangeChange = useCallback((priceChange: PriceChange) => {
    setPriceChange(priceChange);
    // Skip the automatic first call (initial chart load); only award XP for user-initiated changes
    if (initialRangeFiredRef.current) {
      onChangeChartRange();
    } else {
      initialRangeFiredRef.current = true;
    }
  }, [onChangeChartRange]);

  useEffect(() => {
    if (!ticker) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setQuote(null);
    setChartPoints([]);

    fetchChartData(ticker, '1D')
      .then((data) => {
        if (cancelled) return;
        setQuote(data.quote);
        setChartPoints(data.points);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [ticker]);

  if (!ticker) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center px-4">
        <h2 className="mb-2 text-2xl font-bold text-white">No ticker specified</h2>
        <Link
          to="/"
          className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white no-underline transition-colors hover:bg-brand-700"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to search
        </Link>
      </div>
    );
  }

  const displayChange = priceChange?.change ?? quote?.regularMarketChange ?? 0;
  const displayChangePercent = priceChange?.changePercent ?? quote?.regularMarketChangePercent ?? 0;
  const displayPrice = priceChange?.currentPrice ?? quote?.regularMarketPrice;
  const rangeLabel = priceChange?.rangeLabel ?? 'Today';
  const isPositive = displayChange >= 0;

  return (
    <div className="w-full px-4 py-6 sm:px-8 lg:px-12">
      {/* Top bar: back + search */}
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <Link
          to="/"
          className="flex items-center gap-2 text-sm text-neutral-400 no-underline transition-colors hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to search
        </Link>
        <div className="w-full sm:w-80">
          <SearchBar />
        </div>
      </div>

      {/* Stock Header — full width, above the grid */}
      <div
        className="mb-6 flex items-start justify-between rounded-2xl p-5"
        style={{
          background: 'rgba(26,26,26,0.5)',
          border: '1px solid rgba(255,255,255,0.05)',
        }}
      >
        <div>
          <div className="flex items-center gap-3">
            <h1
              className="text-3xl font-extrabold tracking-tight text-white"
              style={{ textShadow: '0 0 30px rgba(255,255,255,0.08)' }}
            >
              {ticker}
            </h1>
            <WatchButton ticker={ticker} />
          </div>
          <p className="mt-1 text-sm text-neutral-500">
            {loading ? (
              <span className="skeleton inline-block h-4 w-40" />
            ) : (
              companyName
            )}
          </p>
        </div>
        <div className="text-right">
          {loading ? (
            <Loader2 className="ml-auto h-6 w-6 animate-spin text-brand-500" />
          ) : displayPrice != null ? (
            <>
              <p className="text-3xl font-extrabold tabular-nums text-white">
                ${displayPrice.toFixed(2)}
              </p>
              <div
                className={`mt-1 inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-sm font-semibold ${
                  isPositive ? 'text-brand-400' : 'text-danger-400'
                }`}
                style={{
                  background: isPositive ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)',
                  border: isPositive ? '1px solid rgba(34,197,94,0.2)' : '1px solid rgba(239,68,68,0.2)',
                }}
              >
                {isPositive ? (
                  <TrendingUp className="h-3.5 w-3.5" />
                ) : (
                  <TrendingDown className="h-3.5 w-3.5" />
                )}
                <span>
                  {isPositive ? '+' : ''}{displayChange.toFixed(2)} ({isPositive ? '+' : ''}{displayChangePercent.toFixed(2)}%)
                </span>
              </div>
              <p className="mt-0.5 text-[11px] text-neutral-600">{rangeLabel}</p>
            </>
          ) : (
            <>
              <p className="text-2xl font-bold text-neutral-500">$ —</p>
              <p className="text-sm text-neutral-600">{error || 'Price unavailable'}</p>
            </>
          )}
        </div>
      </div>

      {/* 2-column layout: content left (2fr), chat sidebar right (1fr sticky) */}
      <div className="flex flex-col gap-6 lg:grid lg:items-start lg:grid-cols-[2fr_1fr]">
        {/* Left column: chart + narrative + analysis + news */}
        <div className="flex flex-col gap-8">
          <PriceChart ticker={ticker} initialPoints={chartPoints} initialLoading={loading} onRangeChange={handleRangeChange} />
          <NarrativeSummaryCard ticker={ticker} companyName={companyName} />
          <AnalysisSection ticker={ticker} companyName={companyName} />
          <div>
            <h2 className="mb-4 text-lg font-semibold text-white">
              Narrative Timeline —{' '}
              <span className="text-purple-400">{ticker}</span>
            </h2>
            <NarrativeTimeline ticker={ticker} />
          </div>
          <NewsSection ticker={ticker} companyName={companyName} />
        </div>

        {/* Right column: sticky chat panel — fills viewport height below navbar */}
        <div className="sticky top-24 h-[calc(100vh-7rem)]">
          <ChatPanel ticker={ticker} companyName={companyName} />
        </div>
      </div>
    </div>
  );
}
