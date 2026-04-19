import { useEffect, useState } from 'react';
import { Sparkles, Loader2 } from 'lucide-react';
import { fetchNarrativeSummary } from '../services/analysisService';

interface Props {
  ticker: string;
  companyName: string;
}

export default function NarrativeSummaryCard({ ticker, companyName }: Props) {
  const [summary, setSummary] = useState<string | null>(null);
  const [loading, setLoading]  = useState(true);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setSummary(null);
    setLoading(true);
    setUnavailable(false);

    fetchNarrativeSummary(ticker, companyName)
      .then((data) => {
        if (cancelled) return;
        if (data.summary) {
          setSummary(data.summary);
        } else {
          setUnavailable(true);
        }
      })
      .catch(() => {
        if (!cancelled) setUnavailable(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [ticker, companyName]);

  // Don't render anything if no LLM key is configured server-side
  if (!loading && unavailable) return null;

  return (
    <div
      className="mb-8 rounded-2xl p-5"
      style={{
        background: 'rgba(168,85,247,0.04)',
        border: '1px solid rgba(168,85,247,0.12)',
      }}
    >
      {/* Header */}
      <div className="mb-3 flex items-center gap-2.5">
        <div
          className="flex h-7 w-7 items-center justify-center rounded-lg"
          style={{
            background: 'radial-gradient(circle at 30% 30%, rgba(168,85,247,0.25), rgba(168,85,247,0.06))',
            border: '1px solid rgba(168,85,247,0.2)',
          }}
        >
          <Sparkles size={13} className="text-purple-400" />
        </div>
        <span className="text-xs font-semibold text-purple-300">AI Narrative Summary</span>
        <span
          className="rounded-full px-2 py-0.5 text-[10px] font-medium text-purple-400/60"
          style={{ background: 'rgba(168,85,247,0.08)', border: '1px solid rgba(168,85,247,0.12)' }}
        >
          Powered by FinBERT + LLM
        </span>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center gap-2.5">
          <Loader2 size={14} className="animate-spin text-purple-400/50 shrink-0" />
          <span className="text-xs text-white/30 italic">Generating narrative analysis…</span>
        </div>
      ) : (
        <p className="text-sm leading-relaxed text-white/70">{summary}</p>
      )}
    </div>
  );
}
