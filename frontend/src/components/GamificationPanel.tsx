import { useEffect, useRef } from 'react';
import { X, Trophy, Target, CheckCircle2, Circle, Lock } from 'lucide-react';
import { useGamification, XP_PER_LEVEL } from '../contexts/GamificationContext';

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function GamificationPanel({ open, onClose }: Props) {
  const { state } = useGamification();
  const panelRef = useRef<HTMLDivElement>(null);

  const level = Math.floor(state.xp / XP_PER_LEVEL) + 1;
  const xpInLevel = state.xp % XP_PER_LEVEL;
  const completedMissions = state.missions.filter(m => m.completed).length;
  const allDone = completedMissions === state.missions.length;

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onClose]);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) onClose();
    };
    const id = setTimeout(() => document.addEventListener('mousedown', handler), 50);
    return () => { clearTimeout(id); document.removeEventListener('mousedown', handler); };
  }, [open, onClose]);

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-[60] transition-all duration-200"
        style={{
          background: open ? 'rgba(0,0,0,0.4)' : 'transparent',
          pointerEvents: open ? 'auto' : 'none',
        }}
        aria-hidden="true"
      />

      {/* Slide-in panel */}
      <div
        ref={panelRef}
        className="fixed right-0 top-16 z-[70] flex h-[calc(100vh-4rem)] w-80 flex-col overflow-y-auto"
        style={{
          background: 'rgba(10,10,10,0.97)',
          borderLeft: '1px solid rgba(34,197,94,0.12)',
          transform: open ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 0.25s cubic-bezier(0.4,0,0.2,1)',
          backdropFilter: 'blur(20px)',
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-5 py-4"
          style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
        >
          <div className="flex items-center gap-2">
            <Trophy className="h-4 w-4 text-brand-400" />
            <span className="text-sm font-bold uppercase tracking-widest text-neutral-300">Progress</span>
          </div>
          <button
            onClick={onClose}
            className="flex h-7 w-7 items-center justify-center rounded-lg text-neutral-500 transition-colors hover:text-white"
            style={{ background: 'rgba(255,255,255,0.05)' }}
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* XP Summary */}
        <div className="px-5 py-4" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
          <div className="mb-3 flex items-baseline justify-between">
            <div>
              <span className="text-2xl font-extrabold text-white">Level {level}</span>
              <span className="ml-2 text-sm text-neutral-500">· {state.xp} XP total</span>
            </div>
            <span className="text-xs text-neutral-500">{xpInLevel}/{XP_PER_LEVEL}</span>
          </div>
          <div
            className="h-2 w-full overflow-hidden rounded-full"
            style={{ background: 'rgba(255,255,255,0.06)' }}
          >
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{
                width: `${(xpInLevel / XP_PER_LEVEL) * 100}%`,
                background: 'linear-gradient(90deg, #16a34a, #4ade80)',
                boxShadow: '0 0 8px rgba(34,197,94,0.5)',
              }}
            />
          </div>
        </div>

        {/* Missions */}
        <div className="px-5 py-4" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Target className="h-3.5 w-3.5 text-brand-400" />
              <span className="text-xs font-bold uppercase tracking-widest text-neutral-400">Missions</span>
            </div>
            <span
              className="rounded-full px-2 py-0.5 text-[10px] font-semibold"
              style={{
                background: allDone ? 'rgba(34,197,94,0.15)' : 'rgba(255,255,255,0.06)',
                color: allDone ? '#4ade80' : '#737373',
              }}
            >
              {completedMissions}/{state.missions.length}
            </span>
          </div>

          <div
            className="mb-4 h-1.5 w-full overflow-hidden rounded-full"
            style={{ background: 'rgba(255,255,255,0.06)' }}
          >
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{
                width: `${(completedMissions / state.missions.length) * 100}%`,
                background: allDone
                  ? 'linear-gradient(90deg, #16a34a, #4ade80)'
                  : 'linear-gradient(90deg, #16a34a, #22c55e)',
              }}
            />
          </div>

          {allDone && (
            <div
              className="mb-3 rounded-xl px-3 py-2.5 text-center text-sm font-semibold text-brand-300"
              style={{
                background: 'rgba(5,46,22,0.4)',
                border: '1px solid rgba(34,197,94,0.2)',
                animation: 'glow-pulse 2s ease-in-out infinite',
              }}
            >
              🎉 All missions complete!
            </div>
          )}

          <div className="space-y-2">
            {state.missions.map((m) => (
              <div
                key={m.id}
                className="flex items-center gap-3 rounded-xl px-3 py-2.5 transition-colors"
                style={{
                  background: m.completed ? 'rgba(5,46,22,0.3)' : 'rgba(26,26,26,0.6)',
                  border: m.completed ? '1px solid rgba(34,197,94,0.15)' : '1px solid rgba(255,255,255,0.04)',
                }}
              >
                <span className="text-base">{m.emoji}</span>
                <div className="min-w-0 flex-1">
                  <p
                    className="text-sm font-medium"
                    style={{ color: m.completed ? '#86efac' : '#a3a3a3' }}
                  >
                    {m.title}
                  </p>
                  <p className="truncate text-[11px] text-neutral-600">{m.description}</p>
                </div>
                <div className="shrink-0">
                  {m.completed ? (
                    <CheckCircle2 className="h-4 w-4 text-brand-500" />
                  ) : (
                    <Circle className="h-4 w-4 text-neutral-700" />
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Badges */}
        <div className="px-5 py-4">
          <div className="mb-3 flex items-center gap-2">
            <span className="text-base">🏅</span>
            <span className="text-xs font-bold uppercase tracking-widest text-neutral-400">Badges</span>
          </div>

          <div className="space-y-2">
            {state.badges.map((b) => (
              <div
                key={b.id}
                className="flex items-center gap-3 rounded-xl px-3 py-3 transition-all"
                style={{
                  background: b.unlocked ? 'rgba(5,46,22,0.35)' : 'rgba(20,20,20,0.6)',
                  border: b.unlocked
                    ? '1px solid rgba(34,197,94,0.25)'
                    : '1px solid rgba(255,255,255,0.04)',
                  opacity: b.unlocked ? 1 : 0.55,
                }}
              >
                <div
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-xl"
                  style={{
                    background: b.unlocked ? 'rgba(34,197,94,0.15)' : 'rgba(255,255,255,0.03)',
                    filter: b.unlocked ? 'none' : 'grayscale(1)',
                  }}
                >
                  {b.emoji}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <p
                      className="text-sm font-semibold"
                      style={{ color: b.unlocked ? '#e5e5e5' : '#525252' }}
                    >
                      {b.title}
                    </p>
                    {b.unlocked && (
                      <span
                        className="rounded-full px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide"
                        style={{ background: 'rgba(34,197,94,0.2)', color: '#4ade80' }}
                      >
                        Unlocked
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-neutral-600">{b.description}</p>
                </div>
                {!b.unlocked && <Lock className="h-3.5 w-3.5 shrink-0 text-neutral-700" />}
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
