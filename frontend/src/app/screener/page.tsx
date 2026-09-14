"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ScripDetailCard } from "@/components/scrip-detail-card";
import { Shell } from "@/components/shell";
import { api, getAccessToken } from "@/lib/api";
import { formatPct, formatUsd } from "@/lib/utils";
import type { BasketInfo, ScreenerHit, ScreenerResponse, StrategyView } from "@/types/trading";

export default function ScreenerPage() {
  const router = useRouter();
  const [baskets, setBaskets] = useState<BasketInfo[]>([]);
  const [strategies, setStrategies] = useState<StrategyView[]>([]);
  const [selectedBasket, setSelectedBasket] = useState<string>("nifty50");
  const [selectedStrategy, setSelectedStrategy] = useState<string>("all");
  const [sideFilter, setSideFilter] = useState<string>("all");
  const [minStrength, setMinStrength] = useState<number>(0.5);
  const [timeframe, setTimeframe] = useState<string>("1d");
  const [results, setResults] = useState<ScreenerResponse | null>(null);
  const [inspectScrip, setInspectScrip] = useState<ScreenerHit | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getAccessToken()) {
      router.replace("/login");
      return;
    }
    Promise.all([api.baskets(), api.strategies()])
      .then(([bList, strats]) => {
        setBaskets(bList);
        setStrategies(strats);
      })
      .catch((err: Error) => setError(err.message));
  }, [router]);

  async function handleScan() {
    setBusy(true);
    setError(null);
    try {
      const payload = {
        basket_id: selectedBasket,
        strategy_ids: selectedStrategy === "all" ? [] : [selectedStrategy],
        timeframe,
        min_strength: minStrength,
        side_filter: sideFilter,
        limit: 30,
      };
      const res = await api.screenerScan(payload);
      setResults(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Market scan failed");
    } finally {
      setBusy(false);
    }
  }

  function handleBacktestHit(hit: ScreenerHit) {
    const backendSym = hit.exchange === "US" ? hit.symbol : `${hit.symbol}.NS`;
    router.push(`/backtests?symbol=${encodeURIComponent(backendSym)}`);
  }

  return (
    <Shell>
      {/* Header */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-medium text-white">Quantitative Strategy Screener</h1>
          <p className="text-sm text-mute">
            Scan stock universes in real-time for systematic strategy setups and filter out noise.
          </p>
        </div>
      </div>

      {/* Filter Control Bar */}
      <section className="mb-8 rounded-lg border border-line bg-ink-900 p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3">
          <span className="text-xs font-mono font-semibold uppercase tracking-wider text-gain">
            Market Scanner Filters & Noise Gates
          </span>
          <span className="text-xs font-mono text-mute">Universe & Conviction Rules</span>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {/* Target Basket */}
          <div>
            <label className="text-xs font-mono text-mute">UNIVERSE BASKET</label>
            <select
              value={selectedBasket}
              onChange={(e) => setSelectedBasket(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-line bg-ink-800 px-3 py-2 text-xs font-mono text-white"
            >
              <option value="nifty50">NIFTY 50 (Bluechips)</option>
              <option value="nifty100">NIFTY 100 (Large Cap)</option>
              <option value="nifty150">NIFTY MIDCAP 150 (Growth)</option>
              <option value="nifty250">NIFTY SMALLCAP 250</option>
              <option value="us_tech">US TECH & ETFs</option>
            </select>
          </div>

          {/* Target Strategy */}
          <div>
            <label className="text-xs font-mono text-mute">STRATEGY SETUP</label>
            <select
              value={selectedStrategy}
              onChange={(e) => setSelectedStrategy(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-line bg-ink-800 px-3 py-2 text-xs font-mono text-white"
            >
              <option value="all">⚡ All Quantitative Strategies</option>
              {strategies.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>

          {/* Timeframe */}
          <div>
            <label className="text-xs font-mono text-mute">BAR TIMEFRAME</label>
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-line bg-ink-800 px-3 py-2 text-xs font-mono text-white"
            >
              <option value="1d">1 Day (D1)</option>
              <option value="1h">1 Hour (H1)</option>
              <option value="15m">15 Min (M15)</option>
              <option value="5m">5 Min (M5)</option>
            </select>
          </div>

          {/* Signal Direction Filter */}
          <div>
            <label className="text-xs font-mono text-mute">SIGNAL DIRECTION</label>
            <select
              value={sideFilter}
              onChange={(e) => setSideFilter(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-line bg-ink-800 px-3 py-2 text-xs font-mono text-white"
            >
              <option value="all">Both Buy & Sell</option>
              <option value="buy">🟢 Long / Buy Only</option>
              <option value="sell">🔴 Short / Sell Only</option>
            </select>
          </div>

          {/* Min Conviction Gate */}
          <div>
            <div className="flex justify-between text-xs font-mono text-mute">
              <span>MIN CONVICTION</span>
              <span className="text-white font-semibold">{Math.round(minStrength * 100)}%</span>
            </div>
            <input
              type="range"
              min={0.3}
              max={0.9}
              step={0.05}
              value={minStrength}
              onChange={(e) => setMinStrength(Number(e.target.value))}
              className="mt-2.5 w-full accent-gain"
            />
          </div>
        </div>

        <div className="mt-5 flex justify-end">
          <button
            disabled={busy}
            onClick={handleScan}
            className="rounded-lg bg-gain px-6 py-2.5 text-xs font-bold font-mono text-ink-950 transition-all hover:brightness-110 disabled:opacity-50"
          >
            {busy ? "⚡ Scanning Universe & Evaluating Setups…" : "🔍 Run Screener Scan"}
          </button>
        </div>
      </section>

      {error ? (
        <div className="mb-6 rounded-lg border border-loss/40 bg-loss/10 p-4 text-sm text-loss font-mono">
          ⚠️ {error}
        </div>
      ) : null}

      {/* Inspect Scrip Modal */}
      {inspectScrip && (
        <div className="mb-8">
          <ScripDetailCard
            scrip={{
              symbol: inspectScrip.symbol,
              name: inspectScrip.name,
              exchange: inspectScrip.exchange,
              backend_symbol:
                inspectScrip.exchange === "US"
                  ? inspectScrip.symbol
                  : `${inspectScrip.symbol}.NS`,
            }}
            onClose={() => setInspectScrip(null)}
          />
        </div>
      )}

      {/* Results Matrix */}
      {results && (
        <section className="space-y-4">
          {/* Summary KPI Strip */}
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-ink-900 p-4 text-xs font-mono">
            <div className="flex items-center gap-6">
              <span>
                Scanned Universe: <strong className="text-white">{results.total_scanned} stocks</strong>
              </span>
              <span>
                High-Conviction Hits:{" "}
                <strong className="text-gain">{results.hits_count} setups</strong>
              </span>
              <span>
                Noise Rejection Rate:{" "}
                <strong className="text-mute">
                  {results.total_scanned > 0
                    ? `${Math.round(((results.total_scanned - results.hits_count) / results.total_scanned) * 100)}%`
                    : "0%"}
                </strong>
              </span>
            </div>
            <span className="text-mute">Sorted by conviction score</span>
          </div>

          {results.hits.length === 0 ? (
            <div className="rounded-lg border border-line bg-ink-900 p-12 text-center text-sm font-mono text-mute">
              No strategy setups passed the {Math.round(minStrength * 100)}% conviction gate in this basket.
              Try lowering the min conviction slider or selecting "All Strategies".
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {results.hits.map((hit) => {
                const isBuy = hit.side === "buy";
                const isGain = hit.change_pct >= 0;
                return (
                  <div
                    key={`${hit.symbol}-${hit.strategy_id}`}
                    className="flex flex-col justify-between rounded-xl border border-line bg-ink-900 p-5 shadow-lg transition-all hover:border-gain/40"
                  >
                    <div>
                      {/* Top Scrip Line */}
                      <div className="flex items-start justify-between gap-2 border-b border-line pb-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-mono font-bold text-base text-white">
                              {hit.symbol}
                            </span>
                            <span className="rounded bg-ink-950 px-1.5 py-0.5 text-[10px] font-mono text-mute">
                              {hit.exchange}
                            </span>
                            <span
                              className={`rounded px-2 py-0.5 text-[10px] font-bold font-mono ${
                                isBuy ? "bg-gain/20 text-gain" : "bg-loss/20 text-loss"
                              }`}
                            >
                              {isBuy ? "🟢 BUY" : "🔴 SELL"} ({Math.round(hit.strength * 100)}%)
                            </span>
                          </div>
                          <div className="mt-0.5 text-xs text-mute">{hit.name}</div>
                        </div>

                        <div className="text-right font-mono">
                          <div className="text-sm font-bold text-white">{formatUsd(hit.ltp)}</div>
                          <div className={`text-xs font-semibold ${isGain ? "text-gain" : "text-loss"}`}>
                            {isGain ? "+" : ""}
                            {formatPct(hit.change_pct)}
                          </div>
                        </div>
                      </div>

                      {/* Strategy Trigger Reason */}
                      <div className="my-3 rounded-lg border border-line bg-ink-950 p-3">
                        <div className="text-[10px] font-mono text-gain font-semibold uppercase">
                          {hit.strategy_name} Setup Trigger
                        </div>
                        <p className="mt-1 text-xs text-white leading-relaxed">{hit.reason}</p>
                      </div>

                      {/* Technical & Historical KPIs */}
                      <div className="grid grid-cols-4 gap-2 font-mono text-[11px]">
                        <div className="rounded border border-line bg-ink-950 p-2">
                          <div className="text-[9px] text-mute uppercase">RSI (14)</div>
                          <div className="mt-0.5 font-semibold text-white">
                            {hit.rsi !== null ? hit.rsi : "—"}
                          </div>
                        </div>
                        <div className="rounded border border-line bg-ink-950 p-2">
                          <div className="text-[9px] text-mute uppercase">50 SMA Dist</div>
                          <div
                            className={`mt-0.5 font-semibold ${
                              (hit.dist_sma50_pct ?? 0) >= 0 ? "text-gain" : "text-loss"
                            }`}
                          >
                            {hit.dist_sma50_pct !== undefined && hit.dist_sma50_pct !== null
                              ? `${hit.dist_sma50_pct >= 0 ? "+" : ""}${hit.dist_sma50_pct}%`
                              : "—"}
                          </div>
                        </div>
                        <div className="rounded border border-line bg-ink-950 p-2">
                          <div className="text-[9px] text-mute uppercase">1Y Win Rate</div>
                          <div className="mt-0.5 font-semibold text-gain">
                            {hit.hist_win_rate_pct !== null ? `${hit.hist_win_rate_pct}%` : "—"}
                          </div>
                        </div>
                        <div className="rounded border border-line bg-ink-950 p-2">
                          <div className="text-[9px] text-mute uppercase">1Y Max DD</div>
                          <div className="mt-0.5 font-semibold text-loss">
                            {hit.hist_max_dd_pct !== null ? `-${hit.hist_max_dd_pct}%` : "—"}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="mt-4 flex items-center justify-between border-t border-line pt-3">
                      <button
                        type="button"
                        onClick={() => setInspectScrip(hit)}
                        className="rounded-lg border border-line bg-ink-800 px-3 py-1.5 text-xs font-mono text-white transition-colors hover:bg-ink-700"
                      >
                        📊 Inspect Candles & Drawdown
                      </button>

                      <button
                        type="button"
                        onClick={() => handleBacktestHit(hit)}
                        className="rounded-lg bg-gain px-3.5 py-1.5 text-xs font-bold font-mono text-ink-950 transition-all hover:brightness-110"
                      >
                        🚀 Backtest Setup
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      )}
    </Shell>
  );
}
