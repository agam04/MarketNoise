import { useEffect, useState, useRef } from 'react';
import { TrendingUp, Activity, AlertTriangle, Loader2 } from 'lucide-react';
import {
  fetchAnalysis,
  type AnalysisResult,
  type SentimentResult,
  type VelocityResult,
  type HypeResult,
} from '../services/analysisService';
import PatternCard from './PatternCard';

interface AnalysisSectionProps {
  ticker: string;
  companyName?: string;
}

/* ---------- Hover tooltip — "why this score" ── */
function ScoreTooltip({ text }: { text: string }) {
  return (
    <div
      className="pointer-events-none absolute bottom-[calc(100%+10px)] left-1/2 z-50 w-64 -translate-x-1/2 rounded-xl p-3"
      style={{
        background: 'rgba(8,12,20,0.97)',
        border: '1px solid rgba(34,197,94,0.2)',
        backdropFilter: 'blur(16px)',
        boxShadow: '0 12px 40px rgba(0,0,0,0.6)',
      }}
    >
      <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-brand-400">Why this score</p>
      <p className="text-xs leading-relaxed text-neutral-400">{text}</p>
      {/* Down-pointing arrow */}
      <div
        className="absolute left-1/2 top-full -translate-x-1/2"
        style={{
          width: 0, height: 0,
          borderLeft: '6px solid transparent',
          borderRight: '6px solid transparent',
          borderTop: '6px solid rgba(34,197,94,0.2)',
        }}
      />
    </div>
  );
}

/* ---------- Shared card wrapper with top accent + hover tooltip ---------- */
function AnalysisCard({
  accentColor,
  tooltip,
  children,
}: {
  accentColor: string;
  tooltip?: string;
  children: React.ReactNode;
}) {
  const [hovered, setHovered] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Small delay so rapid mouse-overs don't flash the tooltip
  const handleEnter = () => { timerRef.current = setTimeout(() => setHovered(true), 300); };
  const handleLeave = () => { if (timerRef.current) clearTimeout(timerRef.current); setHovered(false); };

  return (
    <div
      className="group relative overflow-visible rounded-2xl bg-surface-800 p-5 transition-all duration-300"
      style={{
        border: hovered ? '1px solid rgba(34,197,94,0.2)' : '1px solid rgba(255,255,255,0.06)',
        boxShadow: hovered ? '0 0 20px rgba(34,197,94,0.06), 0 1px 3px rgba(0,0,0,0.3)' : '0 1px 3px rgba(0,0,0,0.3)',
        transform: hovered ? 'translateY(-2px)' : 'none',
      }}
      onMouseEnter={handleEnter}
      onMouseLeave={handleLeave}
    >
      <div
        className="absolute left-0 right-0 top-0 h-0.5 rounded-t-2xl"
        style={{ background: `linear-gradient(90deg, ${accentColor}, transparent)` }}
      />
      {children}
      {hovered && tooltip && <ScoreTooltip text={tooltip} />}
    </div>
  );
}

/* ---------- Shared icon badge ---------- */
function IconBadge({ icon: Icon, color }: { icon: typeof TrendingUp; color: string }) {
  return (
    <div
      className="flex h-11 w-11 items-center justify-center rounded-xl"
      style={{
        background: `radial-gradient(circle at 30% 30%, ${color}33, ${color}0d)`,
        border: `1px solid ${color}33`,
        boxShadow: `0 0 16px ${color}1a, inset 0 1px 0 rgba(255,255,255,0.05)`,
      }}
    >
      <Icon className="h-5 w-5" style={{ color }} />
    </div>
  );
}

/* ---------- Shared explanation box ---------- */
function ExplanationBox({ label, text, accentColor }: { label: string; text: string; accentColor: string }) {
  return (
    <div
      className="rounded-lg p-3"
      style={{
        background: 'rgba(10,10,10,0.5)',
        borderLeft: `2px solid ${accentColor}4d`,
      }}
    >
      <p className="mb-1 text-xs font-medium" style={{ color: accentColor }}>{label}</p>
      <p className="text-xs leading-relaxed text-neutral-400">{text}</p>
    </div>
  );
}

