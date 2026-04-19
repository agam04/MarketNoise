import { useEffect, useRef } from 'react';
import { useGamification } from '../contexts/GamificationContext';
import type { XPToast as XPToastItem, BadgeToast } from '../contexts/GamificationContext';

function XPBubble({ toast, onDone }: { toast: XPToastItem; onDone: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDone, 1800);
    return () => clearTimeout(t);
  }, [onDone]);

  return (
    <div
      className="pointer-events-none flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-bold text-white shadow-lg"
      style={{
        background: 'linear-gradient(135deg, #16a34a, #15803d)',
        boxShadow: '0 0 16px rgba(34,197,94,0.4)',
        animation: 'xp-toast-in 1.8s ease forwards',
      }}
    >
      <span style={{ color: '#86efac' }}>+{toast.amount}</span>
      <span className="text-xs font-semibold text-white/80">XP</span>
    </div>
  );
}

function BadgeBubble({ badge, onDone }: { badge: BadgeToast; onDone: () => void }) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    timerRef.current = setTimeout(onDone, 3500);
    return () => clearTimeout(timerRef.current);
  }, [onDone]);

  return (
    <div
      className="pointer-events-auto flex cursor-pointer items-center gap-3 rounded-xl px-4 py-3 shadow-xl"
      style={{
        background: 'rgba(5,46,22,0.95)',
        border: '1px solid rgba(34,197,94,0.4)',
        boxShadow: '0 0 24px rgba(34,197,94,0.2)',
        animation: 'xp-toast-in 3.5s ease forwards',
        backdropFilter: 'blur(12px)',
      }}
      onClick={onDone}
    >
      <span className="text-2xl">{badge.emoji}</span>
      <div>
        <p className="text-[10px] font-bold uppercase tracking-widest text-brand-400">Badge Unlocked!</p>
        <p className="text-sm font-semibold text-white">{badge.title}</p>
      </div>
    </div>
  );
}

export default function XPToastContainer() {
  const { state, dismissToast, dismissBadgeToast } = useGamification();

  return (
    <div
      className="pointer-events-none fixed bottom-6 right-6 z-[9999] flex flex-col items-end gap-2"
      aria-live="polite"
    >
      {state.toasts.map((t) => (
        <XPBubble key={t.id} toast={t} onDone={() => dismissToast(t.id)} />
      ))}
      {state.badgeToast && (
        <BadgeBubble badge={state.badgeToast} onDone={dismissBadgeToast} />
      )}
    </div>
  );
}
