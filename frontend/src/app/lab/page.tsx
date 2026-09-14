"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Shell } from "@/components/shell";
import { SymbolSearch } from "@/components/symbol-search";
import { EquityChart } from "@/components/equity-chart";
import { Kpi } from "@/components/kpi";
import { api, getAccessToken } from "@/lib/api";
import { cn, formatPct, formatUsd } from "@/lib/utils";
import type {
  GridResultPoint,
  GridSearchResponse,
  ParamRange,
  ScripInfo,
  StrategyLabInfo,
  StrategyView,
} from "@/types/trading";

function ParamSlider({
  param,
  value,
  onChange,
}: {
  param: ParamRange;
  value: number;
  onChange: (val: number) => void;
}) {
  return (
    <div className="rounded-lg border border-line bg-ink-950 p-3">
      <div className="flex items-center justify-between mb-2">
        <label className="text-xs font-mono text-mute uppercase">{param.name}</label>
        <span className="text-xs font-mono font-bold text-gain">{value}</span>
      </div>
      <input
        type="range"
        min={param.min}
        max={param.max}
        step={param.step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-gain"
      />
      <div className="flex justify-between text-[10px] font-mono text-mute mt-1">
        <span>{param.min}</span>
        <span className="text-white">{param.default}</span>
        <span>{param.max}</span>
      </div>
    </div>
  );
}

function HeatmapCell({ point, best }: { point: GridResultPoint; best: GridResultPoint }) {
  const sharpeNorm = Math.max(0, Math.min(1, (point.sharpe + 1) / 4));
  const isBest = point.params === best.params || point.sharpe === best.sharpe;
  const bg =
    point.sharpe >= 1.0
      ? "bg-gain/20 border-gain/40"
      : point.sharpe >= 0.5
        ? "bg-gain/10 border-gain/20"
        : point.sharpe >= 0
          ? "bg-ink-950 border-line"
          : "bg-loss/10 border-loss/20";

  return (
    <div
      className={cn(
        "rounded-lg border p-3 text-center font-mono transition-all hover:scale-105",
        bg,
        isBest && "ring-1 ring-gain"
      )}
    >
      <div className="text-[10px] text-mute uppercase">Sharpe</div>
      <div
        className={cn(
          "text-sm font-bold mt-0.5",
          point.sharpe >= 1.0 ? "text-gain" : point.sharpe >= 0 ? "text-white" : "text-loss"
        )}
      >
        {point.sharpe.toFixed(2)}
      </div>
      <div className="text-[10px] text-mute mt-1">
        {Object.entries(point.params)
          .slice(0, 2)
          .map(([k, v]) => `${k}=${v}`)
          .join(", ")}
      </div>
      {isBest && (
        <span className="mt-1 inline-block rounded bg-gain px-1.5 py-0.5 text-[9px] font-bold text-ink-950">
          BEST
        </span>
      )}
    </div>
  );
}

export default function StrategyLabPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [strategyId, setStrategyId] = useState("sma-crossover");
  const [symbols, setSymbols] = useState("SPY,QQQ");
  const [lookbackYears, setLookbackYears] = useState(3);
  const [timeframe, setTimeframe] = useState("1d");
  const [startingCash, setStartingCash] = useState(100_000);
  const [maxCombinations, setMaxCombinations] = useState(80);
  const [error, setError] = useState<string | null>(null);

  const { data: strategies = [] } = useQuery({
    queryKey: ["strategies"],
    queryFn: () => api.strategies(),
    staleTime: 60_000,
  });

  const { data: labInfo } = useQuery({
    queryKey: ["lab", strategyId],
    queryFn: () => api.gridSearchLab(strategyId),
    staleTime: 300_000,
  });

  const [params, setParams] = useState<Record<string, number>>({});

  useEffect(() => {
    if (labInfo?.param_grid) {
      const defaults: Record<string, number> = {};
      labInfo.param_grid.forEach((p) => {
        defaults[p.name] = p.default;
      });
      setParams(defaults);
    }
  }, [labInfo]);

  const gridMutation = useMutation({
    mutationFn: (payload: {
      strategy_id: string;
      symbols: string[];
      start: string;
      end: string;
      timeframe: string;
      starting_cash: number;
      max_combinations: number;
    }) => api.gridSearch(payload),
  });

  const singleMutation = useMutation({
    mutationFn: (payload: {
      strategy_id: string;
      symbols: string[];
      start: string;
      end: string;
      timeframe: string;
      starting_cash: number;
      params: Record<string, number>;
    }) => api.backtest(payload),
  });

  function handleAddSymbol(scrip: ScripInfo) {
    const current = symbols.split(",").map((s) => s.trim()).filter(Boolean);
    if (!current.includes(scrip.backend_symbol)) {
      setSymbols([...current, scrip.backend_symbol].join(","));
    }
  }

  function handleParamChange(name: string, value: number) {
    setParams((prev) => ({ ...prev, [name]: value }));
  }

  async function handleGridSearch(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const end = new Date();
    const start = new Date();
    start.setFullYear(end.getFullYear() - lookbackYears);

    gridMutation.mutate(
      {
        strategy_id: strategyId,
        symbols: symbols.split(",").map((s) => s.trim()).filter(Boolean),
        start: start.toISOString(),
        end: end.toISOString(),
        timeframe,
        starting_cash: startingCash,
        max_combinations: maxCombinations,
      },
      {
        onError: (err) => setError(err.message),
      }
    );
  }

  async function handleSingleRun(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const end = new Date();
    const start = new Date();
    start.setFullYear(end.getFullYear() - lookbackYears);

    singleMutation.mutate(
      {
        strategy_id: strategyId,
        symbols: symbols.split(",").map((s) => s.trim()).filter(Boolean),
        start: start.toISOString(),
        end: end.toISOString(),
        timeframe,
        starting_cash: startingCash,
        params,
      },
      {
        onError: (err) => setError(err.message),
      }
    );
  }

  const selectedStrategy = strategies.find((s) => s.id === strategyId);

  return (
    <Shell>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-medium text-white">Strategy Lab & Parameter Optimizer</h1>
          <p className="text-sm text-mute">
            Tune strategy parameters with grid search and visualize Sharpe heatmaps.
          </p>
        </div>
      </div>

      {/* Strategy & Universe Selection */}
      <form className="mb-6 space-y-4 rounded-lg border border-line bg-ink-900 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3">
          <span className="text-xs font-mono font-semibold uppercase tracking-wider text-gain">
            Step 1: Select Strategy & Asset Universe
          </span>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="text-xs font-mono text-mute">STRATEGY</label>
            <select
              value={strategyId}
              onChange={(e) => {
                setStrategyId(e.target.value);
                queryClient.invalidateQueries({ queryKey: ["lab", e.target.value] });
              }}
              className="mt-1 block w-full rounded-lg border border-line bg-ink-800 px-3 py-2 text-xs font-mono text-white"
            >
              {strategies.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
            {selectedStrategy && (
              <p className="mt-1 text-xs text-mute">{selectedStrategy.description}</p>
            )}
          </div>

          <div>
            <label className="text-xs font-mono text-mute">ASSET UNIVERSE (COMMA SEPARATED)</label>
            <SymbolSearch onSelect={handleAddSymbol} placeholder="Add scrip (e.g. RELIANCE, AAPL)..." />
            <input
              type="text"
              value={symbols}
              onChange={(e) => setSymbols(e.target.value)}
              className="mt-2 block w-full rounded-lg border border-line bg-ink-800 px-3 py-2 text-xs font-mono text-white"
            />
          </div>
        </div>

        <div className="grid grid-cols-4 gap-3">
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
          <div>
            <label className="text-xs font-mono text-mute">MAX COMBOS</label>
            <input
              type="number"
              value={maxCombinations}
              onChange={(e) => setMaxCombinations(Number(e.target.value))}
              min={10}
              max={500}
              className="mt-1 block w-full rounded-lg border border-line bg-ink-800 px-3 py-2 text-xs text-white font-mono"
            />
          </div>
        </div>
      </form>

      {/* Parameter Grid Visualization */}
      {labInfo && (
        <section className="mb-6 rounded-lg border border-line bg-ink-900 p-5">
          <div className="mb-4 flex items-center justify-between border-b border-line pb-3">
            <span className="text-xs font-mono font-semibold uppercase tracking-wider text-gain">
              Step 2: Parameter Space Explorer
            </span>
            <span className="text-xs font-mono text-mute">
              Drag sliders to set manual params, or click Grid Search to scan all combinations
            </span>
          </div>

          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {labInfo.param_grid.map((param) => (
              <ParamSlider
                key={param.name}
                param={param}
                value={params[param.name] ?? param.default}
                onChange={(val) => handleParamChange(param.name, val)}
              />
            ))}
          </div>

          <div className="mt-5 flex justify-end gap-3">
            <button
              type="button"
              disabled={singleMutation.isPending}
              onClick={handleSingleRun}
              className="rounded-lg border border-line bg-ink-800 px-5 py-2.5 text-xs font-bold font-mono text-white transition-all hover:bg-ink-700 disabled:opacity-50"
            >
              {singleMutation.isPending ? "Running..." : "Run with Current Params"}
            </button>
            <button
              type="button"
              disabled={gridMutation.isPending}
              onClick={handleGridSearch}
              className="rounded-lg bg-gain px-5 py-2.5 text-xs font-bold font-mono text-ink-950 transition-all hover:brightness-110 disabled:opacity-50"
            >
              {gridMutation.isPending ? "Scanning Grid..." : "Launch Grid Search"}
            </button>
          </div>
        </section>
      )}

      {error ? (
        <div className="mb-6 rounded-lg border border-loss/40 bg-loss/10 p-4 text-sm text-loss font-mono">
          {error}
        </div>
      ) : null}

      {/* Single Run Result */}
      {singleMutation.data && (
        <section className="mb-6 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-gain/40 bg-gain/5 p-5">
            <div>
              <span className="text-xs font-mono font-semibold uppercase tracking-wider text-gain">
                Manual Run Result
              </span>
              <div className="mt-1 text-lg font-medium text-white">
                Sharpe: <strong className="text-gain font-mono">{singleMutation.data.sharpe.toFixed(2)}</strong>
                {" | "}
                Return:{" "}
                <strong className={singleMutation.data.total_return_pct >= 0 ? "text-gain font-mono" : "text-loss font-mono"}>
                  {formatPct(singleMutation.data.total_return_pct)}
                </strong>
                {" | "}
                Max DD: <strong className="text-loss font-mono">{formatPct(-singleMutation.data.max_drawdown_pct)}</strong>
              </div>
            </div>
          </div>
          <div className="rounded-lg border border-line bg-ink-900 p-4">
            <h2 className="mb-3 text-sm font-medium text-white">Equity Curve</h2>
            <EquityChart data={singleMutation.data.equity_curve} />
          </div>
        </section>
      )}

      {/* Grid Search Results */}
      {gridMutation.data && (
        <section className="space-y-6">
          {/* Best Result Summary */}
          <div className="rounded-lg border border-gain/40 bg-gain/5 p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <span className="text-xs font-mono font-semibold uppercase tracking-wider text-gain">
                  Optimal Parameters Found
                </span>
                <div className="mt-1 font-mono text-xs text-white">
                  {Object.entries(gridMutation.data.best_params).map(([k, v]) => (
                    <span key={k} className="mr-3">
                      <span className="text-mute">{k}</span>
                      <strong className="text-gain ml-1">{String(v)}</strong>
                    </span>
                  ))}
                </div>
              </div>
              <div className="flex items-center gap-3 font-mono text-xs">
                <span className="rounded bg-ink-900 border border-line px-3 py-1.5">
                  Sharpe:{" "}
                  <strong className="text-gain">{gridMutation.data.best_result.sharpe.toFixed(2)}</strong>
                </span>
                <span className="rounded bg-ink-900 border border-line px-3 py-1.5">
                  Win Rate:{" "}
                  <strong className="text-gain">{(gridMutation.data.best_result.win_rate * 100).toFixed(1)}%</strong>
                </span>
                <span className="rounded bg-ink-900 border border-line px-3 py-1.5">
                  Combos:{" "}
                  <strong className="text-white">{gridMutation.data.combinations_tested}</strong>
                </span>
              </div>
            </div>
          </div>

          {/* KPIs */}
          <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-4">
            <Kpi
              label="Best Sharpe"
              value={gridMutation.data.best_result.sharpe.toFixed(2)}
              tone={gridMutation.data.best_result.sharpe >= 1.0 ? "gain" : "neutral"}
            />
            <Kpi
              label="Total Return"
              value={formatPct(gridMutation.data.best_result.total_return_pct)}
              tone={gridMutation.data.best_result.total_return_pct >= 0 ? "gain" : "loss"}
            />
            <Kpi
              label="Max Drawdown"
              value={formatPct(-gridMutation.data.best_result.max_drawdown_pct)}
              tone="loss"
            />
            <Kpi
              label="Profit Factor"
              value={gridMutation.data.best_result.profit_factor.toFixed(2)}
              tone={gridMutation.data.best_result.profit_factor >= 1.5 ? "gain" : "neutral"}
              hint={`${gridMutation.data.best_result.trades} trades`}
            />
          </div>

          {/* Sharpe Heatmap Grid */}
          <section className="rounded-lg border border-line bg-ink-900 p-4">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h2 className="text-sm font-medium text-white">Parameter Grid Search Heatmap</h2>
                <p className="text-xs text-mute">
                  Each cell is a unique parameter combination. Warmer green = higher Sharpe ratio.
                </p>
              </div>
              <span className="text-xs font-mono text-mute">
                Sorted by Sharpe descending
              </span>
            </div>
            <div className="grid gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
              {gridMutation.data.results.map((point, idx) => (
                <HeatmapCell key={idx} point={point} best={gridMutation.data.best_result} />
              ))}
            </div>
          </section>

          {/* Results Table */}
          <section className="overflow-x-auto rounded-lg border border-line bg-ink-900">
            <div className="border-b border-line p-3">
              <h2 className="text-sm font-medium text-white">All Parameter Combinations Ranked</h2>
            </div>
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-ink-950 uppercase text-mute">
                <tr>
                  <th className="px-3 py-2.5">Rank</th>
                  <th className="px-3 py-2.5">Parameters</th>
                  <th className="px-3 py-2.5">Sharpe</th>
                  <th className="px-3 py-2.5">Return</th>
                  <th className="px-3 py-2.5">Max DD</th>
                  <th className="px-3 py-2.5">Trades</th>
                  <th className="px-3 py-2.5">Win Rate</th>
                  <th className="px-3 py-2.5">Profit Factor</th>
                </tr>
              </thead>
              <tbody>
                {gridMutation.data.results.slice(0, 20).map((point, idx) => (
                  <tr
                    key={idx}
                    className={cn(
                      "border-t border-line hover:bg-ink-800/50",
                      idx === 0 && "bg-gain/5"
                    )}
                  >
                    <td className="px-3 py-2 text-mute">{idx + 1}</td>
                    <td className="px-3 py-2 text-white">
                      {Object.entries(point.params).map(([k, v]) => `${k}=${v}`).join(", ")}
                    </td>
                    <td
                      className={cn(
                        "px-3 py-2 font-semibold",
                        point.sharpe >= 1.0 ? "text-gain" : point.sharpe >= 0 ? "text-white" : "text-loss"
                      )}
                    >
                      {point.sharpe.toFixed(2)}
                    </td>
                    <td
                      className={cn(
                        "px-3 py-2 font-semibold",
                        point.total_return_pct >= 0 ? "text-gain" : "text-loss"
                      )}
                    >
                      {formatPct(point.total_return_pct)}
                    </td>
                    <td className="px-3 py-2 text-loss">{formatPct(-point.max_drawdown_pct)}</td>
                    <td className="px-3 py-2 text-mute">{point.trades}</td>
                    <td className="px-3 py-2">{(point.win_rate * 100).toFixed(1)}%</td>
                    <td className="px-3 py-2">{point.profit_factor.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </section>
      )}
    </Shell>
  );
}
