import type { PatternResult } from '../services/analysisService';

interface Props {
  pattern: PatternResult;
}

const RISK_CONFIG = {
  extreme: { label: 'Extreme Risk',  bg: 'rgba(239,68,68,0.12)',  border: 'rgba(239,68,68,0.25)',  text: '#fca5a5' },
  high:    { label: 'High Risk',     bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.25)', text: '#fcd34d' },
  moderate:{ label: 'Moderate',      bg: 'rgba(96,165,250,0.12)', border: 'rgba(96,165,250,0.25)', text: '#93c5fd' },
  low:     { label: 'Low Risk',      bg: 'rgba(34,197,94,0.12)',  border: 'rgba(34,197,94,0.25)',  text: '#86efac' },
};

const PATTERN_ICONS: Record<string, string> = {
  short_squeeze:     '🔥',
  macro_fear:        '⚠️',
  theme_hype:        '🌊',
  narrative_cooloff: '❄️',
  pre_catalyst:      '📊',
  balanced_coverage: '✓',
};

export default function PatternCard({ pattern }: Props) {
  const risk   = RISK_CONFIG[pattern.risk] ?? RISK_CONFIG.low;
  const icon   = PATTERN_ICONS[pattern.id] ?? '◈';

  return (
    <div
      className="flex h-full flex-col rounded-2xl border p-5"
      style={{
        background:   '#1a1a1a',
        borderColor:  'rgba(255,255,255,0.06)',
        borderTopColor: pattern.color,
        borderTopWidth: 2,
      }}
    >
      {/* Header row */}
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          {/* Icon badge */}
          <div
            className="flex h-9 w-9 items-center justify-center rounded-lg text-base shrink-0"
            style={{ background: `${pattern.color}18` }}
          >
            {icon}
          </div>
          <div>
            <p className="text-[10px] font-medium uppercase tracking-widest text-white/30">
              Narrative Pattern
            </p>
            <h4 className="text-sm font-semibold leading-tight text-white">
              {pattern.name}
            </h4>
          </div>
        </div>

        {/* Risk badge */}
        <span
          className="shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
          style={{ background: risk.bg, color: risk.text, border: `1px solid ${risk.border}` }}
        >
          {risk.label}
        </span>
      </div>

      {/* Description */}
      <p className="mb-4 flex-1 text-[12px] leading-relaxed text-white/55">
        {pattern.description}
      </p>

      {/* Signals matched */}
      <div>
        <p className="mb-2 text-[10px] font-medium uppercase tracking-widest text-white/25">
          Signals detected
        </p>
        <div className="flex flex-wrap gap-1.5">
          {pattern.signals_matched.map(sig => (
            <span
              key={sig}
              className="rounded-full px-2 py-0.5 text-[11px]"
              style={{
                background: `${pattern.color}14`,
                color:      pattern.color,
                border:     `1px solid ${pattern.color}30`,
              }}
            >
              {sig}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
