"use client";

import { useState } from "react";
import { EquityChart } from "@/components/equity-chart";
import { Kpi } from "@/components/kpi";
import { UnderwaterChart } from "@/components/underwater-chart";
import { formatPct, formatUsd } from "@/lib/utils";
import type { BacktestResult } from "@/types/trading";

interface BacktestVisualizerProps {
  result: BacktestResult;
}

export function BacktestVisualizer({ result }: BacktestVisualizerProps) {
  const [chartTab, setChartTab] = useState<"equity" | "underwater">("equity");
  const mc = result.monte_carlo;

  const totalTrades = result.trades || (result.winning_trades || 0) + (result.losing_trades || 0);
  const winRate = result.win_rate * 100.0;
  const profitFactor = result.profit_factor ?? 0.0;

  return (
    <div className="space-y-6">
      {/* Tear-sheet KPI Grid */}
      <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-6">
        <Kpi
          label="Total Return"
          value={formatPct(result.total_return_pct)}
          tone={result.total_return_pct >= 0 ? "gain" : "loss"}
          hint={result.cagr_pct ? `CAGR ${formatPct(result.cagr_pct)}` : undefined}
        />
        <Kpi
          label="Sharpe Ratio"
          value={result.sharpe.toFixed(2)}
          tone={result.sharpe >= 1.0 ? "gain" : result.sharpe < 0 ? "loss" : "neutral"}
          hint={result.sortino ? `Sortino ${result.sortino.toFixed(2)}` : undefined}
        />
        <Kpi
          label="Calmar Ratio"
          value={(result.calmar ?? 0.0).toFixed(2)}
          tone={(result.calmar ?? 0) >= 1.0 ? "gain" : "neutral"}
          hint={result.sortino ? `Sortino ${result.sortino.toFixed(2)}` : undefined}
        />
        <Kpi
          label="Max Drawdown"
          value={formatPct(-result.max_drawdown_pct)}
          tone="loss"
          hint={
            result.max_drawdown_duration_bars
              ? `${result.max_drawdown_duration_bars} bars recovery`
              : undefined
          }
        />
        <Kpi
          label="Win Rate"
          value={`${winRate.toFixed(1)}%`}
          tone={winRate >= 50 ? "gain" : "neutral"}
          hint={`${result.winning_trades ?? 0}W / ${result.losing_trades ?? 0}L`}
        />
        <Kpi
          label="Profit Factor"
          value={profitFactor > 0 ? profitFactor.toFixed(2) : "N/A"}
          tone={profitFactor >= 1.5 ? "gain" : profitFactor < 1.0 ? "loss" : "neutral"}
          hint={result.exposure_pct ? `Exposure ${result.exposure_pct.toFixed(1)}%` : undefined}
        />
      </div>

      {/* Chart Pane with Tabs */}
      <section className="rounded-lg border border-line bg-ink-900 p-4">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3">
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setChartTab("equity")}
              className={`rounded px-3 py-1 text-xs font-mono transition-colors ${
                chartTab === "equity"
                  ? "bg-gain/20 text-gain border border-gain/40"
                  : "bg-ink-800 text-mute hover:bg-ink-700"
              }`}
            >
              Equity Curve
            </button>
            <button
              type="button"
              onClick={() => setChartTab("underwater")}
              className={`rounded px-3 py-1 text-xs font-mono transition-colors ${
                chartTab === "underwater"
                  ? "bg-loss/20 text-loss border border-loss/40"
                  : "bg-ink-800 text-mute hover:bg-ink-700"
              }`}
            >
              Underwater Drawdown
            </button>
          </div>

          <div className="flex items-center gap-4 text-xs font-mono text-mute">
            <span>
              Ending Equity:{" "}
              <strong className="text-white">{formatUsd(result.ending_equity)}</strong>
            </span>
            <span>
              Total Signals: <strong className="text-white">{result.signals}</strong>
            </span>
          </div>
        </div>

        {chartTab === "equity" ? (
          <EquityChart data={result.equity_curve} />
        ) : (
          <UnderwaterChart data={result.equity_curve} />
        )}
      </section>

      {/* Monte Carlo Simulation & Trade Expectancy */}
      {mc && mc.simulations > 0 ? (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Monte Carlo Card */}
          <section className="rounded-lg border border-line bg-ink-900 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-medium text-white">
                Monte Carlo Bootstrap ({mc.simulations} Iterations)
              </h2>
              <span className="rounded bg-ink-800 px-2 py-0.5 text-xs font-mono text-mute">
                90% Confidence Band
              </span>
            </div>

            <p className="mb-4 text-xs text-mute">
              Resampled bootstrap paths across trade sequences to evaluate catastrophic drawdown
              risk and capital distribution.
            </p>

            <div className="grid grid-cols-3 gap-2 font-mono text-xs">
              <div className="rounded border border-line bg-ink-950 p-2.5">
                <div className="text-mute">5th %ile (Worst)</div>
                <div className="mt-1 font-semibold text-loss">{formatUsd(mc.equity_p5)}</div>
                <div className="text-[10px] text-mute">
                  DD: {mc.max_dd_p95 ? `${mc.max_dd_p95.toFixed(1)}%` : "N/A"}
                </div>
              </div>
              <div className="rounded border border-line bg-ink-950 p-2.5">
                <div className="text-mute">50th %ile (Median)</div>
                <div className="mt-1 font-semibold text-white">{formatUsd(mc.equity_p50)}</div>
                <div className="text-[10px] text-mute">
                  DD: {mc.max_dd_p50 ? `${mc.max_dd_p50.toFixed(1)}%` : "N/A"}
                </div>
              </div>
              <div className="rounded border border-line bg-ink-950 p-2.5">
                <div className="text-mute">95th %ile (Best)</div>
                <div className="mt-1 font-semibold text-gain">{formatUsd(mc.equity_p95)}</div>
                <div className="text-[10px] text-mute">
                  DD: {mc.max_dd_p5 ? `${mc.max_dd_p5.toFixed(1)}%` : "N/A"}
                </div>
              </div>
            </div>

            <div className="mt-4 flex items-center justify-between border-t border-line pt-3 text-xs font-mono">
              <span className="text-mute">Probability of Ruin (&gt;50% DD):</span>
              <span
                className={`font-semibold ${
                  (mc.ruin_probability_pct ?? 0) > 5 ? "text-loss" : "text-gain"
                }`}
              >
                {(mc.ruin_probability_pct ?? 0.0).toFixed(1)}%
              </span>
            </div>
          </section>

          {/* Trade Expectancy & Distribution */}
          <section className="rounded-lg border border-line bg-ink-900 p-4">
            <h2 className="mb-3 text-sm font-medium text-white">Trade & Payoff Expectancy</h2>
            <div className="space-y-3 font-mono text-xs">
              <div className="flex justify-between border-b border-line pb-2">
                <span className="text-mute">Executed Trades</span>
                <span className="text-white font-semibold">{totalTrades}</span>
              </div>
              <div className="flex justify-between border-b border-line pb-2">
                <span className="text-mute">Average Trade Return / Expectancy</span>
                <span
                  className={
                    (result.expectancy ?? 0) >= 0
                      ? "text-gain font-semibold"
                      : "text-loss font-semibold"
                  }
                >
                  {(result.expectancy ?? 0).toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between border-b border-line pb-2">
                <span className="text-mute">Average Winning Trade</span>
                <span className="text-gain font-semibold">{formatUsd(result.avg_win ?? 0)}</span>
              </div>
              <div className="flex justify-between border-b border-line pb-2">
                <span className="text-mute">Average Losing Trade</span>
                <span className="text-loss font-semibold">{formatUsd(result.avg_loss ?? 0)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-mute">Market Time In Exposure</span>
                <span className="text-white">{(result.exposure_pct ?? 0).toFixed(1)}%</span>
              </div>
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}
