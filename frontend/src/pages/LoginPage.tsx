import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { LogIn } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

export default function LoginPage() {
  const { login, isLoading } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    try {
      await login(username, password);
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Login failed');
    }
  }

  return (
    <div className="flex min-h-[80vh] items-center justify-center px-4">
      <div
        className="w-full max-w-sm rounded-2xl p-8"
        style={{
          background: 'rgba(26,26,26,0.7)',
          border: '1px solid rgba(255,255,255,0.06)',
        }}
      >
        <div className="mb-6 text-center">
          <div
            className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl"
            style={{
              background: 'radial-gradient(circle, rgba(34,197,94,0.2), rgba(34,197,94,0.05))',
              border: '1px solid rgba(34,197,94,0.25)',
            }}
          >
            <LogIn className="h-6 w-6 text-brand-400" />
          </div>
          <h1 className="text-xl font-bold text-white">Sign in</h1>
          <p className="mt-1 text-sm text-neutral-500">Access your MarketNoise account</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="rounded-lg bg-red-500/10 px-4 py-2 text-sm text-red-400"
              style={{ border: '1px solid rgba(239,68,68,0.2)' }}>
              {error}
            </div>
          )}

          <div>
            <label className="mb-1 block text-xs font-medium text-neutral-400">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className="w-full rounded-lg px-3 py-2.5 text-sm text-white outline-none transition-all focus:ring-1 focus:ring-brand-600/50"
              style={{
                background: 'rgba(15,15,15,0.8)',
                border: '1px solid rgba(255,255,255,0.08)',
              }}
              placeholder="Enter your username"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-neutral-400">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full rounded-lg px-3 py-2.5 text-sm text-white outline-none transition-all focus:ring-1 focus:ring-brand-600/50"
              style={{
                background: 'rgba(15,15,15,0.8)',
                border: '1px solid rgba(255,255,255,0.08)',
              }}
              placeholder="Enter your password"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full rounded-lg bg-brand-600 py-2.5 text-sm font-semibold text-white transition-all hover:bg-brand-700 disabled:opacity-50"
            style={{ boxShadow: '0 0 20px rgba(34,197,94,0.15)' }}
          >
            {isLoading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-neutral-500">
          Don't have an account?{' '}
          <Link to="/register" className="text-brand-400 hover:text-brand-300">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
