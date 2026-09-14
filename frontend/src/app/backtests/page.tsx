"use client";

import { FormEvent, useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { BacktestVisualizer } from "@/components/backtest-visualizer";
import { EquityChart } from "@/components/equity-chart";
import { Kpi } from "@/components/kpi";
import { Shell } from "@/components/shell";
import { SymbolSearch } from "@/components/symbol-search";
import { api, getAccessToken } from "@/lib/api";
import { cn, formatPct, formatTs, formatUsd } from "@/lib/utils";
import type { BacktestResult, BasketInfo, ScripInfo, StrategyView, WalkForwardResult } from "@/types/trading";

type Mode = "single" | "walk-forward";

const STRATEGY_DESCRIPTIONS: Record<string, { summary: string; tags: string[]; icon: string }> = {
  "trend-breakout": {
    summary: "Donchian 20-day high breakout with ATR volatility expansion filter and Supertrend trailing stop.",
    tags: ["Trend Following", "Momentum", "Breakout"],
    icon: "📈",
  },
  "volatility-breakout": {
    summary: "Detects Bollinger Band squeeze compression followed by explosive directional expansion with MACD momentum.",
    tags: ["Volatility Squeeze", "Momentum", "Bollinger"],
    icon: "⚡",
  },
  "sma-crossover": {
    summary: "Classic moving average trend crossover: Buys on fast/slow cross up, flattens on cross down.",
    tags: ["Moving Average", "Trend", "Classic"],
    icon: "🔄",
  },
  "mean-reversion": {
    summary: "Standardized Z-Score statistical mean-reversion with dynamic entry and exit bounds.",
    tags: ["Mean Reversion", "Statistical", "Oscillator"],
    icon: "🎯",
  },
  "stat-arb-pairs": {
    summary: "Statistical Arbitrage on cointegrated pairs spread (e.g. RELIANCE vs INFY or SPY vs QQQ).",
    tags: ["Stat Arb", "Pairs Trading", "Market Neutral"],
    icon: "⚖️",
  },
};

function BacktestsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialSym = searchParams.get("symbol") || "RELIANCE.NS,TCS.NS,INFY.NS";

  const [strategies, setStrategies] = useState<StrategyView[]>([]);
  const [strategyId, setStrategyId] = useState("trend-breakout");
  const [symbols, setSymbols] = useState(initialSym);
  const [baskets, setBaskets] = useState<BasketInfo[]>([]);
  const [mode, setMode] = useState<Mode>("single");
  const [startingCash, setStartingCash] = useState(100_000);
  const [lookbackYears, setLookbackYears] = useState(3);
  const [timeframe, setTimeframe] = useState("1d");
  const [trainBars, setTrainBars] = useState(252);
  const [testBars, setTestBars] = useState(63);
  const [stepBars, setStepBars] = useState(63);
  const [anchored, setAnchored] = useState(false);
  const [single, setSingle] = useState<BacktestResult | null>(null);
  const [walk, setWalk] = useState<WalkForwardResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!getAccessToken()) {
      router.replace("/login");
      return;
    }
    Promise.all([api.strategies(), api.baskets()])
      .then(([strats, bList]) => {
        setStrategies(strats);
        setBaskets(bList);
        if (strats.length > 0) {
          const defaultStrat = strats.find((s) => s.id === "trend-breakout") ?? strats[0];
          setStrategyId(defaultStrat.id);
        }
      })
      .catch((err: Error) => setError(err.message));
  }, [router]);

  function handleSelectBasket(basketId: string) {
    const found = baskets.find((b) => b.id === basketId);
    if (found) {
      setSymbols(found.symbols.slice(0, 5).join(","));
    }
  }

  function handleAddSymbol(scrip: ScripInfo) {
    const current = symbols.split(",").map((s) => s.trim()).filter(Boolean);
    if (!current.includes(scrip.backend_symbol)) {
      setSymbols([...current, scrip.backend_symbol].join(","));
    }
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSingle(null);
    setWalk(null);
    const end = new Date();
    const start = new Date();
    start.setFullYear(end.getFullYear() - lookbackYears);

    const payload = {
      strategy_id: strategyId,
      symbols: symbols.split(",").map((s) => s.trim()).filter(Boolean),
      start: start.toISOString(),
      end: end.toISOString(),
      timeframe,
      starting_cash: startingCash,
    };

    try {
      if (mode === "single") {
        setSingle(await api.backtest(payload));
      } else {
        setWalk(
          await api.walkForward({
            ...payload,
            train_bars: trainBars,
            test_bars: testBars,
            step_bars: stepBars,
            anchored,
          }),
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Backtest execution failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell>
      {/* Header */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-medium">Quantitative Backtest Studio</h1>
          <p className="text-sm text-mute">
            Select a strategy, choose stock baskets or scrips, and run institutional tear-sheet simulations.
          </p>
        </div>
        <div className="flex rounded-lg border border-line bg-ink-900 p-1">
          <button
            type="button"
            onClick={() => setMode("single")}
            className={cn(
              "rounded px-3.5 py-1.5 text-xs font-mono font-medium transition-colors",
              mode === "single" ? "bg-gain text-ink-950 font-bold" : "text-mute hover:text-white",
            )}
          >
            Tear-Sheet Backtest
          </button>
          <button
            type="button"
            onClick={() => setMode("walk-forward")}
            className={cn(
              "rounded px-3.5 py-1.5 text-xs font-mono font-medium transition-colors",
              mode === "walk-forward" ? "bg-gain text-ink-950 font-bold" : "text-mute hover:text-white",
            )}
          >
            Walk-Forward Optimization
          </button>
        </div>
      </div>

      {/* Step 1: Strategy Selection Cards */}
      <section className="mb-6 rounded-lg border border-line bg-ink-900 p-5">
        <div className="mb-3 flex items-center justify-between">
          <span className="text-xs font-mono uppercase tracking-wider text-gain font-semibold">
            Step 1: Choose Quantitative Strategy
          </span>
          <span className="text-xs text-mute font-mono">{strategies.length} strategies available</span>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {strategies.map((s) => {
            const meta = STRATEGY_DESCRIPTIONS[s.id] || {
              summary: s.description,
              tags: ["Quant"],
              icon: "📊",
            };
            const isSelected = strategyId === s.id;
            return (
              <div
                key={s.id}
                onClick={() => setStrategyId(s.id)}
                className={`cursor-pointer rounded-lg border p-4 transition-all ${
                  isSelected
                    ? "border-gain bg-gain/10 shadow-lg ring-1 ring-gain"
                    : "border-line bg-ink-950 hover:border-line/80 hover:bg-ink-850"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{meta.icon}</span>
                    <span className="font-semibold text-white text-sm">{s.name}</span>
                  </div>
                  {isSelected ? (
                    <span className="rounded bg-gain px-1.5 py-0.5 text-[10px] font-bold text-ink-950 font-mono">
                      ACTIVE
                    </span>
                  ) : null}
                </div>
                <p className="mt-2 text-xs text-mute leading-relaxed">{meta.summary}</p>
                <div className="mt-3 flex flex-wrap gap-1">
                  {meta.tags.map((t) => (
                    <span
                      key={t}
                      className="rounded bg-ink-900 px-1.5 py-0.5 text-[10px] font-mono text-mute"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Step 2 & 3: Symbol Basket & Execution Parameters */}
      <form onSubmit={onSubmit} className="mb-8 space-y-4 rounded-lg border border-line bg-ink-900 p-5">
        <div className="flex items-center justify-between border-b border-line pb-3">
          <span className="text-xs font-mono uppercase tracking-wider text-gain font-semibold">
            Step 2 & 3: Basket & Time Horizon
          </span>
          <div className="flex items-center gap-2 text-xs font-mono text-mute">
            <span>Quick Baskets:</span>
            <button
              type="button"
              onClick={() => handleSelectBasket("nifty50")}
              className="rounded bg-ink-800 px-2 py-1 hover:bg-ink-700 hover:text-white"
            >
              Nifty 50
            </button>
            <button
              type="button"
              onClick={() => handleSelectBasket("nifty100")}
              className="rounded bg-ink-800 px-2 py-1 hover:bg-ink-700 hover:text-white"
            >
              Nifty 100
            </button>
            <button
              type="button"
              onClick={() => handleSelectBasket("nifty150")}
              className="rounded bg-ink-800 px-2 py-1 hover:bg-ink-700 hover:text-white"
            >
              Midcap 150
            </button>
            <button
              type="button"
              onClick={() => handleSelectBasket("us_tech")}
              className="rounded bg-ink-800 px-2 py-1 hover:bg-ink-700 hover:text-white"
            >
              US Tech
            </button>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          {/* Symbol Search & Target List */}
          <div className="space-y-1.5 md:col-span-2">
            <label className="text-xs font-mono text-mute">SEARCH & ADD SCRIPS (NO .NS NEEDED)</label>
            <SymbolSearch onSelect={handleAddSymbol} placeholder="Search scrip to add (e.g. RELIANCE, TCS, INFY)..." />
            <div className="mt-2">
              <label className="text-[11px] font-mono text-mute">SELECTED SYMBOLS IN BASKET</label>
              <input
                type="text"
                value={symbols}
                onChange={(e) => setSymbols(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-line bg-ink-800 px-3 py-2 text-xs font-mono text-white"
              />
            </div>
          </div>

          {/* Time Horizon, Timeframe & Capital */}
          <div className="grid grid-cols-3 gap-2">
            <div>
              <label className="text-xs font-mono text-mute">TIMEFRAME</label>
              <select
                value={timeframe}
                onChange={(e) => setTimeframe(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-line bg-ink-800 px-3 py-2 text-xs text-white font-mono"
              >
                <option value="1d">1 Day (D1)</option>
                <option value="1h">1 Hour (H1)</option>
                <option value="15m">15 Min (M15)</option>
                <option value="5m">5 Min (M5)</option>
                <option value="1m">1 Min (M1)</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-mono text-mute">DURATION</label>
              <select
                value={lookbackYears}
                onChange={(e) => setLookbackYears(Number(e.target.value))}
                className="mt-1 block w-full rounded-lg border border-line bg-ink-800 px-3 py-2 text-xs text-white font-mono"
              >
                <option value={1}>1 Year</option>
                <option value={2}>2 Years</option>
                <option value={3}>3 Years</option>
                <option value={5}>5 Years</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-mono text-mute">CAPITAL</label>
              <input
                type="number"
                value={startingCash}
                onChange={(e) => setStartingCash(Number(e.target.value))}
                className="mt-1 block w-full rounded-lg border border-line bg-ink-800 px-3 py-2 text-xs text-white font-mono"
              />
            </div>
          </div>
        </div>

        {mode === "walk-forward" ? (
          <div className="grid grid-cols-4 gap-3 border-t border-line pt-3 font-mono text-xs text-mute">
            <label>
              TRAIN BARS:
              <input
                type="number"
                value={trainBars}
                onChange={(e) => setTrainBars(Number(e.target.value))}
                className="mt-1 block w-full rounded border border-line bg-ink-800 px-2.5 py-1.5 text-white"
              />
            </label>
            <label>
              TEST BARS:
              <input
                type="number"
                value={testBars}
                onChange={(e) => setTestBars(Number(e.target.value))}
                className="mt-1 block w-full rounded border border-line bg-ink-800 px-2.5 py-1.5 text-white"
              />
            </label>
            <label>
              STEP BARS:
              <input
                type="number"
                value={stepBars}
                onChange={(e) => setStepBars(Number(e.target.value))}
                className="mt-1 block w-full rounded border border-line bg-ink-800 px-2.5 py-1.5 text-white"
              />
            </label>
            <div className="flex items-center gap-2 pt-4">
              <input
                type="checkbox"
                checked={anchored}
                onChange={(e) => setAnchored(e.target.checked)}
                className="rounded border-line bg-ink-800"
              />
              <span>Anchored Training</span>
            </div>
          </div>
        ) : null}

        <div className="flex justify-end pt-2">
          <button
            disabled={busy}
            className="rounded-lg bg-gain px-6 py-2.5 text-sm font-bold font-mono text-ink-950 transition-all hover:brightness-110 disabled:opacity-50"
          >
            {busy ? "⚡ Running Quantitative Backtest…" : "🚀 Launch Backtest"}
          </button>
        </div>
      </form>

      {error ? (
        <div className="mb-6 rounded-lg border border-loss/40 bg-loss/10 p-4 text-sm text-loss font-mono">
          ⚠️ {error}
        </div>
      ) : null}

      {/* Clear Plain-English Results */}
      {single ? (
        <div className="space-y-6">
          {/* Executive Summary Card */}
          <section className="rounded-lg border border-gain/40 bg-gain/5 p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <span className="text-xs font-mono font-semibold uppercase tracking-wider text-gain">
                  Strategy Executive Summary
                </span>
                <div className="mt-1 text-lg font-medium text-white">
                  Starting with <strong className="text-gain font-mono">{formatUsd(single.starting_cash)}</strong> grew
                  to <strong className="text-gain font-mono">{formatUsd(single.ending_equity)}</strong> (
                  <span className={single.total_return_pct >= 0 ? "text-gain font-mono" : "text-loss font-mono"}>
                    {single.total_return_pct >= 0 ? "+" : ""}
                    {formatPct(single.total_return_pct)}
                  </span>
                  )
                </div>
              </div>
              <div className="flex items-center gap-3 font-mono text-xs">
                <span className="rounded bg-ink-900 border border-line px-3 py-1.5">
                  Sharpe: <strong className="text-white">{single.sharpe.toFixed(2)}</strong>
                </span>
                <span className="rounded bg-ink-900 border border-line px-3 py-1.5">
                  Max Drawdown: <strong className="text-loss">{formatPct(-single.max_drawdown_pct)}</strong>
                </span>
                <span className="rounded bg-ink-900 border border-line px-3 py-1.5">
                  Win Rate: <strong className="text-gain">{(single.win_rate * 100).toFixed(1)}%</strong>
                </span>
              </div>
            </div>
          </section>

          {/* Full Tear-Sheet Visualizer */}
          <BacktestVisualizer result={single} />
        </div>
      ) : null}

      {walk ? (
        <div className="space-y-6">
          <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-4">
            <Kpi
              label="OOS Return"
              value={formatPct(walk.oos_return_pct)}
              tone={walk.oos_return_pct >= 0 ? "gain" : "loss"}
            />
            <Kpi label="OOS Max Drawdown" value={formatPct(-walk.oos_max_drawdown_pct)} tone="loss" />
            <Kpi label="OOS Sharpe" value={walk.oos_sharpe.toFixed(2)} />
            <Kpi
              label="OOS Ending Capital"
              value={formatUsd(walk.ending_equity)}
              hint={`${walk.folds.length} rolling folds`}
            />
          </div>

          <section className="rounded-lg border border-line bg-ink-900 p-4">
            <h2 className="mb-3 text-sm font-medium text-white">Walk-Forward Out-of-Sample Equity Curve</h2>
            <EquityChart data={walk.oos_equity_curve} />
          </section>

          <section className="overflow-x-auto rounded-lg border border-line bg-ink-900">
            <div className="border-b border-line p-3">
              <h2 className="text-sm font-medium text-white">Walk-Forward Folds Breakdown</h2>
            </div>
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-ink-950 uppercase text-mute">
                <tr>
                  <th className="px-3 py-2.5">Fold Range</th>
                  <th className="px-3 py-2.5">Best In-Sample Params</th>
                  <th className="px-3 py-2.5">IS Sharpe</th>
                  <th className="px-3 py-2.5">OOS Sharpe</th>
                  <th className="px-3 py-2.5">OOS Return</th>
                  <th className="px-3 py-2.5">OOS Max DD</th>
                </tr>
              </thead>
              <tbody>
                {walk.folds.map((fold, index) => (
                  <tr key={`${fold.test_start}-${index}`} className="border-t border-line hover:bg-ink-800/50">
                    <td className="px-3 py-2.5 text-mute">
                      {formatTs(fold.train_start)} → {formatTs(fold.test_end)}
                    </td>
                    <td className="px-3 py-2.5 text-white">{JSON.stringify(fold.params)}</td>
                    <td className="px-3 py-2.5">{fold.is_sharpe.toFixed(2)}</td>
                    <td
                      className={
                        fold.oos_sharpe >= 1.0
                          ? "px-3 py-2.5 text-gain font-semibold"
                          : fold.oos_sharpe < 0
                            ? "px-3 py-2.5 text-loss font-semibold"
                            : "px-3 py-2.5 text-mute"
                      }
                    >
                      {fold.oos_sharpe.toFixed(2)}
                    </td>
                    <td
                      className={
                        fold.oos_return_pct >= 0
                          ? "px-3 py-2.5 text-gain font-semibold"
                          : "px-3 py-2.5 text-loss font-semibold"
                      }
                    >
                      {formatPct(fold.oos_return_pct)}
                    </td>
                    <td className="px-3 py-2.5 text-loss">{formatPct(-fold.oos_max_drawdown_pct)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </div>
      ) : null}
    </Shell>
  );
}

export default function BacktestsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-mute font-mono">Loading Backtest Studio…</div>}>
      <BacktestsContent />
    </Suspense>
  );
}
