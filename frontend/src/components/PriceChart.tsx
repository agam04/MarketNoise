import { useState, useEffect, useCallback } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { Loader2 } from 'lucide-react';
import { TIME_RANGES, type TimeRange } from '../utils/constants';
import { fetchChartData } from '../services/stockService';
import type { PricePoint } from '../types/stock';

export interface PriceChange {
  change: number;
  changePercent: number;
  currentPrice: number;
  rangeLabel: string;
}

interface PriceChartProps {
  ticker: string;
  initialPoints?: PricePoint[];
  initialLoading?: boolean;
  onRangeChange?: (priceChange: PriceChange) => void;
}

export default function PriceChart({ ticker, initialPoints = [], initialLoading = false, onRangeChange }: PriceChartProps) {
  const [activeRange, setActiveRange] = useState<TimeRange>('1D');
  const [data, setData] = useState<PricePoint[]>(initialPoints);
  const [loading, setLoading] = useState(initialLoading);
  const [error, setError] = useState<string | null>(null);

  // Compute and report price change from chart data
  const reportChange = useCallback((points: PricePoint[], range: TimeRange) => {
    if (!onRangeChange || points.length < 2) return;
    const startPrice = points[0].price;
    const endPrice = points[points.length - 1].price;
    const change = endPrice - startPrice;
    const changePercent = startPrice !== 0 ? (change / startPrice) * 100 : 0;
    const labels: Record<TimeRange, string> = { '1D': 'Today', '7D': 'Past Week', '1M': 'Past Month', '3M': 'Past 3 Months' };
    onRangeChange({ change, changePercent, currentPrice: endPrice, rangeLabel: labels[range] });
  }, [onRangeChange]);

  // Sync initial data from parent (for the default 1D range)
  useEffect(() => {
    if (activeRange === '1D' && initialPoints.length > 0) {
      setData(initialPoints);
      setLoading(false);
      reportChange(initialPoints, '1D');
    }
  }, [initialPoints, activeRange, reportChange]);

  // Fetch new data when user changes time range (skip 1D since parent already fetched it)
  useEffect(() => {
    if (activeRange === '1D') return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchChartData(ticker, activeRange)
      .then(({ points }) => {
        if (!cancelled) {
          setData(points);
          reportChange(points, activeRange);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [ticker, activeRange, reportChange]);

  const hasData = data.length > 0;

  return (
    <div className="gradient-border p-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Price History</h2>
        <div className="flex gap-1 rounded-xl bg-surface-900/80 p-1">
          {TIME_RANGES.map((range) => (
            <button
              key={range}
              onClick={() => setActiveRange(range)}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-all duration-200 ${
                activeRange === range
                  ? 'bg-brand-600 text-white'
                  : 'text-neutral-500 hover:text-neutral-300'
              }`}
              style={activeRange === range ? { boxShadow: '0 0 12px rgba(34,197,94,0.3)' } : {}}
            >
              {range}
            </button>
          ))}
        </div>
      </div>

      <div className="h-64">
        {loading || initialLoading ? (
          <div className="flex h-full items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-brand-500" />
          </div>
        ) : error || !hasData ? (
          <div className="flex h-full flex-col items-center justify-center text-neutral-500">
            <div className="mb-3 h-16 w-full max-w-md rounded-lg bg-surface-700/50" />
            <p className="mt-3 text-sm">
              {error
                ? `Could not load price data — ${error}`
                : `No price data available for ${ticker}.`}
            </p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <defs>
                <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#22c55e" stopOpacity={0.5} />
                  <stop offset="60%" stopColor="#22c55e" stopOpacity={0.1} />
                  <stop offset="100%" stopColor="#22c55e" stopOpacity={0} />
                </linearGradient>
                <filter id="lineGlow">
                  <feGaussianBlur stdDeviation="3" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
              <XAxis dataKey="date" stroke="#404040" tick={{ fontSize: 11, fill: '#525252' }} />
              <YAxis
                stroke="#404040"
                tick={{ fontSize: 11, fill: '#525252' }}
                domain={['auto', 'auto']}
                tickFormatter={(v: number) => `$${v}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(15,15,15,0.95)',
                  border: '1px solid rgba(34,197,94,0.2)',
                  borderTop: '2px solid #22c55e',
                  borderRadius: '10px',
                  color: '#e5e5e5',
                  backdropFilter: 'blur(8px)',
                  boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
                  padding: '8px 12px',
                }}
                formatter={(value: number | undefined) => value != null ? [`$${value.toFixed(2)}`, 'Price'] : ['—', 'Price']}
                labelStyle={{ color: '#737373', fontSize: '11px', marginBottom: '2px' }}
              />
              <Area
                type="monotone"
                dataKey="price"
                stroke="#4ade80"
                strokeWidth={2.5}
                fill="url(#priceGradient)"
                filter="url(#lineGlow)"
                dot={false}
                activeDot={{ r: 4, fill: '#4ade80', stroke: '#052e16', strokeWidth: 2 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
