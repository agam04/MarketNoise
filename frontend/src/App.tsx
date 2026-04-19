import { useEffect, useRef } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { GamificationProvider, useGamification } from './contexts/GamificationContext';
import Navbar from './components/Navbar';
import HomePage from './pages/HomePage';
import StockPage from './pages/StockPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import SettingsPage from './pages/SettingsPage';
import WatchlistPage from './pages/WatchlistPage';
import XPToastContainer from './components/XPToast';
import Confetti from './components/Confetti';

/** Subtle green radial glow that follows the cursor — adds depth without distraction */
function CursorSpotlight() {
  const spotRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = spotRef.current;
    if (!el) return;
    const onMove = (e: MouseEvent) => {
      el.style.transform = `translate(${e.clientX - 300}px, ${e.clientY - 300}px)`;
    };
    window.addEventListener('mousemove', onMove);
    return () => window.removeEventListener('mousemove', onMove);
  }, []);

  return (
    <div
      ref={spotRef}
      className="pointer-events-none fixed left-0 top-0 z-0 h-[600px] w-[600px] rounded-full"
      style={{
        background: 'radial-gradient(circle, rgba(34,197,94,0.07) 0%, rgba(34,197,94,0.02) 40%, transparent 70%)',
        filter: 'blur(32px)',
        transition: 'transform 0.12s ease-out',
        willChange: 'transform',
      }}
    />
  );
}

/** Must be inside GamificationProvider to access context */
function GamificationLayer() {
  const { state, stopConfetti, gamificationEnabled } = useGamification();
  if (!gamificationEnabled) return null;
  return (
    <>
      <Confetti active={state.confetti} onDone={stopConfetti} />
      <XPToastContainer />
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <GamificationProvider>
          <div className="relative min-h-screen w-full overflow-x-hidden bg-surface-900 text-neutral-200">
            <CursorSpotlight />
            <div className="relative z-10">
              <Navbar />
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/stock/:ticker" element={<StockPage />} />
                <Route path="/watchlist" element={<WatchlistPage />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />
                <Route path="/settings" element={<SettingsPage />} />
              </Routes>
            </div>
            <GamificationLayer />
          </div>
        </GamificationProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
