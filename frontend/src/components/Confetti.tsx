import { useEffect, useRef } from 'react';

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  color: string;
  size: number;
  rotation: number;
  rotationSpeed: number;
  life: number;
}

const COLORS = [
  '#22c55e', '#4ade80', '#86efac',
  '#facc15', '#fbbf24',
  '#38bdf8', '#7dd3fc',
  '#f472b6', '#fb7185',
];

function makeParticle(canvas: HTMLCanvasElement): Particle {
  return {
    x: Math.random() * canvas.width,
    y: -10,
    vx: (Math.random() - 0.5) * 6,
    vy: Math.random() * 4 + 2,
    color: COLORS[Math.floor(Math.random() * COLORS.length)],
    size: Math.random() * 7 + 4,
    rotation: Math.random() * Math.PI * 2,
    rotationSpeed: (Math.random() - 0.5) * 0.2,
    life: 1,
  };
}

interface ConfettiProps {
  active: boolean;
  onDone: () => void;
  duration?: number;
}

export default function Confetti({ active, onDone, duration = 2500 }: ConfettiProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef<number>(0);
  const particlesRef = useRef<Particle[]>([]);
  const startRef = useRef<number>(0);

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      if (active) onDone();
      return;
    }

    if (!active) return;

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    particlesRef.current = Array.from({ length: 120 }, () => makeParticle(canvas));
    startRef.current = performance.now();

    function frame(now: number) {
      if (!ctx || !canvas) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const elapsed = now - startRef.current;
      const spawnPhase = elapsed < duration * 0.4;

      if (spawnPhase && particlesRef.current.length < 200) {
        for (let i = 0; i < 3; i++) {
          particlesRef.current.push(makeParticle(canvas));
        }
      }

      particlesRef.current = particlesRef.current.filter(p => {
        p.x += p.vx;
        p.y += p.vy;
        p.vy += 0.12;
        p.rotation += p.rotationSpeed;
        p.life -= 0.008;

        if (p.y > canvas.height || p.life <= 0) return false;

        ctx.save();
        ctx.globalAlpha = p.life;
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rotation);
        ctx.fillStyle = p.color;
        ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.5);
        ctx.restore();
        return true;
      });

      if (elapsed < duration || particlesRef.current.length > 0) {
        rafRef.current = requestAnimationFrame(frame);
      } else {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        onDone();
      }
    }

    rafRef.current = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(rafRef.current);
  }, [active, duration, onDone]);

  if (!active) return null;

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none fixed inset-0 z-[9998]"
      aria-hidden="true"
    />
  );
}
