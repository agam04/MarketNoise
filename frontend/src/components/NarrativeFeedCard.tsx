import { Link } from 'react-router-dom';
import { TrendingUp, TrendingDown, Minus, Zap, Activity } from 'lucide-react';
import type { TrendingItem } from '../services/analysisService';

const HYPE_CONFIG = {
  extreme: { label: 'Extreme Hype', bg: 'rgba(239,68,68,0.12)',  border: 'rgba(239,68,68,0.25)',  text: '#f87171' },
  high:    { label: 'High Hype',    bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.25)', text: '#fbbf24' },
  moderate:{ label: 'Moderate',     bg: 'rgba(96,165,250,0.12)', border: 'rgba(96,165,250,0.25)', text: '#93c5fd' },
  low:     { label: 'Low Hype',     bg: 'rgba(34,197,94,0.12)',  border: 'rgba(34,197,94,0.25)',  text: '#86efac' },
};

const VELOCITY_CONFIG = {
  accelerating: { icon: TrendingUp,   color: '#fbbf24', label: 'Accelerating' },
  decelerating: { icon: TrendingDown, color: '#4ade80', label: 'Cooling' },
  stable:       { icon: Minus,        color: '#6b7280', label: 'Stable' },
};

const SENTIMENT_GRADIENT: Record<string, string> = {
  positive: 'linear-gradient(135deg, #4ade80, #22c55e)',
  negative: 'linear-gradient(135deg, #f87171, #ef4444)',
  neutral:  'linear-gradient(135deg, #a3a3a3, #737373)',
};

interface Props {
  item: TrendingItem;
  rank: number;
}

export default function NarrativeFeedCard({ item, rank }: Props) {
  const hype = HYPE_CONFIG[item.hype_level] ?? HYPE_CONFIG.low;
  const vel  = VELOCITY_CONFIG[item.velocity_trend] ?? VELOCITY_CONFIG.stable;
  const VelIcon = vel.icon;

  const sentimentDisplay =
    item.sentiment_label === 'positive' ? 'Bullish'
    : item.sentiment_label === 'negative' ? 'Bearish'
    : 'Neutral';

  const compoundSign = item.compound >= 0 ? '+' : '';

  return (
    <Link
      to={`/stock/${item.ticker}`}
      className="group block no-underline"
      style={{ textDecoration: 'none' }}
    >
      <div
        className="relative overflow-hidden rounded-2xl p-5 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-xl"
        style={{
          background: '#1a1a1a',
          border: '1px solid rgba(255,255,255,0.06)',
          borderTopColor: item.pattern.color,
          borderTopWidth: 2,
          boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
        }}
      >
        {/* Subtle hover glow using pattern color */}
        <div
          className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100 rounded-2xl"
          style={{
            background: `radial-gradient(circle at 50% 0%, ${item.pattern.color}08, transparent 60%)`,
          }}
        />

        {/* Header: rank + ticker + hype badge */}
        <div className="mb-3 flex items-start justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <span className="text-[11px] font-mono text-white/20 tabular-nums w-4">
              {rank}
            </span>
            <div>
              <p className="text-base font-extrabold tracking-tight text-white leading-none">
                {item.ticker}
              </p>
              <p className="mt-0.5 text-[11px] text-white/40 leading-none truncate max-w-[120px]">
                {item.name}
              </p>
            </div>
          </div>

          <span
            className="shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
            style={{ background: hype.bg, color: hype.text, border: `1px solid ${hype.border}` }}
          >
            {hype.label}
          </span>
        </div>

        {/* Pattern badge */}
        <div className="mb-3 flex items-center gap-2">
          <div
            className="flex h-6 w-6 items-center justify-center rounded-md text-xs shrink-0"
            style={{ background: `${item.pattern.color}18` }}
          >
            {PATTERN_ICON[item.pattern.id] ?? '◈'}
          </div>
          <p className="text-xs font-semibold" style={{ color: item.pattern.color }}>
            {item.pattern.name}
          </p>
        </div>

        {/* Divider */}
        <div className="mb-3 h-px" style={{ background: 'rgba(255,255,255,0.05)' }} />

        {/* Signal row: sentiment + velocity */}
        <div className="flex items-center justify-between gap-2">
          {/* Sentiment */}
          <div className="flex items-center gap-1.5">
            <Activity size={11} style={{ color: '#6b7280' }} />
            <span
              className="text-xs font-semibold"
              style={{
                background: SENTIMENT_GRADIENT[item.sentiment_label] ?? SENTIMENT_GRADIENT.neutral,
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              {sentimentDisplay}
            </span>
            <span className="text-[10px] text-white/25 tabular-nums">
              ({compoundSign}{item.compound.toFixed(2)})
            </span>
          </div>

          {/* Velocity */}
          <div className="flex items-center gap-1" style={{ color: vel.color }}>
            <VelIcon size={11} />
            <span className="text-[10px] font-medium">{vel.label}</span>
          </div>
        </div>

        {/* Hype score bar */}
        <div className="mt-3">
          <div className="flex justify-between mb-1 text-[10px] text-white/25">
            <span className="flex items-center gap-1">
              <Zap size={9} />
              Hype {item.hype_score.toFixed(0)}/100
            </span>
            <span>{item.article_count} article{item.article_count !== 1 ? 's' : ''}</span>
          </div>
          <div className="h-1 w-full overflow-hidden rounded-full bg-white/[0.06]">
            <div
              className="h-1 rounded-full transition-all duration-700"
              style={{
                width: `${Math.min(item.hype_score, 100)}%`,
                background:
                  item.hype_level === 'extreme' ? 'linear-gradient(90deg, #ef4444, #f87171)' :
                  item.hype_level === 'high'    ? 'linear-gradient(90deg, #f59e0b, #fbbf24)' :
                  item.hype_level === 'moderate'? 'linear-gradient(90deg, #3b82f6, #60a5fa)' :
                                                  'linear-gradient(90deg, #22c55e, #4ade80)',
              }}
            />
          </div>
        </div>
      </div>
    </Link>
  );
}

const PATTERN_ICON: Record<string, string> = {
  short_squeeze:     '🔥',
  macro_fear:        '⚠️',
  theme_hype:        '🌊',
  narrative_cooloff: '❄️',
  pre_catalyst:      '📊',
  balanced_coverage: '✓',
};
