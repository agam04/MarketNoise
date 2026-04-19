import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import type { AuthTokens, UserInfo } from '../services/authService';
import {
  login as apiLogin,
  register as apiRegister,
  refreshToken,
} from '../services/authService';

interface AuthState {
  user: UserInfo | null;
  tokens: AuthTokens | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  getAccessToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

const TOKENS_KEY = 'mn_tokens';
const USER_KEY = 'mn_user';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserInfo | null>(() => {
    const saved = localStorage.getItem(USER_KEY);
    return saved ? JSON.parse(saved) : null;
  });
  const [tokens, setTokens] = useState<AuthTokens | null>(() => {
    const saved = localStorage.getItem(TOKENS_KEY);
    return saved ? JSON.parse(saved) : null;
  });
  const [isLoading, setIsLoading] = useState(false);

  const persist = (t: AuthTokens | null, u: UserInfo | null) => {
    if (t && u) {
      localStorage.setItem(TOKENS_KEY, JSON.stringify(t));
      localStorage.setItem(USER_KEY, JSON.stringify(u));
    } else {
      localStorage.removeItem(TOKENS_KEY);
      localStorage.removeItem(USER_KEY);
    }
    setTokens(t);
    setUser(u);
  };

  const login = useCallback(async (username: string, password: string) => {
    setIsLoading(true);
    try {
      const result = await apiLogin(username, password);
      persist(result.tokens, result.user);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const register = useCallback(async (username: string, email: string, password: string) => {
    setIsLoading(true);
    try {
      const result = await apiRegister(username, email, password);
      persist(result.tokens, result.user);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    persist(null, null);
  }, []);

  const getAccessToken = useCallback(async (): Promise<string | null> => {
    if (!tokens) return null;

    // Check if access token is expired (JWT payload has exp)
    try {
      const payload = JSON.parse(atob(tokens.access.split('.')[1]));
      const expiresAt = payload.exp * 1000;
      if (Date.now() < expiresAt - 30000) {
        // Token valid for at least 30 more seconds
        return tokens.access;
      }
    } catch {
      // Can't parse — try refresh anyway
    }

    // Refresh the token
    try {
      const newAccess = await refreshToken(tokens.refresh);
      const newTokens = { ...tokens, access: newAccess };
      persist(newTokens, user);
      return newAccess;
    } catch {
      // Refresh failed — log out
      persist(null, null);
      return null;
    }
  }, [tokens, user]);

  // Verify tokens on mount
  useEffect(() => {
    if (tokens && !user) {
      // Tokens exist but no user — try to refresh
      getAccessToken().then((t) => {
        if (!t) persist(null, null);
      });
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        tokens,
        isAuthenticated: !!user && !!tokens,
        isLoading,
        login,
        register,
        logout,
        getAccessToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
