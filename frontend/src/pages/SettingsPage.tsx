import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Settings, Key, Plus, Trash2, Check, ExternalLink } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { getApiKeys, saveApiKey, deleteApiKey } from '../services/authService';
import type { ApiKeyInfo } from '../services/authService';

const SERVICES = [
  {
    id: 'gemini',
    label: 'Google Gemini',
    description: 'AI Chat option (requires billing on Google)',
    getKeyUrl: 'https://aistudio.google.com/apikey',
    getKeyLabel: 'Get key from Google AI Studio',
  },
  {
    id: 'groq',
    label: 'Groq (Llama 3.3 70B)',
    description: 'AI Chat option — free, no credit card needed',
    getKeyUrl: 'https://console.groq.com/keys',
    getKeyLabel: 'Get free key from Groq Console',
  },
  {
    id: 'twelvedata',
    label: 'Twelve Data',
    description: 'Stock prices and charts (800 req/day free)',
    getKeyUrl: 'https://twelvedata.com/account/api-keys',
    getKeyLabel: 'Get free key from Twelve Data',
  },
  {
    id: 'gnews',
    label: 'GNews',
    description: 'News article scraping (100 req/day free)',
    getKeyUrl: 'https://gnews.io/dashboard',
    getKeyLabel: 'Get free key from GNews',
  },
  {
    id: 'reddit_id',
    label: 'Reddit Client ID',
    description: 'Reddit scraping (create a "script" app)',
    getKeyUrl: 'https://www.reddit.com/prefs/apps',
    getKeyLabel: 'Create app at Reddit',
  },
  {
    id: 'reddit_secret',
    label: 'Reddit Client Secret',
    description: 'Reddit scraping (from same app above)',
    getKeyUrl: 'https://www.reddit.com/prefs/apps',
    getKeyLabel: 'Create app at Reddit',
  },
];

export default function SettingsPage() {
  const { isAuthenticated, user, getAccessToken } = useAuth();
  const navigate = useNavigate();
  const [keys, setKeys] = useState<ApiKeyInfo[]>([]);
  const [editing, setEditing] = useState<string | null>(null);
  const [newKeyValue, setNewKeyValue] = useState('');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }
    loadKeys();
  }, [isAuthenticated]);

  async function loadKeys() {
    const token = await getAccessToken();
    if (!token) return;
    const data = await getApiKeys(token);
    setKeys(data);
  }

  async function handleSave(service: string) {
    if (!newKeyValue.trim()) return;
    setSaving(true);
    try {
      const token = await getAccessToken();
      if (!token) return;
      await saveApiKey(token, service, newKeyValue.trim());
      setEditing(null);
      setNewKeyValue('');
      setSaved(service);
      setTimeout(() => setSaved(null), 2000);
      await loadKeys();
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(service: string) {
    const token = await getAccessToken();
    if (!token) return;
    await deleteApiKey(token, service);
    await loadKeys();
  }

  function getExistingKey(service: string): ApiKeyInfo | undefined {
    return keys.find((k) => k.service === service);
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <div className="mb-8 flex items-center gap-3">
        <div
          className="flex h-10 w-10 items-center justify-center rounded-xl"
          style={{
            background: 'radial-gradient(circle, rgba(34,197,94,0.2), rgba(34,197,94,0.05))',
            border: '1px solid rgba(34,197,94,0.25)',
          }}
        >
          <Settings className="h-5 w-5 text-brand-400" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white">Settings</h1>
          <p className="text-sm text-neutral-500">Signed in as {user?.username}</p>
        </div>
      </div>

      <div
        className="rounded-2xl p-6"
        style={{
          background: 'rgba(26,26,26,0.7)',
          border: '1px solid rgba(255,255,255,0.06)',
        }}
      >
        <div className="mb-5 flex items-center gap-2">
          <Key className="h-4 w-4 text-brand-400" />
          <h2 className="font-semibold text-white">API Keys</h2>
        </div>
        <p className="mb-6 text-sm text-neutral-500">
          Your keys are encrypted at rest. They're never exposed in the browser — only used server-side.
        </p>

        <div className="space-y-4">
          {SERVICES.map(({ id, label, description, getKeyUrl, getKeyLabel }) => {
            const existing = getExistingKey(id);
            const isEditing = editing === id;
            const justSaved = saved === id;

            return (
              <div
                key={id}
                className="rounded-xl p-4"
                style={{
                  background: 'rgba(15,15,15,0.5)',
                  border: '1px solid rgba(255,255,255,0.05)',
                }}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-sm font-medium text-white">{label}</h3>
                    <p className="text-xs text-neutral-500">{description}</p>
                    <a
                      href={getKeyUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-1 inline-flex items-center gap-1 text-xs text-brand-400 no-underline hover:text-brand-300"
                    >
                      <ExternalLink className="h-3 w-3" />
                      {getKeyLabel}
                    </a>
                  </div>
                  {existing && !isEditing && (
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-brand-900/40 px-2 py-0.5 text-xs font-mono text-brand-400">
                        {existing.masked_key}
                      </span>
                      <button
                        onClick={() => { setEditing(id); setNewKeyValue(''); }}
                        className="text-xs text-neutral-400 hover:text-white"
                      >
                        Update
                      </button>
                      <button
                        onClick={() => handleDelete(id)}
                        className="text-neutral-500 hover:text-red-400"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  )}
                  {!existing && !isEditing && (
                    <button
                      onClick={() => { setEditing(id); setNewKeyValue(''); }}
                      className="flex items-center gap-1 text-xs text-brand-400 hover:text-brand-300"
                    >
                      <Plus className="h-3.5 w-3.5" />
                      Add key
                    </button>
                  )}
                  {justSaved && (
                    <span className="flex items-center gap-1 text-xs text-brand-400">
                      <Check className="h-3.5 w-3.5" /> Saved
                    </span>
                  )}
                </div>

                {isEditing && (
                  <div className="mt-3 flex gap-2">
                    <input
                      type="password"
                      value={newKeyValue}
                      onChange={(e) => setNewKeyValue(e.target.value)}
                      placeholder="Paste your API key"
                      className="flex-1 rounded-lg px-3 py-2 text-sm text-white outline-none focus:ring-1 focus:ring-brand-600/50"
                      style={{
                        background: 'rgba(26,26,26,0.8)',
                        border: '1px solid rgba(255,255,255,0.08)',
                      }}
                      autoFocus
                      onKeyDown={(e) => { if (e.key === 'Enter') handleSave(id); }}
                    />
                    <button
                      onClick={() => handleSave(id)}
                      disabled={saving || !newKeyValue.trim()}
                      className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-40"
                    >
                      {saving ? '...' : 'Save'}
                    </button>
                    <button
                      onClick={() => { setEditing(null); setNewKeyValue(''); }}
                      className="rounded-lg px-3 py-2 text-sm text-neutral-400 hover:text-white"
                      style={{ border: '1px solid rgba(255,255,255,0.08)' }}
                    >
                      Cancel
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
