export interface SentimentResult {
  ticker: string;
  label: string;
  compound: number;
  positive: number;
  negative: number;
  neutral: number;
  article_count: number;
  explanation: string;
  articles: {
    title: string;
    source: string;
    label: string;
    compound: number;
    positive: number;
    negative: number;
    neutral: number;
  }[];
}

export interface VelocityResult {
  ticker: string;
  score: number;
  trend: 'accelerating' | 'decelerating' | 'stable';
  mention_count: number;
  change_percent: number;
  explanation: string;
}

export interface HypeResult {
  ticker: string;
  score: number;
  level: 'low' | 'moderate' | 'high' | 'extreme';
  sentiment_imbalance: number;
  velocity_factor: number;
  source_concentration: number;
  explanation: string;
}

export interface PatternResult {
  id: string;
  name: string;
  description: string;
  risk: 'extreme' | 'high' | 'moderate' | 'low';
  color: string;
  signals_matched: string[];
}

export interface AnalysisResult {
  sentiment: SentimentResult;
  velocity: VelocityResult;
  hype: HypeResult;
  pattern: PatternResult;
}

// ── Drift ──────────────────────────────────────────────────────────────────

export interface DriftPoint {
  date: string;
  compound: number;
  count: number;
  label: 'positive' | 'negative' | 'neutral';
}

export interface DriftWindow {
  avg_compound: number;
  article_count: number;
  direction: 'positive' | 'negative' | 'neutral';
  drift_direction: 'improving' | 'worsening' | 'stable';
  drift_magnitude: number;
}

export interface DriftShift {
  detected: boolean;
  date: string | null;
  from_label: string | null;
  to_label: string | null;
  description: string;
}

export interface DriftResult {
  ticker: string;
  timeline: DriftPoint[];
  windows: {
    '7d': DriftWindow | null;
    '30d': DriftWindow | null;
    '90d': DriftWindow | null;
  };
  shift: DriftShift;
  data_available: boolean;
}

// ── Trending feed ──────────────────────────────────────────────────────────

export interface TrendingItem {
  ticker: string;
  name: string;
  hype_score: number;
  hype_level: 'low' | 'moderate' | 'high' | 'extreme';
  velocity_trend: 'accelerating' | 'decelerating' | 'stable';
  velocity_score: number;
  compound: number;
  sentiment_label: string;
  article_count: number;
  pattern: PatternResult;
  composite_score: number;
}

// ── Helpers ────────────────────────────────────────────────────────────────

async function fetchWithTimeout(url: string, timeoutMs: number): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { signal: controller.signal });
  } finally {
    clearTimeout(id);
  }
}

// ── API calls ──────────────────────────────────────────────────────────────

export async function fetchAnalysis(
  ticker: string,
  companyName: string
): Promise<AnalysisResult> {
  const res = await fetchWithTimeout(
    `/api/market/analyze/${ticker}/?name=${encodeURIComponent(companyName)}`,
    45000
  );
  if (!res.ok) throw new Error(`Analysis failed: ${res.status}`);
  return await res.json();
}

export async function fetchNarrativeSummary(
  ticker: string,
  companyName: string
): Promise<{ ticker: string; summary: string | null }> {
  const res = await fetch(
    `/api/market/narrative-summary/${ticker}/?name=${encodeURIComponent(companyName)}`
  );
  if (!res.ok) throw new Error(`Summary fetch failed: ${res.status}`);
  return await res.json();
}

export async function fetchTrending(): Promise<TrendingItem[]> {
  const res = await fetch('/api/market/trending/');
  if (!res.ok) throw new Error(`Trending fetch failed: ${res.status}`);
  return await res.json();
}

export async function fetchDrift(ticker: string): Promise<DriftResult> {
  const res = await fetchWithTimeout(`/api/market/drift/${ticker}/`, 30000);
  if (!res.ok) throw new Error(`Drift fetch failed: ${res.status}`);
  return await res.json();
}
