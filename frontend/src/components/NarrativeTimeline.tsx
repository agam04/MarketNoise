import { useEffect, useState } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer,
} from 'recharts';
import { TrendingUp, TrendingDown, Minus, Activity, Loader2 } from 'lucide-react';
import { fetchDrift, type DriftResult, type DriftWindow } from '../services/analysisService';

interface Props {
  ticker: string;
}

type Window = '7d' | '30d' | '90d';

// ── Custom tooltip ─────────────────────────────────────────────────────────

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const val: number = payload[0]?.value ?? 0;
  const color = val >= 0.05 ? '#4ade80' : val <= -0.05 ? '#f87171' : '#94a3b8';
  const lbl = val >= 0.05 ? 'Bullish' : val <= -0.05 ? 'Bearish' : 'Neutral';
  return (
    <div className="rounded-xl border border-white/10 bg-[#1a1a1a] px-3 py-2 text-xs shadow-xl">
      <p className="mb-1 text-white/50">{label}</p>
      <p style={{ color }} className="font-semibold">
        {lbl} ({val >= 0 ? '+' : ''}{val.toFixed(3)})
      </p>
    </div>
  );
}

// ── Window stat pill ───────────────────────────────────────────────────────

function WindowStat({ label, win }: { label: string; win: DriftWindow | null }) {
  if (!win) return null;

  const dirColor =
    win.direction === 'positive' ? '#4ade80' :
    win.direction === 'negative' ? '#f87171' : '#94a3b8';

  const driftIcon =
    win.drift_direction === 'improving' ? <TrendingUp size={12} /> :
    win.drift_direction === 'worsening' ? <TrendingDown size={12} /> :
    <Minus size={12} />;

  const driftColor =
    win.drift_direction === 'improving' ? '#4ade80' :
    win.drift_direction === 'worsening' ? '#f87171' : '#94a3b8';

  return (
    <div className="flex flex-col gap-1 rounded-xl border border-white/[0.06] bg-white/[0.03] px-4 py-3">
      <span className="text-[10px] font-medium uppercase tracking-widest text-white/30">{label}</span>
      <span className="text-lg font-bold" style={{ color: dirColor }}>
        {win.avg_compound >= 0 ? '+' : ''}{win.avg_compound.toFixed(3)}
      </span>
      <span className="flex items-center gap-1 text-[11px]" style={{ color: driftColor }}>
        {driftIcon}
        {win.drift_direction}
      </span>
      <span className="text-[10px] text-white/30">{win.article_count} articles</span>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────

export default function NarrativeTimeline({ ticker }: Props) {
  const [drift, setDrift]         = useState<DriftResult | null>(null);
  const [loading, setLoading]     = useState(true);
  const [activeWindow, setActive] = useState<Window>('30d');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchDrift(ticker)
      .then(d => { if (!cancelled) { setDrift(d); setLoading(false); } })
      .catch(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [ticker]);

  // Filter timeline data to the selected window
  const timelineForWindow = (win: Window) => {
    if (!drift) return [];
    const days = win === '7d' ? 7 : win === '30d' ? 30 : 90;
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - days);
    return drift.timeline.filter(p => new Date(p.date) >= cutoff);
  };

  const points = timelineForWindow(activeWindow);

  // Compute dominant sentiment colour for the chart stroke/fill
  const windowStats = drift?.windows[activeWindow];
  const avgCompound = windowStats?.avg_compound ?? 0;
  const strokeColor = avgCompound >= 0.05 ? '#4ade80' : avgCompound <= -0.05 ? '#f87171' : '#94a3b8';

  return (
    <div
      className="rounded-2xl border p-6"
      style={{
        background: '#1a1a1a',
        borderColor: 'rgba(255,255,255,0.06)',
      }}
    >
      {/* Header */}
      <div className="mb-5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div
            className="flex h-8 w-8 items-center justify-center rounded-lg"
            style={{ background: 'radial-gradient(circle at 30% 30%, rgba(168,85,247,0.25), rgba(168,85,247,0.05))' }}
          >
            <Activity size={15} className="text-purple-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Narrative Timeline</h3>
            <p className="text-[11px] text-white/40">How the story has evolved over time</p>
          </div>
        </div>

        {/* Window selector */}
        <div className="flex gap-1 rounded-lg border border-white/[0.06] bg-white/[0.03] p-1">
          {(['7d', '30d', '90d'] as Window[]).map(w => (
            <button
              key={w}
              onClick={() => setActive(w)}
              className="rounded-md px-3 py-1 text-xs font-medium transition-all"
              style={{
                background:  activeWindow === w ? 'rgba(168,85,247,0.2)' : 'transparent',
                color:       activeWindow === w ? '#c084fc' : 'rgba(255,255,255,0.4)',
                borderColor: activeWindow === w ? 'rgba(168,85,247,0.3)' : 'transparent',
              }}
            >
              {w.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex h-48 items-center justify-center">
          <Loader2 size={20} className="animate-spin text-white/30" />
        </div>
      )}

      {/* No data yet */}
      {!loading && (!drift?.data_available || points.length === 0) && (
        <div className="flex h-48 flex-col items-center justify-center gap-3 text-center">
          <div className="rounded-full border border-white/[0.06] bg-white/[0.03] p-4">
            <Activity size={24} className="text-white/20" />
          </div>
          <div>
            <p className="text-sm font-medium text-white/50">Building narrative history</p>
            <p className="mt-1 max-w-xs text-[11px] text-white/30">
              Timeline populates as articles are scraped. Data accumulates automatically
              every 30 minutes once scrapers are running.
            </p>
          </div>
        </div>
      )}

      {/* Chart */}
      {!loading && drift?.data_available && points.length > 0 && (
        <>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={points} margin={{ top: 8, right: 4, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="sentimentGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={strokeColor} stopOpacity={0.25} />
                  <stop offset="95%" stopColor={strokeColor} stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.3)' }}
                tickLine={false}
                axisLine={false}
                tickFormatter={d => {
                  const dt = new Date(d);
                  return `${dt.getMonth() + 1}/${dt.getDate()}`;
                }}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={[-1, 1]}
                tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.3)' }}
                tickLine={false}
                axisLine={false}
                tickCount={5}
              />
              <Tooltip content={<ChartTooltip />} />
              <ReferenceLine y={0} stroke="rgba(255,255,255,0.15)" strokeDasharray="4 4" />
              <Area
                type="monotone"
                dataKey="compound"
                stroke={strokeColor}
                strokeWidth={2}
                fill="url(#sentimentGrad)"
                dot={false}
                activeDot={{ r: 4, fill: strokeColor, stroke: '#1a1a1a', strokeWidth: 2 }}
              />
            </AreaChart>
          </ResponsiveContainer>

          {/* Window stats row */}
          <div className="mt-4 grid grid-cols-3 gap-3">
            <WindowStat label="7 Days"  win={drift.windows['7d']}  />
            <WindowStat label="30 Days" win={drift.windows['30d']} />
            <WindowStat label="90 Days" win={drift.windows['90d']} />
          </div>

          {/* Shift detection */}
          {drift.shift.detected && (
            <div
              className="mt-4 flex items-start gap-3 rounded-xl border px-4 py-3"
              style={{ borderColor: 'rgba(168,85,247,0.2)', background: 'rgba(168,85,247,0.05)' }}
            >
              <div className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-purple-400" />
              <p className="text-xs text-white/70">
                <span className="font-medium text-purple-300">Shift detected — </span>
                {drift.shift.description}
              </p>
            </div>
          )}

          {!drift.shift.detected && (
            <div
              className="mt-4 flex items-start gap-3 rounded-xl border px-4 py-3"
              style={{ borderColor: 'rgba(255,255,255,0.05)', background: 'rgba(255,255,255,0.02)' }}
            >
              <div className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-white/20" />
              <p className="text-[11px] text-white/40">{drift.shift.description}</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
