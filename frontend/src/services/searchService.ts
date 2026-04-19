import type { Stock } from '../types/stock';

export async function searchStocks(query: string): Promise<Stock[]> {
  const q = query.trim();
  if (q.length < 1) return [];

  try {
    const res = await fetch(`/api/market/search/?q=${encodeURIComponent(q)}`);
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}
