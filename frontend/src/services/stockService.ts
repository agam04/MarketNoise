import type { PricePoint } from '../types/stock';
import type { TimeRange } from '../utils/constants';

export interface QuoteResult {
  regularMarketPrice: number;
  regularMarketChange: number;
  regularMarketChangePercent: number;
  regularMarketPreviousClose: number;
  shortName: string;
}

export async function fetchQuote(ticker: string): Promise<QuoteResult> {
  const res = await fetch(`/api/market/quote/${ticker}/`);
  if (!res.ok) throw new Error(`Quote fetch failed: ${res.status}`);
  const data = await res.json();
  if (data.error) throw new Error(data.error);
  return data as QuoteResult;
}

export async function fetchPriceHistory(
  ticker: string,
  timeRange: TimeRange
): Promise<PricePoint[]> {
  const res = await fetch(`/api/market/chart/${ticker}/?range=${timeRange}`);
  if (!res.ok) throw new Error(`Chart fetch failed: ${res.status}`);
  const data = await res.json();
  if (data.error) throw new Error(data.error);
  return data as PricePoint[];
}

export async function fetchChartData(
  ticker: string,
  timeRange: TimeRange
): Promise<{ points: PricePoint[]; quote: QuoteResult }> {
  const [points, quote] = await Promise.all([
    fetchPriceHistory(ticker, timeRange),
    fetchQuote(ticker),
  ]);
  return { points, quote };
}
