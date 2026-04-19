import { useState, useEffect, useRef } from 'react';
import { Newspaper, ExternalLink, Loader2 } from 'lucide-react';
import { fetchStockNews } from '../services/newsService';
import type { NewsItem } from '../types/stock';
import { useGamification } from '../contexts/GamificationContext';

interface NewsSectionProps {
  ticker: string;
  companyName: string;
}

export default function NewsSection({ ticker, companyName }: NewsSectionProps) {
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Keep companyName current without triggering re-fetches when the quote
  // loads and changes it from "AAPL" → "Apple Inc." — ticker is the stable key.
  const { onClickNews } = useGamification();
  const companyNameRef = useRef(companyName);
  useEffect(() => { companyNameRef.current = companyName; }, [companyName]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setNews([]);  // clear stale articles from previous ticker immediately

    fetchStockNews(ticker, companyNameRef.current)
      .then((items) => {
        if (!cancelled) setNews(items);
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
  }, [ticker]);  // only re-fetch when the ticker changes, not when quote loads

  return (
    <div>
      <div className="mb-4 flex items-center gap-3">
        <div className="relative">
          <Newspaper className="h-5 w-5 text-brand-400" />
          <span
            className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-brand-500"
            style={{ animation: 'glow-pulse 2s ease-in-out infinite' }}
          />
        </div>
        <h2 className="text-lg font-semibold text-white">
          Latest News — <span className="text-brand-400">{ticker}</span>
        </h2>
      </div>

      {loading ? (
        <div
          className="flex h-48 items-center justify-center rounded-2xl"
          style={{ background: 'rgba(26,26,26,0.5)', border: '1px solid rgba(255,255,255,0.05)' }}
        >
          <Loader2 className="h-6 w-6 animate-spin text-brand-500" />
        </div>
      ) : error || news.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-surface-600 bg-surface-800/50 p-10 text-center">
          <Newspaper className="mx-auto mb-3 h-10 w-10 text-neutral-600" />
          <h3 className="mb-1 font-semibold text-neutral-400">
            {error ? 'Could not load news' : 'No news found'}
          </h3>
          <p className="text-sm text-neutral-500">
            {error || `No recent news articles found for ${ticker}.`}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {news.map((item) => (
            <a
              key={item.id}
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={onClickNews}
              className="group relative flex items-start gap-4 rounded-xl p-4 no-underline transition-all duration-200"
              style={{
                background: 'rgba(26,26,26,0.5)',
                border: '1px solid rgba(255,255,255,0.05)',
                borderLeft: '2px solid transparent',
              }}
              onMouseEnter={(e) => {
                const el = e.currentTarget as HTMLElement;
                el.style.borderLeftColor = 'rgba(34,197,94,0.5)';
                el.style.background = 'rgba(26,26,26,0.9)';
              }}
              onMouseLeave={(e) => {
                const el = e.currentTarget as HTMLElement;
                el.style.borderLeftColor = 'transparent';
                el.style.background = 'rgba(26,26,26,0.5)';
              }}
            >
              {/* Source initial avatar */}
              <div
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-xs font-bold uppercase"
                style={{
                  background: 'rgba(34,197,94,0.1)',
                  border: '1px solid rgba(34,197,94,0.2)',
                  color: '#4ade80',
                }}
              >
                {item.source.charAt(0)}
              </div>

              <div className="flex-1 min-w-0">
                <h3 className="mb-1.5 text-sm font-medium leading-snug text-neutral-200 transition-colors group-hover:text-white line-clamp-2">
                  {item.headline}
                </h3>
                <div className="flex items-center gap-2">
                  <span
                    className="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
                    style={{
                      background: 'rgba(34,197,94,0.08)',
                      color: '#4ade80',
                      border: '1px solid rgba(34,197,94,0.15)',
                    }}
                  >
                    {item.source}
                  </span>
                  <span className="text-[11px] text-neutral-600">{item.timestamp}</span>
                </div>
              </div>

              <ExternalLink className="mt-0.5 h-3.5 w-3.5 shrink-0 text-neutral-700 transition-all group-hover:text-brand-500" />
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
