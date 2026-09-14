import type {
  BacktestResult,
  BasketInfo,
  DashboardSnapshot,
  PortfolioBlendRequest,
  PortfolioBlendResponse,
  WalkForwardResult,
  Bar,
  JournalEntry,
  Quote,
  ScripInfo,
  ScreenerRequest,
  ScreenerResponse,
  StrategyView,
  TokenResponse,
} from "@/types/trading";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function readError(body: unknown, status: number): string {
  if (body && typeof body === "object") {
    const rec = body as Record<string, unknown>;
    if (typeof rec.message === "string") return rec.message;
    if (typeof rec.detail === "string") return rec.detail;
    if (Array.isArray(rec.detail)) {
      return rec.detail
        .map((item) => {
          if (item && typeof item === "object" && "msg" in item) {
            return String((item as { msg: unknown }).msg);
          }
          return JSON.stringify(item);
        })
        .join("; ");
    }
  }
  return `Request failed (${status})`;
}

const ACCESS_KEY = "af_access";
const REFRESH_KEY = "af_refresh";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_KEY);
}

export function setTokens(tokens: TokenResponse): void {
  localStorage.setItem(ACCESS_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${BASE}${path}`, { ...init, headers });
  if (response.status === 401 && typeof window !== "undefined") {
    clearTokens();
    if (!path.startsWith("/api/v1/auth")) {
      window.location.href = "/login";
    }
  }
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    throw new Error(readError(body, response.status));
  }
  return (await response.json()) as T;
}

export const api = {
  login: (email: string, password: string) =>
    request<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  dashboard: () => request<DashboardSnapshot>("/api/v1/dashboard"),
  strategies: () => request<StrategyView[]>("/api/v1/strategies"),
  toggleStrategy: (id: string, enabled: boolean) =>
    request<StrategyView>(`/api/v1/strategies/${id}/toggle`, {
      method: "POST",
      body: JSON.stringify({ enabled }),
    }),
  runCycle: () => request<{ signals: number }>("/api/v1/strategies/cycle", { method: "POST" }),
  killSwitch: (active: boolean, flatten = true, reason = "") =>
    request<{ active: boolean; reason: string; cancelled_orders: number }>(
      "/api/v1/risk/kill-switch",
      { method: "POST", body: JSON.stringify({ active, flatten, reason }) },
    ),
  journal: () => request<{ items: JournalEntry[] }>("/api/v1/journal"),
  backtest: (payload: {
    strategy_id: string;
    symbols: string[];
    start: string;
    end: string;
    timeframe?: string;
    starting_cash?: number;
  }) =>
    request<BacktestResult>("/api/v1/backtests", {
      method: "POST",
      body: JSON.stringify({
        timeframe: "1d",
        starting_cash: 100000,
        ...payload,
      }),
    }),
  walkForward: (payload: {
    strategy_id: string;
    symbols: string[];
    start: string;
    end: string;
    train_bars: number;
    test_bars: number;
    step_bars: number;
    anchored: boolean;
    timeframe?: string;
    starting_cash?: number;
  }) =>
    request<WalkForwardResult>("/api/v1/backtests/walk-forward", {
      method: "POST",
      body: JSON.stringify({
        timeframe: "1d",
        starting_cash: 100000,
        ...payload,
      }),
    }),
  quotes: (symbols?: string) =>
    request<Quote[]>(
      `/api/v1/market/quotes${symbols ? `?symbols=${encodeURIComponent(symbols)}` : ""}`,
    ),
  bars: (symbol: string, lookback = 120, timeframe = "1d") =>
    request<Bar[]>(
      `/api/v1/market/bars?symbol=${encodeURIComponent(symbol)}&lookback=${lookback}&timeframe=${timeframe}`,
    ),
  search: (query: string, limit = 15) =>
    request<ScripInfo[]>(
      `/api/v1/market/search?q=${encodeURIComponent(query)}&limit=${limit}`,
    ),
  baskets: () => request<BasketInfo[]>("/api/v1/market/baskets"),
  screenerScan: (payload: ScreenerRequest) =>
    request<ScreenerResponse>("/api/v1/screener/scan", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  portfolioBlend: (payload: PortfolioBlendRequest) =>
    request<PortfolioBlendResponse>("/api/v1/portfolio/blend", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
