const API_BASE = '/api/auth';

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface UserInfo {
  id: number;
  username: string;
  email: string;
}

export interface ApiKeyInfo {
  service: string;
  service_display: string;
  masked_key: string;
  updated_at: string;
}

function authHeaders(token: string): HeadersInit {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
}

export async function login(username: string, password: string): Promise<{ tokens: AuthTokens; user: UserInfo }> {
  // Get tokens
  const tokenRes = await fetch(`${API_BASE}/token/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!tokenRes.ok) {
    const err = await tokenRes.json().catch(() => ({}));
    throw new Error(err.detail || 'Invalid credentials');
  }
  const tokens: AuthTokens = await tokenRes.json();

  // Get profile
  const profileRes = await fetch(`${API_BASE}/profile/`, {
    headers: authHeaders(tokens.access),
  });
  const user: UserInfo = await profileRes.json();

  return { tokens, user };
}

export async function register(
  username: string,
  email: string,
  password: string
): Promise<{ tokens: AuthTokens; user: UserInfo }> {
  const res = await fetch(`${API_BASE}/register/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || 'Registration failed');
  }
  const data = await res.json();
  return { tokens: data.tokens, user: data.user };
}

export async function refreshToken(refresh: string): Promise<string> {
  const res = await fetch(`${API_BASE}/token/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  });
  if (!res.ok) throw new Error('Token refresh failed');
  const data = await res.json();
  return data.access;
}

export async function getApiKeys(token: string): Promise<ApiKeyInfo[]> {
  const res = await fetch(`${API_BASE}/apikeys/`, {
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to fetch API keys');
  return res.json();
}

export async function saveApiKey(token: string, service: string, key: string): Promise<void> {
  const res = await fetch(`${API_BASE}/apikeys/`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ service, key }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || 'Failed to save API key');
  }
}

export async function deleteApiKey(token: string, service: string): Promise<void> {
  const res = await fetch(`${API_BASE}/apikeys/${service}/`, {
    method: 'DELETE',
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to delete API key');
}
