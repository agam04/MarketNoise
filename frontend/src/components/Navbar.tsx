import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { BarChart3, Home, Settings, LogIn, LogOut, Bookmark, Trophy, Gamepad2 } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useGamification, XP_PER_LEVEL } from '../contexts/GamificationContext';
import GamificationPanel from './GamificationPanel';

export default function Navbar() {
  const location = useLocation();
  const { isAuthenticated, user, logout } = useAuth();
  const { state, gamificationEnabled, toggleGameMode } = useGamification();
  const isHome = location.pathname === '/';
  const [panelOpen, setPanelOpen] = useState(false);

  const level = Math.floor(state.xp / XP_PER_LEVEL) + 1;
  const xpInLevel = state.xp % XP_PER_LEVEL;
  const xpProgress = (xpInLevel / XP_PER_LEVEL) * 100;
  const completedMissions = state.missions.filter(m => m.completed).length;

  return (
    <>
      <nav
        className="sticky top-0 z-50 bg-surface-950/80 backdrop-blur-xl"
        style={{ borderBottom: '1px solid rgba(34,197,94,0.08)' }}
      >
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
          <Link to="/" className="group flex items-center gap-2.5 no-underline">
            <BarChart3
              className="h-7 w-7 text-brand-500 transition-all group-hover:text-brand-400"
              style={{ filter: 'drop-shadow(0 0 0px rgba(34,197,94,0))' }}
              onMouseEnter={(e) => { e.currentTarget.style.filter = 'drop-shadow(0 0 8px rgba(34,197,94,0.5))'; }}
              onMouseLeave={(e) => { e.currentTarget.style.filter = 'drop-shadow(0 0 0px rgba(34,197,94,0))'; }}
            />
            <span className="text-xl font-bold tracking-tight">
              <span className="text-white">Market</span>
              <span className="text-brand-400">Noise</span>
            </span>
          </Link>

          <div className="flex items-center gap-1">
            <Link
              to="/"
              className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium no-underline transition-all ${
                isHome
                  ? 'bg-brand-900/40 text-brand-400'
                  : 'text-neutral-400 hover:bg-surface-800 hover:text-white'
              }`}
            >
              <Home className="h-4 w-4" />
              Home
            </Link>

            {isAuthenticated ? (
              <>
                <Link
                  to="/watchlist"
                  className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium no-underline transition-all ${
                    location.pathname === '/watchlist'
                      ? 'bg-brand-900/40 text-brand-400'
                      : 'text-neutral-400 hover:bg-surface-800 hover:text-white'
                  }`}
                >
                  <Bookmark className="h-4 w-4" />
                  Watchlist
                </Link>
                <Link
                  to="/settings"
                  className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium no-underline transition-all ${
                    location.pathname === '/settings'
                      ? 'bg-brand-900/40 text-brand-400'
                      : 'text-neutral-400 hover:bg-surface-800 hover:text-white'
                  }`}
                >
                  <Settings className="h-4 w-4" />
                  Settings
                </Link>
                <div className="mx-1 h-4 w-px bg-neutral-800" />
                <span className="px-2 text-sm text-neutral-500">{user?.username}</span>
                <button
                  onClick={logout}
                  className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-neutral-400 transition-all hover:bg-surface-800 hover:text-white"
                >
                  <LogOut className="h-4 w-4" />
                  Logout
                </button>
              </>
            ) : (
              <Link
                to="/login"
                className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-neutral-400 no-underline transition-all hover:bg-surface-800 hover:text-white"
              >
                <LogIn className="h-4 w-4" />
                Sign in
              </Link>
            )}

            {/* XP chip / game-mode toggle */}
            <div className="mx-1 h-4 w-px bg-neutral-800" />

            {gamificationEnabled ? (
              <>
                <button
                  onClick={() => setPanelOpen(v => !v)}
                  className="btn-press flex items-center gap-2 rounded-lg px-3 py-1.5 transition-all"
                  style={{
                    background: panelOpen ? 'rgba(5,46,22,0.4)' : 'rgba(26,26,26,0.8)',
                    border: panelOpen ? '1px solid rgba(34,197,94,0.35)' : '1px solid rgba(255,255,255,0.07)',
                  }}
                  title="View missions & badges"
                >
                  <Trophy className="h-3.5 w-3.5 text-brand-400" />
                  <div className="flex flex-col items-start gap-0.5">
                    <div className="flex items-center gap-1.5">
                      <span className="text-[11px] font-bold text-brand-300">Lv {level}</span>
                      <span className="text-[10px] text-neutral-500">{state.xp} XP</span>
                      {completedMissions > 0 && (
                        <span
                          className="rounded-full px-1 py-0.5 text-[9px] font-bold"
                          style={{ background: 'rgba(34,197,94,0.2)', color: '#4ade80' }}
                        >
                          {completedMissions}/{state.missions.length}
                        </span>
                      )}
                    </div>
                    <div
                      className="w-16 overflow-hidden rounded-full"
                      style={{ height: '3px', background: 'rgba(255,255,255,0.08)' }}
                    >
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{
                          width: `${xpProgress}%`,
                          background: 'linear-gradient(90deg, #16a34a, #4ade80)',
                        }}
                      />
                    </div>
                  </div>
                </button>
                {/* Disable game mode */}
                <button
                  onClick={toggleGameMode}
                  className="flex h-7 w-7 items-center justify-center rounded-lg text-neutral-600 transition-all hover:text-neutral-300"
                  style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}
                  title="Disable game mode"
                >
                  <Gamepad2 className="h-3.5 w-3.5" />
                </button>
              </>
            ) : (
              <button
                onClick={toggleGameMode}
                className="btn-press flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[11px] text-neutral-500 transition-all hover:text-neutral-300"
                style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}
                title="Enable game mode"
              >
                <Gamepad2 className="h-3.5 w-3.5" />
                Game
              </button>
            )}
          </div>
        </div>
      </nav>

      <GamificationPanel open={panelOpen} onClose={() => setPanelOpen(false)} />
    </>
  );
}
