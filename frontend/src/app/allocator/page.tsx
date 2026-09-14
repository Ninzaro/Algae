"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { EquityChart } from "@/components/equity-chart";
import { Kpi } from "@/components/kpi";
import { Shell } from "@/components/shell";
import { SymbolSearch } from "@/components/symbol-search";
import { api, getAccessToken } from "@/lib/api";
import { formatPct, formatUsd } from "@/lib/utils";
import type {
  BasketInfo,
  PortfolioBlendRequest,
  PortfolioBlendResponse,
  ScripInfo,
  StrategyView,
} from "@/types/trading";

export default function AllocatorPage() {
  const router = useRouter();
  const [strategies, setStrategies] = useState<StrategyView[]>([]);
  const [baskets, setBaskets] = useState<BasketInfo[]>([]);
  const [symbols, setSymbols] = useState("RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS");
  const [lookbackYears, setLookbackYears] = useState(3);
  const [timeframe, setTimeframe] = useState("1d");
  const [method, setMethod] = useState<"custom" | "equal_weight" | "risk_parity" | "max_sharpe">(
    "risk_parity",
  );
  const [strategyWeights, setStrategyWeights] = useState<Record<string, number>>({});
  const [blendResult, setBlendResult] = useState<PortfolioBlendResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getAccessToken()) {
      router.replace("/login");
      return;
    }
    Promise.all([api.strategies(), api.baskets()])
      .then(([strats, bList]) => {
        setStrategies(strats);
        setBaskets(bList);
        // Default equal weights for top 3 strategies
        const initialWeights: Record<string, number> = {};
        strats.forEach((s, idx) => {
          initialWeights[s.id] = idx < 3 ? 1.0 / Math.min(3, strats.length) : 0.0;
        });
        setStrategyWeights(initialWeights);
      })
      .catch((err: Error) => setError(err.message));
  }, [router]);

  function handleWeightChange(strategyId: string, value: number) {
    setMethod("custom");
    setStrategyWeights((prev) => ({
      ...prev,
      [strategyId]: value,
    }));
  }

  function handlePreset(preset: "equal_weight" | "risk_parity" | "max_sharpe") {
    setMethod(preset);
  }

  function handleAddSymbol(scrip: ScripInfo) {
    const current = symbols.split(",").map((s) => s.trim()).filter(Boolean);
    if (!current.includes(scrip.backend_symbol)) {
      setSymbols([...current, scrip.backend_symbol].join(","));
    }
  }

  function handleSelectBasket(basketId: string) {
    const found = baskets.find((b) => b.id === basketId);
    if (found) {
      setSymbols(found.symbols.slice(0, 8).join(","));
    }
  }

  async function handleOptimize() {
    setBusy(true);
    setError(null);
    try {
      const end = new Date();
      const start = new Date();
      start.setFullYear(end.getFullYear() - lookbackYears);

      // Selected active strategies
      const activeAllocations = Object.entries(strategyWeights)
        .filter(([_, w]) => method !== "custom" || w > 0)
        .map(([id, w]) => ({
          strategy_id: id,
          weight: w,
        }));

      if (activeAllocations.length === 0) {
        throw new Error("Please allocate weight to at least one strategy.");
      }

      const payload: PortfolioBlendRequest = {
        allocations: activeAllocations,
        symbols: symbols.split(",").map((s) => s.trim()).filter(Boolean),
        start: start.toISOString(),
        end: end.toISOString(),
        starting_cash: 100_000,
        timeframe,
        method,
      };

      const res = await api.portfolioBlend(payload);
      setBlendResult(res);

      // Sync computed weights back into UI state if optimized
      const updatedWeights: Record<string, number> = {};
      res.strategy_profiles.forEach((p) => {
        updatedWeights[p.strategy_id] = p.weight;
      });
      setStrategyWeights((prev) => ({ ...prev, ...updatedWeights }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Portfolio optimization failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell>
      {/* Top Header */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-medium text-white">Multi-Strategy Portfolio Allocator</h1>
          <p className="text-sm text-mute">
            Combine uncorrelated quantitative strategies with Risk Parity & Mean-Variance optimization to reduce drawdown.
          </p>
        </div>
      </div>

      {/* Strategy Weight Studio & Optimization Engine */}
      <section className="mb-8 rounded-lg border border-line bg-ink-900 p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3">
          <div>
            <span className="text-xs font-mono font-semibold uppercase tracking-wider text-gain">
              Step 1: Allocation Method & Strategy Weights
            </span>
          </div>

          {/* Preset Buttons */}
          <div className="flex flex-wrap items-center gap-1.5 rounded-lg border border-line bg-ink-950 p-1 text-xs font-mono">
            <button
              type="button"
              onClick={() => handlePreset("risk_parity")}
              className={`rounded px-3 py-1 font-semibold transition-colors ${
                method === "risk_parity"
                  ? "bg-gain text-ink-950"
                  : "text-mute hover:bg-ink-800 hover:text-white"
              }`}
            >
              🛡️ Risk Parity (1/Vol)
            </button>
            <button
              type="button"
              onClick={() => handlePreset("max_sharpe")}
              className={`rounded px-3 py-1 font-semibold transition-colors ${
                method === "max_sharpe"
                  ? "bg-gain text-ink-950"
                  : "text-mute hover:bg-ink-800 hover:text-white"
              }`}
            >
              🎯 Max Sharpe
            </button>
            <button
              type="button"
              onClick={() => handlePreset("equal_weight")}
              className={`rounded px-3 py-1 font-semibold transition-colors ${
                method === "equal_weight"
                  ? "bg-gain text-ink-950"
                  : "text-mute hover:bg-ink-800 hover:text-white"
              }`}
            >
              ⚖️ Equal Weight (1/N)
            </button>
          </div>
        </div>

        {/* Strategy Sliders Grid */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {strategies.map((strat) => {
            const currentW = strategyWeights[strat.id] ?? 0.0;
            const pct = Math.round(currentW * 100);
            return (
              <div
                key={strat.id}
                className={`rounded-lg border p-4 transition-all ${
                  pct > 0
                    ? "border-gain/40 bg-ink-950 shadow-md"
                    : "border-line bg-ink-950/50 opacity-60"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-sm text-white">{strat.name}</span>
                  <span className="font-mono text-xs font-bold text-gain">{pct}%</span>
                </div>
                <p className="mt-1 text-xs text-mute line-clamp-2">{strat.description}</p>
                <div className="mt-3">
                  <input
                    type="range"
                    min={0}
                    max={1}
                    step={0.05}
                    value={currentW}
                    onChange={(e) => handleWeightChange(strat.id, Number(e.target.value))}
                    className="w-full accent-gain"
                  />
                </div>
              </div>
            );
          })}
        </div>

        {/* Step 2: Universe & Horizon */}
        <div className="mt-6 border-t border-line pt-4">
          <div className="mb-3 flex items-center justify-between">
            <span className="text-xs font-mono font-semibold uppercase tracking-wider text-gain">
              Step 2: Portfolio Asset Universe & Timeframe
            </span>
            <div className="flex gap-1.5 text-xs font-mono text-mute">
              <span>Baskets:</span>
              <button
                type="button"
                onClick={() => handleSelectBasket("nifty50")}
                className="rounded bg-ink-800 px-2 py-0.5 hover:bg-ink-700 hover:text-white"
              >
                Nifty 50
              </button>
              <button
                type="button"
                onClick={() => handleSelectBasket("nifty100")}
                className="rounded bg-ink-800 px-2 py-0.5 hover:bg-ink-700 hover:text-white"
              >
                Nifty 100
              </button>
              <button
                type="button"
                onClick={() => handleSelectBasket("us_tech")}
                className="rounded bg-ink-800 px-2 py-0.5 hover:bg-ink-700 hover:text-white"
              >
                US Tech
              </button>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <div className="md:col-span-2 space-y-2">
              <SymbolSearch onSelect={handleAddSymbol} placeholder="Search scrip to add to basket (e.g. RELIANCE, TCS)..." />
              <input
                type="text"
                value={symbols}
                onChange={(e) => setSymbols(e.target.value)}
                className="w-full rounded-lg border border-line bg-ink-800 px-3 py-2 text-xs font-mono text-white"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs font-mono text-mute">TIMEFRAME</label>
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

              <div>
                <label className="text-xs font-mono text-mute">HORIZON</label>
                <select
                  value={lookbackYears}
                  onChange={(e) => setLookbackYears(Number(e.target.value))}
                  className="mt-1 block w-full rounded-lg border border-line bg-ink-800 px-3 py-2 text-xs font-mono text-white"
                >
                  <option value={1}>1 Year</option>
                  <option value={2}>2 Years</option>
                  <option value={3}>3 Years</option>
                  <option value={5}>5 Years</option>
                </select>
              </div>
            </div>
          </div>

          <div className="mt-5 flex justify-end">
            <button
              disabled={busy}
              onClick={handleOptimize}
              className="rounded-lg bg-gain px-6 py-2.5 text-xs font-bold font-mono text-ink-950 transition-all hover:brightness-110 disabled:opacity-50"
            >
              {busy ? "⚡ Optimizing Multi-Strategy Portfolio…" : "🚀 Run Portfolio Optimization"}
            </button>
          </div>
        </div>
      </section>

      {error ? (
        <div className="mb-6 rounded-lg border border-loss/40 bg-loss/10 p-4 text-sm text-loss font-mono">
          ⚠️ {error}
        </div>
      ) : null}

      {/* Optimization Results */}
      {blendResult && (
        <div className="space-y-6">
          {/* Executive Blended Tear-Sheet KPIs */}
          <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6">
            <Kpi
              label="Blended Return"
              value={formatPct(blendResult.total_return_pct)}
              tone={blendResult.total_return_pct >= 0 ? "gain" : "loss"}
              hint={`CAGR ${formatPct(blendResult.cagr_pct)}`}
            />
            <Kpi
              label="Blended Sharpe"
              value={blendResult.sharpe.toFixed(2)}
              tone={blendResult.sharpe >= 1.0 ? "gain" : "neutral"}
              hint={`Sortino ${blendResult.sortino.toFixed(2)}`}
            />
            <Kpi
              label="Blended Max Drawdown"
              value={formatPct(-blendResult.max_drawdown_pct)}
              tone="loss"
              hint={`Vol ${blendResult.annualized_volatility}%`}
            />
            <Kpi
              label="Diversification Ratio"
              value={blendResult.diversification_ratio.toFixed(2)}
              tone={blendResult.diversification_ratio > 1.1 ? "gain" : "neutral"}
              hint="Ratio > 1.0 indicates diversification gain"
            />
            <Kpi
              label="Drawdown Reduction"
              value={`+${blendResult.drawdown_reduction_pct.toFixed(1)}%`}
              tone="gain"
              hint="vs single strategy average DD"
            />
            <Kpi
              label="Ending Capital"
              value={formatUsd(blendResult.ending_equity)}
              hint={`From ${formatUsd(blendResult.starting_cash)}`}
            />
          </div>

          {/* Combined Portfolio Equity Chart */}
          <section className="rounded-lg border border-line bg-ink-900 p-5">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h2 className="text-base font-medium text-white">
                  Blended Portfolio Multi-Strategy Equity Growth
                </h2>
                <p className="text-xs text-mute">
                  Diversified capital curve synthesized from {blendResult.strategy_profiles.length} combined strategies
                </p>
              </div>
              <span className="rounded bg-gain/20 text-gain px-2.5 py-1 text-xs font-mono font-bold border border-gain/40">
                {blendResult.method.toUpperCase().replace("_", " ")}
              </span>
            </div>
            <EquityChart data={blendResult.blended_equity_curve} />
          </section>

          {/* Strategy Correlation Matrix & Breakdown */}
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Correlation Heatmap */}
            <section className="rounded-lg border border-line bg-ink-900 p-4">
              <h2 className="mb-2 text-sm font-medium text-white">Strategy Return Correlation Matrix</h2>
              <p className="mb-4 text-xs text-mute">
                Pairwise correlation between strategy returns. Low or negative correlation ($&lt; 0.3$) provides optimal drawdown dampening.
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-center text-xs font-mono">
                  <thead className="bg-ink-950 text-mute">
                    <tr>
                      <th className="p-2 text-left">Strategy</th>
                      {blendResult.strategy_profiles.map((p) => (
                        <th key={p.strategy_id} className="p-2">
                          {p.strategy_id.split("-")[0].toUpperCase()}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {blendResult.strategy_profiles.map((p1) => (
                      <tr key={p1.strategy_id} className="border-t border-line">
                        <td className="p-2 text-left font-semibold text-white">{p1.name}</td>
                        {blendResult.strategy_profiles.map((p2) => {
                          const corr = blendResult.correlation_matrix[p1.strategy_id]?.[p2.strategy_id] ?? 0.0;
                          const isHigh = corr > 0.6 && p1.strategy_id !== p2.strategy_id;
                          const isLow = corr < 0.2 && p1.strategy_id !== p2.strategy_id;
                          return (
                            <td
                              key={p2.strategy_id}
                              className={`p-2 font-bold ${
                                p1.strategy_id === p2.strategy_id
                                  ? "text-mute bg-ink-950"
                                  : isLow
                                    ? "text-gain bg-gain/10"
                                    : isHigh
                                      ? "text-warn bg-warn/10"
                                      : "text-white"
                              }`}
                            >
                              {corr.toFixed(2)}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            {/* Individual Strategy Standalone Scorecards */}
            <section className="rounded-lg border border-line bg-ink-900 p-4">
              <h2 className="mb-3 text-sm font-medium text-white">Constituent Strategy Scorecards</h2>
              <div className="space-y-3">
                {blendResult.strategy_profiles.map((p) => (
                  <div
                    key={p.strategy_id}
                    className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-ink-950 p-3 text-xs font-mono"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-white">{p.name}</span>
                        <span className="rounded bg-gain/20 text-gain px-1.5 py-0.5 text-[10px] font-bold">
                          {Math.round(p.weight * 100)}% Weight
                        </span>
                      </div>
                      <div className="mt-1 text-mute text-[11px]">Vol: {p.annualized_volatility}%</div>
                    </div>

                    <div className="flex items-center gap-4 text-right">
                      <div>
                        <div className="text-mute text-[10px]">Return</div>
                        <div className={`font-semibold ${p.total_return_pct >= 0 ? "text-gain" : "text-loss"}`}>
                          {formatPct(p.total_return_pct)}
                        </div>
                      </div>
                      <div>
                        <div className="text-mute text-[10px]">Sharpe</div>
                        <div className="font-semibold text-white">{p.sharpe.toFixed(2)}</div>
                      </div>
                      <div>
                        <div className="text-mute text-[10px]">Max DD</div>
                        <div className="font-semibold text-loss">{formatPct(-p.max_drawdown_pct)}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </div>
      )}
    </Shell>
  );
}
