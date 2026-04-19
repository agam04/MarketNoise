import type { NewsItem } from '../types/stock';

export async function fetchStockNews(
  ticker: string,
  companyName: string
): Promise<NewsItem[]> {
  try {
    const res = await fetch(
      `/api/market/news/${ticker}/?name=${encodeURIComponent(companyName)}`
    );
    if (!res.ok) return [];
    const data = await res.json();
    if (!Array.isArray(data)) return [];

    return data.map((a) => ({
      ...a,
      timestamp: formatTimeAgo(a.timestamp),
    }));
  } catch {
    return [];
  }
}

function formatTimeAgo(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffMs = now - then;
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 60) return `${diffMins}m ago`;

  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;

  return new Date(dateStr).toLocaleDateString([], { month: 'short', day: 'numeric' });
}
