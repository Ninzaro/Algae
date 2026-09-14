"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { EquityChart } from "@/components/equity-chart";
import { Kpi } from "@/components/kpi";
import { LoginForm } from "@/components/login-form";
import { ScripDetailCard } from "@/components/scrip-detail-card";
import { Shell } from "@/components/shell";
import { SymbolSearch } from "@/components/symbol-search";
import { Watchlist } from "@/components/watchlist";
import { useDashboardSocket } from "@/hooks/use-dashboard-socket";
import { api, getAccessToken } from "@/lib/api";
import { cn, formatPct, formatTs, formatUsd } from "@/lib/utils";
import type { DashboardSnapshot, EquityPoint, ScripInfo, StrategyView } from "@/types/trading";

type LookbackOption = 7 | 30 | 60 | 90 | 180 | 365 | "ALL";

export default function DashboardPage() {
  const [ready, setReady] = useState(false);
  const [authed, setAuthed] = useState(false);
  const [data, setData] = useState<DashboardSnapshot | null>(null);
  const [strategies, setStrategies] = useState<StrategyView[]>([]);
  const [lookbackDays, setLookbackDays] = useState<LookbackOption>(90);
  const [selectedScrip, setSelectedScrip] = useState<ScripInfo | { symbol: string; backend_symbol?: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const [dash, strats] = await Promise.all([api.dashboard(), api.strategies()]);
    setData(dash);
    setStrategies(strats);
  }, []);

  useEffect(() => {
    const token = getAccessToken();
    setAuthed(Boolean(token));
    setReady(true);
    if (!token) {
      return;
    }
    refresh().catch((err: Error) => setError(err.message));
  }, [refresh]);

  const live = useDashboardSocket(authed, (snapshot) => {
    setData(snapshot);
  });

  async function onKill(active: boolean) {
    setBusy(true);
    try {
      await api.killSwitch(active, true, active ? "dashboard" : "released");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kill switch failed");
    } finally {
      setBusy(false);
    }
  }

  async function onCycle() {
    setBusy(true);
    try {
      await api.runCycle();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cycle failed");
    } finally {
      setBusy(false);
    }
  }

  async function onToggle(id: string, enabled: boolean) {
    await api.toggleStrategy(id, enabled);
    await refresh();
  }

  // Filter equity curve by lookback period
  const filteredEquityCurve = useMemo(() => {
    if (!data || !data.equity_curve || data.equity_curve.length === 0) return [];
    if (lookbackDays === "ALL") return data.equity_curve;

    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - lookbackDays);

    const filtered = data.equity_curve.filter(
      (p) => new Date(p.timestamp).getTime() >= cutoff.getTime(),
    );
    return filtered.length > 0 ? filtered : data.equity_curve;
  }, [data, lookbackDays]);

  // Calculate period metrics
  const periodStats = useMemo(() => {
    if (!data) return { startEquity: 0, periodPnl: 0, periodPnlPct: 0 };
    const currentEquity = data.account.equity;
    const curve = filteredEquityCurve;
    const startEquity = curve.length > 0 ? curve[0].equity : data.account.equity;
    const periodPnl = currentEquity - startEquity;
    const periodPnlPct = startEquity > 0 ? (periodPnl / startEquity) * 100.0 : 0.0;
    return { startEquity, periodPnl, periodPnlPct };
  }, [data, filteredEquityCurve]);

  if (!ready || !authed) {
    return (
      <LoginForm
        onSignedIn={() => {
          setAuthed(true);
          setReady(true);
          refresh().catch((err: Error) => setError(err.message));
        }}
      />
    );
  }

  if (!data) {
    return (
      <Shell>
        <p className="text-mute">{error ?? "Loading book…"}</p>
      </Shell>
    );
  }

  const pnl = data.account.daily_pnl_pct;
  const dayPnlUsd = (data.account.daily_start_equity * pnl) / 100.0;

  return (
    <Shell>
      {/* Top Header & Execution Bar */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-medium">AlphaForge Control Plane</h1>
          <p className="text-sm text-mute">
            Mode <span className="font-mono text-warn font-semibold">{data.mode.toUpperCase()}</span>
            {" · "}
            <span className="font-mono">{data.persistence ?? "memory"}</span>
            {data.kill_switch ? " · ⚠️ kill switch armed" : ""}
            {" · "}
            <span className={live === "live" ? "text-gain font-semibold" : "text-mute"}>
              ● {live === "live" ? "live stream" : live === "connecting" ? "connecting" : "offline"}
            </span>
          </p>
        </div>
        <div className="flex gap-2">
          <button
            disabled={busy}
            onClick={onCycle}
            className="rounded border border-line bg-ink-800 px-3.5 py-2 text-xs font-mono font-medium hover:bg-ink-700 disabled:opacity-50"
          >
            Run Cycle
          </button>
          <button
            disabled={busy}
            onClick={() => onKill(!data.kill_switch)}
            className={cn(
              "rounded px-3.5 py-2 text-xs font-mono font-semibold transition-all",
              data.kill_switch
                ? "bg-warn text-ink-950 hover:brightness-110"
                : "bg-loss text-ink-950 hover:brightness-110",
            )}
          >
            {data.kill_switch ? "Release Kill Switch" : "Emergency Kill Switch"}
          </button>
        </div>
      </div>

      {/* Global Quick Scrip Search Bar */}
      <div className="mb-6 rounded-lg border border-line bg-ink-900 p-3.5 shadow-lg">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="text-sm">🔍</span>
            <span className="text-xs font-mono font-semibold uppercase tracking-wider text-white">
              Instant Scrip Lookup
            </span>
          </div>
          <div className="w-full sm:w-96">
            <SymbolSearch
              onSelect={(scrip) => setSelectedScrip(scrip)}
              placeholder="Search any scrip (e.g. RELIANCE, TCS, HDFCBANK, SPY)..."
            />
          </div>
        </div>
      </div>

      {/* Expandable Scrip Detail Workspace */}
      {selectedScrip && (
        <div className="mb-8">
          <ScripDetailCard scrip={selectedScrip} onClose={() => setSelectedScrip(null)} />
        </div>
      )}

      {error ? <p className="mb-4 text-sm text-loss">{error}</p> : null}

      {/* Portfolio Overview & Lookback Analytics */}
      <section className="mb-8 rounded-lg border border-line bg-ink-900 p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-line pb-4">
          <div>
            <span className="text-xs font-mono uppercase tracking-wider text-mute">Total Portfolio Equity</span>
            <div className="flex items-baseline gap-3">
              <span className="text-2xl font-bold font-mono text-white">
                {formatUsd(data.account.equity)}
              </span>
              <span
                className={`font-mono text-sm font-semibold ${
                  periodStats.periodPnl >= 0 ? "text-gain" : "text-loss"
                }`}
              >
                {periodStats.periodPnl >= 0 ? "+" : ""}
                {formatUsd(periodStats.periodPnl)} ({formatPct(periodStats.periodPnlPct)}) in past{" "}
                {lookbackDays === "ALL" ? "history" : `${lookbackDays}d`}
              </span>
            </div>
          </div>

          {/* Lookback Selector */}
          <div className="flex items-center gap-1.5 rounded-lg border border-line bg-ink-950 p-1 text-xs font-mono">
            <span className="px-2 text-mute">Lookback:</span>
            {([7, 30, 60, 90, 180, 365, "ALL"] as LookbackOption[]).map((lb) => (
              <button
                key={lb}
                type="button"
                onClick={() => setLookbackDays(lb)}
                className={`rounded px-2.5 py-1 transition-colors ${
                  lookbackDays === lb
                    ? "bg-gain text-ink-950 font-bold"
                    : "text-mute hover:bg-ink-800 hover:text-white"
                }`}
              >
                {lb === "ALL" ? "ALL" : `${lb}D`}
              </button>
            ))}
          </div>
        </div>

        {/* Primary KPI Grid */}
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <Kpi
            label="Day P&L"
            value={formatPct(pnl)}
            tone={pnl >= 0 ? "gain" : "loss"}
            hint={`${pnl >= 0 ? "+" : ""}${formatUsd(dayPnlUsd)} today`}
          />
          <Kpi
            label={`Starting Capital (${lookbackDays === "ALL" ? "Inception" : `${lookbackDays}d ago`})`}
            value={formatUsd(periodStats.startEquity)}
          />
          <Kpi
            label="Current Drawdown"
            value={formatPct(-data.account.drawdown_pct)}
            tone={data.account.drawdown_pct > 0 ? "loss" : "neutral"}
            hint={`Peak ${formatUsd(data.account.peak_equity)}`}
          />
          <Kpi
            label="Available Cash"
            value={formatUsd(data.account.cash)}
            hint={`Buying Power ${formatUsd(data.account.buying_power)}`}
          />
          <Kpi
            label="Active Positions"
            value={`${data.positions.length} stocks`}
            hint={`${data.open_orders.length} open orders`}
          />
        </div>

        {/* Dynamic Equity Curve */}
        <div className="mt-6">
          <div className="mb-2 flex items-center justify-between text-xs font-mono text-mute">
            <span>Historical Equity Curve</span>
            <span>{filteredEquityCurve.length} recorded data points</span>
          </div>
          <EquityChart data={filteredEquityCurve.length > 0 ? filteredEquityCurve : data.equity_curve} />
        </div>
      </section>

      {/* Interactive Watchlist Widget */}
      <div className="mb-8">
        <Watchlist
          initialQuotes={data.quotes ?? []}
          onSelectScrip={(scrip) => setSelectedScrip(scrip)}
        />
      </div>

      {/* Positions & Strategy Controls */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Current Positions */}
        <section className="rounded-lg border border-line bg-ink-900 p-4">
          <h2 className="mb-3 text-sm font-medium text-white">Open Portfolio Positions</h2>
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-ink-950 uppercase text-mute">
              <tr>
                <th className="px-3 py-2">Symbol</th>
                <th className="px-3 py-2">Qty</th>
                <th className="px-3 py-2">Avg Price</th>
                <th className="px-3 py-2">LTP</th>
                <th className="px-3 py-2 text-right">uPnL</th>
              </tr>
            </thead>
            <tbody>
              {data.positions.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-6 text-center text-mute">
                    No active open positions (Flat).
                  </td>
                </tr>
              ) : (
                data.positions.map((p) => {
                  const cleanSym = p.symbol.replace(".NS", "").replace(".BO", "");
                  return (
                    <tr
                      key={p.symbol}
                      onClick={() => setSelectedScrip({ symbol: p.symbol, backend_symbol: p.symbol })}
                      className="border-t border-line cursor-pointer hover:bg-ink-800/40"
                    >
                      <td className="px-3 py-2 font-semibold text-white">{cleanSym}</td>
                      <td className="px-3 py-2">{p.quantity}</td>
                      <td className="px-3 py-2">{formatUsd(p.avg_price)}</td>
                      <td className="px-3 py-2">{formatUsd(p.market_price)}</td>
                      <td
                        className={`px-3 py-2 text-right font-semibold ${
                          p.unrealized_pnl >= 0 ? "text-gain" : "text-loss"
                        }`}
                      >
                        {formatUsd(p.unrealized_pnl)}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </section>

        {/* Strategy Control Matrix */}
        <section className="rounded-lg border border-line bg-ink-900 p-4">
          <h2 className="mb-3 text-sm font-medium text-white">Active Quantitative Strategies</h2>
          <ul className="space-y-2.5">
            {strategies.map((s) => (
              <li
                key={s.id}
                className="flex items-center justify-between rounded-lg border border-line bg-ink-950 p-3"
              >
                <div>
                  <div className="text-xs font-semibold text-white">{s.name}</div>
                  <div className="text-[11px] text-mute font-mono">
                    ID: {s.id} · Baskets: {s.symbols.join(", ")}
                  </div>
                </div>
                <button
                  onClick={() => onToggle(s.id, !s.enabled)}
                  className={cn(
                    "rounded px-2.5 py-1 font-mono text-xs font-semibold transition-all",
                    s.enabled
                      ? "bg-gain/20 text-gain border border-gain/40"
                      : "bg-ink-800 text-mute hover:bg-ink-700 hover:text-white",
                  )}
                >
                  {s.enabled ? "ACTIVE" : "DISABLED"}
                </button>
              </li>
            ))}
          </ul>
        </section>
      </div>

      {/* Live Signals Stream */}
      <section className="mt-8 rounded-lg border border-line bg-ink-900 p-4">
        <h2 className="mb-3 text-sm font-medium text-white">Recent Real-Time Signals</h2>
        <ul className="space-y-2 font-mono text-xs">
          {data.recent_signals.length === 0 ? (
            <li className="py-4 text-center text-mute">No signals triggered yet — run a cycle.</li>
          ) : (
            data.recent_signals.map((s) => {
              const cleanSym = s.symbol.replace(".NS", "").replace(".BO", "");
              const isBuy = s.side === "buy";
              return (
                <li
                  key={s.id}
                  className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-2.5"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-mute">{formatTs(s.timestamp)}</span>
                    <span className="font-semibold text-white">{cleanSym}</span>
                    <span
                      className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                        isBuy ? "bg-gain/20 text-gain" : "bg-loss/20 text-loss"
                      }`}
                    >
                      {s.side.toUpperCase()}
                    </span>
                    <span className="text-mute">({s.strategy_id})</span>
                  </div>
                  <span className="text-mute/80">{s.reason}</span>
                </li>
              );
            })
          )}
        </ul>
      </section>
    </Shell>
  );
}
