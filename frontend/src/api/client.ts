const API_BASE = import.meta.env.VITE_API_URL ?? "";

let csrfToken: string | null = null;
let refreshInFlight: Promise<boolean> | null = null;

export function setCsrfToken(token: string | null) {
  csrfToken = token;
}

async function refreshAccessToken(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight;

  refreshInFlight = (async () => {
    try {
      const res = await fetch(`${API_BASE}/api/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) return false;
      const data = (await res.json()) as { csrf_token?: string };
      if (data.csrf_token) {
        setCsrfToken(data.csrf_token);
      }
      return true;
    } catch {
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();

  return refreshInFlight;
}

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    return data.detail ?? data.message ?? res.statusText;
  } catch {
    return res.statusText;
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  retried = false,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  if (csrfToken && options.method && options.method !== "GET") {
    headers.set("X-CSRF-Token", csrfToken);
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers,
  });

  if (
    res.status === 401 &&
    !retried &&
    path !== "/api/auth/refresh" &&
    path !== "/api/auth/logout"
  ) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return apiFetch<T>(path, options, true);
    }
  }

  if (!res.ok) {
    throw new Error(await parseError(res));
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export interface AuthUser {
  id: string;
  email: string;
  name: string | null;
  avatar_url: string | null;
  role: string;
}

export interface Subscription {
  platform: string;
  billing_interval: string;
  status: string;
  current_period_end: string | null;
}

export interface MeResponse {
  user: AuthUser;
  subscriptions: Subscription[];
}

export interface PlatformPlan {
  platform: string;
  name: string;
  available: boolean;
  prices: {
    month: { amount_cents: number; currency: string; stripe_price_id: string | null };
    year: { amount_cents: number; currency: string; stripe_price_id: string | null };
  };
}

import type { InspectResult } from "../components/inspector/types";

export type { InspectResult };

export interface AnalysisSummary {
  id: string;
  platform: string;
  post_url: string;
  post_id: string | null;
  author_name: string | null;
  author_username: string | null;
  author_avatar_url: string | null;
  description_preview: string | null;
  views: number | null;
  likes: number | null;
  comments_count: number | null;
  shares_count: number | null;
  is_saved: boolean;
  analyzed_at: string;
  saved_at: string | null;
}

export interface AnalysisDetail extends AnalysisSummary {
  payload: InspectResult;
}

export type AnalyzeResponse = InspectResult & { analysis_id: string };

export interface AdminStats {
  users: { total: number; new_7d: number; new_30d: number };
  revenue: { last_30d_cents: number; last_7d_cents: number };
  subscriptions: {
    mrr_cents: number;
    arr_cents: number;
    active_subscriptions: number;
    by_platform: Record<string, number>;
    monthly_plans: number;
    yearly_plans: number;
  };
  recent_payments: {
    event_type: string;
    amount_cents: number | null;
    currency: string;
    created_at: string | null;
    user_email: string | null;
    user_name: string | null;
  }[];
  recent_subscriptions: {
    platform: string;
    billing_interval: string;
    status: string;
    created_at: string | null;
    user_email: string;
    user_name: string | null;
  }[];
}

export const api = {
  getMe: () => apiFetch<MeResponse>("/api/auth/me"),
  getProviders: () =>
    apiFetch<{ providers: { id: string; name: string }[]; oauth_base_url: string }>(
      "/api/auth/providers",
    ),
  getCsrf: () => apiFetch<{ csrf_token: string }>("/api/auth/csrf"),
  logout: () => apiFetch<{ ok: boolean }>("/api/auth/logout", { method: "POST" }),
  getPlans: () => apiFetch<{ plans: PlatformPlan[] }>("/api/billing/plans"),
  checkout: (platform: string, interval: "month" | "year") =>
    apiFetch<{ checkout_url: string }>("/api/billing/checkout", {
      method: "POST",
      body: JSON.stringify({ platform, interval }),
    }),
  portal: () =>
    apiFetch<{ portal_url: string }>("/api/billing/portal", { method: "POST" }),
  getPlatforms: () =>
    apiFetch<{ platforms: { id: string; name: string; available: boolean }[] }>(
      "/api/v1/platforms",
    ),
  analyze: (url: string, showBrowser = false) =>
    apiFetch<AnalyzeResponse>("/api/v1/analyze", {
      method: "POST",
      body: JSON.stringify({ url, show_browser: showBrowser }),
    }),
  getAnalysisSession: () =>
    apiFetch<{ analysis: AnalysisDetail | null }>("/api/v1/analyses/session"),
  dismissAnalysisSession: () =>
    apiFetch<{ ok: boolean }>("/api/v1/analyses/session/dismiss", { method: "POST" }),
  saveAnalysis: (id: string) =>
    apiFetch<AnalysisSummary>(`/api/v1/analyses/${id}/save`, { method: "POST" }),
  listSavedAnalyses: () => apiFetch<{ items: AnalysisSummary[] }>("/api/v1/analyses/saved"),
  getAnalysis: (id: string) => apiFetch<AnalysisDetail>(`/api/v1/analyses/${id}`),
  deleteSavedAnalysis: (id: string) =>
    apiFetch<{ ok: boolean }>(`/api/v1/analyses/${id}`, { method: "DELETE" }),
  getAdminStats: () => apiFetch<AdminStats>("/api/admin/stats"),
  getAdminUsers: () =>
    apiFetch<{
      users: {
        id: string;
        email: string;
        name: string | null;
        role: string;
        created_at: string;
        platforms: string[];
        stripe_customer_id: string | null;
      }[];
      total: number;
    }>("/api/admin/users"),
};
