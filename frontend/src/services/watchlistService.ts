export interface WatchlistItem {
  ticker: string;
  name: string;
  added_at: string;
  hype_score: number | null;
  hype_level: 'low' | 'moderate' | 'high' | 'extreme' | null;
  velocity_trend: 'accelerating' | 'decelerating' | 'stable' | null;
  compound: number | null;
  sentiment_label: string | null;
  has_data: boolean;
}

function authHeaders(token: string): HeadersInit {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
}

export async function getWatchlist(token: string): Promise<WatchlistItem[]> {
  const res = await fetch('/api/market/watchlist/', {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to fetch watchlist');
  return res.json();
}

export async function checkWatching(token: string, ticker: string): Promise<boolean> {
  const res = await fetch(`/api/market/watchlist/${ticker}/`, {
    headers: authHeaders(token),
  });
  if (!res.ok) return false;
  const data = await res.json();
  return data.watching;
}

export async function addToWatchlist(token: string, ticker: string): Promise<void> {
  const res = await fetch('/api/market/watchlist/', {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ ticker }),
  });
  if (!res.ok) throw new Error('Failed to add to watchlist');
}

export async function removeFromWatchlist(token: string, ticker: string): Promise<void> {
  const res = await fetch('/api/market/watchlist/', {
    method: 'DELETE',
    headers: authHeaders(token),
    body: JSON.stringify({ ticker }),
  });
  if (!res.ok) throw new Error('Failed to remove from watchlist');
}
