import { useEffect, useState, useRef } from 'react';
import { Bookmark, BookmarkCheck, Loader2 } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import {
  checkWatching,
  addToWatchlist,
  removeFromWatchlist,
} from '../services/watchlistService';

interface Props {
  ticker: string;
}

export default function WatchButton({ ticker }: Props) {
  const { getAccessToken, isAuthenticated } = useAuth();

  const [watching, setWatching] = useState(false);
  const [loading, setLoading]   = useState(true);
  const [working, setWorking]   = useState(false);
  const [justSaved, setJustSaved] = useState(false);
  const [error, setError]       = useState<string | null>(null);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Check initial status
  useEffect(() => {
    if (!isAuthenticated) { setLoading(false); return; }
    let cancelled = false;

    getAccessToken().then((token) => {
      if (!token || cancelled) { setLoading(false); return; }
      checkWatching(token, ticker)
        .then((w) => { if (!cancelled) setWatching(w); })
        .catch(() => {})
        .finally(() => { if (!cancelled) setLoading(false); });
    });

    return () => { cancelled = true; };
  }, [ticker, isAuthenticated]);

  // Cleanup timer on unmount
  useEffect(() => () => { if (saveTimerRef.current) clearTimeout(saveTimerRef.current); }, []);

  if (!isAuthenticated) return null;

  const toggle = async () => {
    if (working || loading) return;
    setWorking(true);
    setError(null);

    const token = await getAccessToken();
    if (!token) {
      setError('Session expired — please sign in again.');
      setWorking(false);
      return;
    }

    try {
      if (watching) {
        await removeFromWatchlist(token, ticker);
        setWatching(false);
        setJustSaved(false);
      } else {
        await addToWatchlist(token, ticker);
        setWatching(true);

        // Trigger "saved" animation
        setJustSaved(true);
        if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
        saveTimerRef.current = setTimeout(() => setJustSaved(false), 2000);
      }
    } catch (e: any) {
      setError('Could not update watchlist.');
      setTimeout(() => setError(null), 3000);
    } finally {
      setWorking(false);
    }
  };

  const isActive = watching;

  return (
    <div className="relative flex flex-col items-start gap-1">
      <button
        onClick={toggle}
        disabled={loading || working}
        title={watching ? 'Remove from watchlist' : 'Add to watchlist'}
        className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium disabled:opacity-40"
        style={{
          background: isActive ? 'rgba(34,197,94,0.12)' : 'rgba(255,255,255,0.04)',
          border: isActive ? '1px solid rgba(34,197,94,0.35)' : '1px solid rgba(255,255,255,0.08)',
          color: isActive ? '#4ade80' : 'rgba(255,255,255,0.5)',
          transition: 'background 0.25s, border-color 0.25s, color 0.25s, box-shadow 0.25s',
          boxShadow: justSaved ? '0 0 14px rgba(34,197,94,0.35)' : 'none',
        }}
      >
        {/* Icon */}
        <span
          style={{
            display: 'inline-flex',
            transform: justSaved ? 'scale(1.35)' : 'scale(1)',
            transition: 'transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1)',
          }}
        >
          {loading || working ? (
            <Loader2 size={13} className="animate-spin" />
          ) : watching ? (
            <BookmarkCheck size={13} />
          ) : (
            <Bookmark size={13} />
          )}
        </span>

        {/* Label */}
        <span style={{ transition: 'opacity 0.2s' }}>
          {watching ? 'Watching' : 'Watch'}
        </span>
      </button>

      {/* "Saved!" micro-toast */}
      <span
        className="pointer-events-none absolute -bottom-5 left-0 text-[10px] font-semibold text-brand-400"
        style={{
          opacity: justSaved ? 1 : 0,
          transform: justSaved ? 'translateY(0)' : 'translateY(-4px)',
          transition: 'opacity 0.2s, transform 0.2s',
          whiteSpace: 'nowrap',
        }}
      >
        ✓ Saved to watchlist
      </span>

      {/* Error micro-toast */}
      {error && (
        <span
          className="pointer-events-none absolute -bottom-5 left-0 text-[10px] font-semibold text-danger-400"
          style={{ whiteSpace: 'nowrap' }}
        >
          {error}
        </span>
      )}
    </div>
  );
}
