import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, setCsrfToken, type AuthUser, type Subscription } from "../api/client";

interface AuthState {
  user: AuthUser | null;
  subscriptions: Subscription[];
  loading: boolean;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
  hasPlatform: (platform: string) => boolean;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const data = await api.getMe();
      setUser(data.user);
      setSubscriptions(data.subscriptions);
      try {
        const csrf = await api.getCsrf();
        setCsrfToken(csrf.csrf_token);
      } catch {
        setCsrfToken(null);
      }
    } catch {
      setUser(null);
      setSubscriptions([]);
      setCsrfToken(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const logout = useCallback(async () => {
    await api.logout();
    setUser(null);
    setSubscriptions([]);
    setCsrfToken(null);
  }, []);

  const hasPlatform = useCallback(
    (platform: string) =>
      user?.role === "admin" ||
      subscriptions.some((s) => s.platform === platform && s.status === "active"),
    [subscriptions, user?.role],
  );

  const value = useMemo(
    () => ({ user, subscriptions, loading, refresh, logout, hasPlatform }),
    [user, subscriptions, loading, refresh, logout, hasPlatform],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
