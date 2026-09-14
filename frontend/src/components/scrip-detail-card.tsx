"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CandlestickChart } from "@/components/candlestick-chart";
import { api } from "@/lib/api";
import { formatPct, formatUsd } from "@/lib/utils";
import type { Bar, Quote, ScripInfo } from "@/types/trading";

interface ScripDetailCardProps {
  scrip: ScripInfo | { symbol: string; backend_symbol?: string; name?: string; exchange?: string; sector?: string };
  onClose?: () => void;
}

export function ScripDetailCard({ scrip, onClose }: ScripDetailCardProps) {
  const router = useRouter();
  const [bars, setBars] = useState<Bar[]>([]);
  const [quote, setQuote] = useState<Quote | null>(null);
  const [lookback, setLookback] = useState(120);
  const [timeframe, setTimeframe] = useState("1d");
  const [loading, setLoading] = useState(true);

  const cleanSymbol = scrip.symbol.replace(".NS", "").replace(".BO", "");
  const backendSymbol = scrip.backend_symbol || (scrip.exchange === "US" ? cleanSymbol : `${cleanSymbol}.NS`);

  useEffect(() => {
    let mounted = true;
    setLoading(true);

    Promise.all([
      api.bars(backendSymbol, lookback, timeframe).catch(() => []),
      api.quotes(backendSymbol).catch(() => []),
    ])
      .then(([bList, qList]) => {
        if (!mounted) return;
        setBars(bList);
        if (qList && qList.length > 0) {
          setQuote(qList[0]);
        }
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [backendSymbol, lookback, timeframe]);

  const ltp = quote ? quote.price : bars.length > 0 ? bars[bars.length - 1].close : 0;
  const change = quote ? quote.change : 0;
  const changePct = quote ? quote.change_pct : 0;
  const isPositive = change >= 0;

  // Calculate technical summary stats
  const highLow = bars.reduce(
    (acc, b) => ({
      high: Math.max(acc.high, b.high),
      low: Math.min(acc.low, b.low),
    }),
    { high: -Infinity, low: Infinity },
  );

  const latestBar = bars.length > 0 ? bars[bars.length - 1] : null;

  function handleLaunchBacktest() {
    router.push(`/backtests?symbol=${encodeURIComponent(backendSymbol)}`);
  }

  return (
    <div className="rounded-xl border border-line bg-ink-900 p-5 shadow-2xl transition-all">
      {/* Top Header */}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-line pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold font-mono text-white">{cleanSymbol}</h2>
            <span className="rounded bg-ink-800 px-2 py-0.5 text-xs font-mono text-mute">
              {scrip.exchange || (scrip.symbol.includes(".NS") ? "NSE" : "US")}
            </span>
            {scrip.sector ? (
              <span className="text-xs text-mute/80">· {scrip.sector}</span>
            ) : null}
          </div>
          <p className="text-xs text-mute">{scrip.name || cleanSymbol}</p>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right font-mono">
            <div className="text-xl font-bold text-white">{formatUsd(ltp)}</div>
            <div className={`text-xs font-semibold ${isPositive ? "text-gain" : "text-loss"}`}>
              {isPositive ? "+" : ""}
              {formatUsd(change)} ({formatPct(changePct)})
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleLaunchBacktest}
              className="rounded-lg bg-gain px-3.5 py-1.5 text-xs font-bold font-mono text-ink-950 transition-all hover:brightness-110"
            >
              🚀 Launch Backtest
            </button>
            {onClose ? (
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg border border-line bg-ink-800 px-2.5 py-1.5 text-xs text-mute hover:bg-ink-700 hover:text-white"
              >
                ✕ Close
              </button>
            ) : null}
          </div>
        </div>
      </div>

      {/* Mini Stats Bar */}
      <div className="mb-5 grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-6 font-mono text-xs">
        <div className="rounded-lg border border-line bg-ink-950 p-2.5">
          <div className="text-[10px] text-mute uppercase">Today's High</div>
          <div className="mt-1 font-semibold text-white">
            {latestBar ? formatUsd(latestBar.high) : "—"}
          </div>
        </div>
        <div className="rounded-lg border border-line bg-ink-950 p-2.5">
          <div className="text-[10px] text-mute uppercase">Today's Low</div>
          <div className="mt-1 font-semibold text-white">
            {latestBar ? formatUsd(latestBar.low) : "—"}
          </div>
        </div>
        <div className="rounded-lg border border-line bg-ink-950 p-2.5">
          <div className="text-[10px] text-mute uppercase">{lookback}D High</div>
          <div className="mt-1 font-semibold text-gain">
            {highLow.high > -Infinity ? formatUsd(highLow.high) : "—"}
          </div>
        </div>
        <div className="rounded-lg border border-line bg-ink-950 p-2.5">
          <div className="text-[10px] text-mute uppercase">{lookback}D Low</div>
          <div className="mt-1 font-semibold text-loss">
            {highLow.low < Infinity ? formatUsd(highLow.low) : "—"}
          </div>
        </div>
        <div className="rounded-lg border border-line bg-ink-950 p-2.5">
          <div className="text-[10px] text-mute uppercase">Volume</div>
          <div className="mt-1 font-semibold text-white">
            {latestBar && latestBar.volume ? latestBar.volume.toLocaleString() : "—"}
          </div>
        </div>
        <div className="rounded-lg border border-line bg-ink-950 p-2.5">
          <div className="text-[10px] text-mute uppercase">Timeframe & Horizon</div>
          <div className="mt-1 flex flex-wrap gap-1 text-[11px]">
            {["1m", "5m", "15m", "1h", "1d"].map((tf) => (
              <button
                key={tf}
                type="button"
                onClick={() => setTimeframe(tf)}
                className={`rounded px-1.5 py-0.5 ${
                  timeframe === tf ? "bg-gain text-ink-950 font-bold" : "text-mute hover:text-white"
                }`}
              >
                {tf.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Interactive Candlestick Chart */}
      {loading ? (
        <div className="flex h-72 items-center justify-center text-sm font-mono text-mute animate-pulse">
          Loading OHLCV candles & technical indicators…
        </div>
      ) : bars.length > 0 ? (
        <CandlestickChart
          bars={bars}
          height={340}
          showVolume={true}
          showSmaFast={true}
          showSmaSlow={true}
          showBollinger={false}
        />
      ) : (
        <div className="py-8 text-center text-sm text-mute font-mono">
          No historical candle data found for {cleanSymbol}.
        </div>
      )}
    </div>
  );
}
