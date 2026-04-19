import { useState, useEffect } from 'react';
import { useGamification } from '../contexts/GamificationContext';
import { Zap, CheckCircle2, XCircle } from 'lucide-react';

interface Option {
  id: string;
  text: string;
}

interface Challenge {
  question: string;
  options: Option[];
  correctId: string;
  explanation: string;
}

const CHALLENGE: Challenge = {
  question: 'What does a high "Hype Score" in MarketNoise typically indicate?',
  options: [
    { id: 'a', text: 'The stock has strong fundamental value' },
    { id: 'b', text: 'There is elevated social media chatter relative to price action' },
    { id: 'c', text: 'Institutional investors are buying heavily' },
    { id: 'd', text: 'The company recently reported earnings' },
  ],
  correctId: 'b',
  explanation:
    "A high Hype Score reflects disproportionate social & news volume relative to the stock's actual price movement — a signal to watch for narrative-driven volatility.",
};

export default function DailyChallenge() {
  const { onCompleteChallenge } = useGamification();
  const [selected, setSelected] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  const isCorrect = selected === CHALLENGE.correctId;

  function handleSubmit() {
    if (!selected || submitted) return;
    setSubmitted(true);
    if (isCorrect) onCompleteChallenge();
  }

  useEffect(() => {
    if (!submitted) return;
    const t = setTimeout(() => setDismissed(true), 2500);
    return () => clearTimeout(t);
  }, [submitted]);

  if (dismissed) return null;

  return (
    <div
      className="w-full rounded-2xl p-5"
      style={{
        background: 'rgba(26,26,26,0.7)',
        border: '1px solid rgba(34,197,94,0.12)',
      }}
    >
      {/* Header */}
      <div className="mb-4 flex items-center gap-2.5">
        <div
          className="flex h-8 w-8 items-center justify-center rounded-lg"
          style={{ background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.2)' }}
        >
          <Zap className="h-4 w-4 text-brand-400" />
        </div>
        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest text-brand-400">Daily Challenge</p>
          <p className="text-[11px] text-neutral-600">+50 XP for correct answer · resets on refresh</p>
        </div>
      </div>

      {/* Question */}
      <p className="mb-4 text-sm font-medium leading-relaxed text-neutral-200">
        {CHALLENGE.question}
      </p>

      {/* Options */}
      <div className="space-y-2">
        {CHALLENGE.options.map((opt) => {
          const isSelected = selected === opt.id;
          const isCorrectOpt = opt.id === CHALLENGE.correctId;

          let borderColor = 'rgba(255,255,255,0.07)';
          let bg = 'rgba(26,26,26,0.5)';
          let textColor = '#a3a3a3';

          if (submitted) {
            if (isCorrectOpt) {
              borderColor = 'rgba(34,197,94,0.4)';
              bg = 'rgba(5,46,22,0.4)';
              textColor = '#86efac';
            } else if (isSelected && !isCorrectOpt) {
              borderColor = 'rgba(239,68,68,0.4)';
              bg = 'rgba(69,10,10,0.4)';
              textColor = '#fca5a5';
            }
          } else if (isSelected) {
            borderColor = 'rgba(34,197,94,0.3)';
            bg = 'rgba(5,46,22,0.25)';
            textColor = '#e5e5e5';
          }

          return (
            <button
              key={opt.id}
              onClick={() => !submitted && setSelected(opt.id)}
              disabled={submitted}
              className="w-full rounded-xl px-4 py-2.5 text-left text-sm transition-all duration-150 disabled:cursor-default"
              style={{ background: bg, border: `1px solid ${borderColor}`, color: textColor }}
              onMouseEnter={(e) => {
                if (!submitted && !isSelected)
                  (e.currentTarget as HTMLElement).style.borderColor = 'rgba(34,197,94,0.2)';
              }}
              onMouseLeave={(e) => {
                if (!submitted && !isSelected)
                  (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.07)';
              }}
            >
              <span className="mr-2 font-bold text-neutral-600">{opt.id.toUpperCase()}.</span>
              {opt.text}
            </button>
          );
        })}
      </div>

      {/* Result */}
      {submitted && (
        <div
          className="mt-4 rounded-xl px-4 py-3"
          style={{
            background: isCorrect ? 'rgba(5,46,22,0.35)' : 'rgba(69,10,10,0.35)',
            border: isCorrect ? '1px solid rgba(34,197,94,0.2)' : '1px solid rgba(239,68,68,0.2)',
            animation: 'fade-up 0.3s ease-out forwards',
          }}
        >
          <div className="flex items-center gap-2">
            {isCorrect ? (
              <>
                <CheckCircle2 className="h-4 w-4 text-brand-400" />
                <span className="text-sm font-semibold text-brand-300">Correct! +50 XP earned</span>
              </>
            ) : (
              <>
                <XCircle className="h-4 w-4 text-danger-400" />
                <span className="text-sm font-semibold text-danger-400">Not quite — the answer was B</span>
              </>
            )}
          </div>
        </div>
      )}

      {/* Submit button */}
      {!submitted && (
        <button
          onClick={handleSubmit}
          disabled={!selected}
          className="mt-4 w-full rounded-xl py-2.5 text-sm font-semibold transition-all"
          style={{
            background: selected ? 'linear-gradient(135deg, #16a34a, #15803d)' : 'rgba(255,255,255,0.04)',
            color: selected ? '#fff' : '#525252',
            border: selected ? 'none' : '1px solid rgba(255,255,255,0.06)',
            boxShadow: selected ? '0 0 16px rgba(34,197,94,0.2)' : 'none',
          }}
        >
          Submit Answer
        </button>
      )}
    </div>
  );
}