/* ---------- Sentiment Card ---------- */
function SentimentCard({ data, loading }: { data: SentimentResult | null; loading: boolean }) {
  const label = data?.label || '—';
  const compound = data?.compound ?? 0;
  const articleCount = data?.article_count ?? 0;

  const labelDisplay = label === 'positive' ? 'Bullish' : label === 'negative' ? 'Bearish' : 'Neutral';
  const gradientMap: Record<string, string> = {
    positive: 'linear-gradient(135deg, #4ade80, #22c55e)',
    negative: 'linear-gradient(135deg, #f87171, #ef4444)',
    neutral: 'linear-gradient(135deg, #a3a3a3, #737373)',
  };
  const barPercent = Math.round((compound + 1) * 50);

  return (
    <AnalysisCard
      accentColor="#22c55e"
      tooltip={data?.explanation || 'FinBERT NLP scores each article headline on a -1 (bearish) to +1 (bullish) scale, then aggregates across recent articles using exponential decay weighting — newer articles count more.'}
    >
      <div className="mb-4 flex items-center gap-3">
        <IconBadge icon={TrendingUp} color="#4ade80" />
        <h3 className="font-semibold text-white">Sentiment Analysis</h3>
      </div>

      <div className="mb-4 rounded-xl bg-surface-700/50 p-4 text-center">
        {loading ? (
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-brand-400" />
        ) : data ? (
          <>
            <p
              className="text-3xl font-extrabold tracking-tight"
              style={{
                background: gradientMap[label] || gradientMap.neutral,
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              {labelDisplay}
            </p>
            <p className="mt-1 text-xs text-neutral-500">
              Score: {compound.toFixed(2)} | {articleCount} article{articleCount !== 1 ? 's' : ''} analyzed
            </p>

            <div className="mt-3 flex items-center gap-2">
              <span className="text-[10px] text-danger-400">Bearish</span>
              <div className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-surface-600">
                <div
                  className="absolute top-0 h-1.5 rounded-full bg-gradient-to-r from-danger-500 via-neutral-500 to-brand-500"
                  style={{ width: '100%' }}
                />
                <div
                  className="absolute top-[-3px] h-4 w-1 rounded-full bg-white transition-all duration-700"
                  style={{ left: `${barPercent}%`, boxShadow: '0 0 6px rgba(255,255,255,0.5)' }}
                />
              </div>
              <span className="text-[10px] text-brand-400">Bullish</span>
            </div>

            {data.positive + data.negative + data.neutral > 0 && (
              <div className="mt-3 flex justify-center gap-4 text-[11px]">
                <span className="text-brand-400">+{(data.positive * 100).toFixed(0)}%</span>
                <span className="text-danger-400">-{(data.negative * 100).toFixed(0)}%</span>
                <span className="text-neutral-500">~{(data.neutral * 100).toFixed(0)}%</span>
              </div>
            )}
          </>
        ) : (
          <>
            <p className="text-3xl font-bold text-neutral-500">—</p>
            <p className="mt-1 text-xs text-neutral-500">Overall Sentiment</p>
          </>
        )}
      </div>

      <ExplanationBox
        label={data?.explanation ? 'Why this score' : 'Why this matters'}
        text={data?.explanation || 'Analyzes news headlines to extract overall sentiment trends — whether coverage is leaning positive, negative, or mixed.'}
        accentColor="#4ade80"
      />
    </AnalysisCard>
  );
}

/* ---------- Velocity Card ---------- */
function VelocityCard({ data, loading }: { data: VelocityResult | null; loading: boolean }) {
  const score = data?.score ?? 0;
  const trend = data?.trend || 'stable';
  const mentionCount = data?.mention_count ?? 0;
  const changePct = data?.change_percent ?? 0;

  const trendDisplay = trend === 'accelerating' ? 'Accelerating' : trend === 'decelerating' ? 'Decelerating' : 'Stable';
  const trendGradient = trend === 'accelerating'
    ? 'linear-gradient(135deg, #fbbf24, #f59e0b)'
    : trend === 'decelerating'
    ? 'linear-gradient(135deg, #4ade80, #22c55e)'
    : 'linear-gradient(135deg, #a3a3a3, #737373)';

  const barGradient = trend === 'accelerating'
    ? 'linear-gradient(90deg, #f59e0b, #fbbf24)'
    : trend === 'decelerating'
    ? 'linear-gradient(90deg, #22c55e, #4ade80)'
    : 'linear-gradient(90deg, #525252, #737373)';

  return (
    <AnalysisCard
      accentColor="#f59e0b"
      tooltip={data?.explanation || 'Compares article mention count in the last 24h vs the prior 24h window. A spike indicates narrative momentum — attention growing faster than the underlying news warrants.'}
    >
      <div className="mb-4 flex items-center gap-3">
        <IconBadge icon={Activity} color="#fbbf24" />
        <h3 className="font-semibold text-white">Narrative Velocity</h3>
      </div>

      <div className="mb-4 rounded-xl bg-surface-700/50 p-4 text-center">
        {loading ? (
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-warning-400" />
        ) : data ? (
          <>
            <p
              className="text-3xl font-extrabold tracking-tight"
              style={{
                background: trendGradient,
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              {trendDisplay}
            </p>
            <p className="mt-1 text-xs text-neutral-500">
              {mentionCount} article{mentionCount !== 1 ? 's' : ''} tracked
            </p>

            <div className="mt-3">
              <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-surface-600">
                <div
                  className="h-1.5 rounded-full transition-all duration-1000 ease-out"
                  style={{
                    width: `${Math.min(score, 100)}%`,
                    background: barGradient,
                    boxShadow: score > 0 ? `0 0 8px ${trend === 'accelerating' ? '#f59e0b' : '#22c55e'}40` : 'none',
                  }}
                />
              </div>
              <div className="mt-1 flex justify-between text-[10px] text-neutral-600">
                <span>Low activity</span>
                <span>High activity</span>
              </div>
            </div>

            {changePct !== 0 && (
              <p className={`mt-2 text-[11px] ${changePct > 0 ? 'text-warning-400' : 'text-brand-400'}`}>
                {changePct > 0 ? '+' : ''}{changePct.toFixed(0)}% vs previous period
              </p>
            )}
          </>
        ) : (
          <>
            <p className="text-3xl font-bold text-neutral-500">—</p>
            <p className="mt-1 text-xs text-neutral-500">Velocity Score</p>
          </>
        )}
      </div>

      <ExplanationBox
        label={data?.explanation ? 'Current trend' : 'Why this matters'}
        text={data?.explanation || 'Measures how quickly attention around this stock is changing. Identifies abnormal spikes and shifts in market focus.'}
        accentColor="#fbbf24"
      />
    </AnalysisCard>
  );
}

/* ---------- Hype Card ---------- */
function HypeCard({ data, loading }: { data: HypeResult | null; loading: boolean }) {
  const score = data?.score ?? 0;
  const level = data?.level || 'low';

  const levelDisplay = level.charAt(0).toUpperCase() + level.slice(1);

  const levelColors: Record<string, { text: string; bar: string }> = {
    extreme: { text: '#f87171', bar: 'linear-gradient(90deg, #ef4444, #f87171)' },
    high: { text: '#fbbf24', bar: 'linear-gradient(90deg, #f59e0b, #fbbf24)' },
    moderate: { text: '#facc15', bar: 'linear-gradient(90deg, #eab308, #facc15)' },
    low: { text: '#4ade80', bar: 'linear-gradient(90deg, #22c55e, #4ade80)' },
  };
  const colors = levelColors[level] || levelColors.low;
  const accentColor = level === 'extreme' || level === 'high' ? '#f59e0b' : '#22c55e';

  return (
    <AnalysisCard
      accentColor={colors.text}
      tooltip={data?.explanation || 'Three-factor model: sentiment imbalance (0–40 pts) + velocity factor (0–35 pts) + source concentration (0–25 pts). Scores above 60 flag hype-driven vs information-driven attention.'}
    >
      <div className="mb-4 flex items-center gap-3">
        <IconBadge icon={AlertTriangle} color="#fbbf24" />
        <h3 className="font-semibold text-white">Hype Risk Score</h3>
      </div>

      <div className="mb-4 rounded-xl bg-surface-700/50 p-4 text-center">
        {loading ? (
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-warning-400" />
        ) : data ? (
          <>
            <p className="text-3xl font-extrabold tracking-tight">
              <span style={{ color: colors.text }}>{score.toFixed(0)}</span>
              <span className="text-base text-neutral-500">/100</span>
            </p>
            <p className="mt-1 text-xs font-medium" style={{ color: colors.text }}>
              {levelDisplay} Risk
            </p>

            <div className="mt-3">
              <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-surface-600">
                <div
                  className="h-1.5 rounded-full transition-all duration-1000 ease-out"
                  style={{
                    width: `${Math.min(score, 100)}%`,
                    background: colors.bar,
                    boxShadow: score > 20 ? `0 0 8px ${colors.text}40` : 'none',
                  }}
                />
              </div>
              <div className="mt-1 flex justify-between text-[10px] text-neutral-600">
                <span>Info-driven</span>
                <span>Hype-driven</span>
              </div>
            </div>

            <div className="mt-3 flex justify-center gap-3 text-[10px]">
              <span className="text-neutral-500">
                Sentiment: <span className="text-neutral-300">{data.sentiment_imbalance.toFixed(0)}</span>
              </span>
              <span className="text-neutral-500">
                Velocity: <span className="text-neutral-300">{data.velocity_factor.toFixed(0)}</span>
              </span>
              <span className="text-neutral-500">
                Sources: <span className="text-neutral-300">{data.source_concentration.toFixed(0)}</span>
              </span>
            </div>
          </>
        ) : (
          <>
            <p className="text-3xl font-bold text-neutral-500">—</p>
            <p className="mt-1 text-xs text-neutral-500">Hype Risk</p>
          </>
        )}
      </div>

      <ExplanationBox
        label={data?.explanation ? 'Risk assessment' : 'Why this matters'}
        text={data?.explanation || 'Combines sentiment imbalance, mention velocity, and source diversity to flag hype-driven vs information-driven attention.'}
        accentColor={accentColor}
      />
    </AnalysisCard>
  );
}

export default function AnalysisSection({ ticker, companyName }: AnalysisSectionProps) {
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setAnalysis(null);

    fetchAnalysis(ticker, companyName || ticker)
      .then((data) => {
        if (!cancelled) setAnalysis(data);
      })
      .catch(() => {
        if (!cancelled) setAnalysis(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [ticker, companyName]);

  return (
    <div>
      <h2 className="mb-4 text-lg font-semibold text-white">
        MarketNoise Analysis —{' '}
        <span className="text-brand-400">{ticker}</span>
      </h2>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <SentimentCard data={analysis?.sentiment || null} loading={loading} />
        <VelocityCard  data={analysis?.velocity  || null} loading={loading} />
        <HypeCard      data={analysis?.hype       || null} loading={loading} />
        {loading ? (
          <div
            className="flex items-center justify-center rounded-2xl border"
            style={{ border: '1px solid rgba(255,255,255,0.06)', background: '#1a1a1a' }}
          >
            <Loader2 size={20} className="animate-spin text-white/20" />
          </div>
        ) : analysis?.pattern ? (
          <PatternCard pattern={analysis.pattern} />
        ) : null}
      </div>
    </div>
  );
}
