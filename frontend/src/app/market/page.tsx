"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CandlestickChart } from "@/components/candlestick-chart";
import { QuoteTape } from "@/components/quote-tape";
import { Shell } from "@/components/shell";
import { api, getAccessToken } from "@/lib/api";
import { formatTs, formatUsd } from "@/lib/utils";
import type { Bar, Quote } from "@/types/trading";

export default function MarketPage() {
  const router = useRouter();
  const [symbols, setSymbols] = useState("SPY,QQQ,RELIANCE.NS");
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [bars, setBars] = useState<Bar[]>([]);
  const [focus, setFocus] = useState("SPY");
  const [lookback, setLookback] = useState(180);
  const [timeframe, setTimeframe] = useState("1d");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load(nextSymbols: string, nextFocus: string, nextLookback: number, nextTf = timeframe) {
    setBusy(true);
    setError(null);
    try {
      const [nextQuotes, nextBars] = await Promise.all([
        api.quotes(nextSymbols),
        api.bars(nextFocus, nextLookback, nextTf),
      ]);
      setQuotes(nextQuotes);
      setBars(nextBars);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Market fetch failed");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!getAccessToken()) {
      router.replace("/login");
      return;
    }
    load(symbols, focus, lookback, timeframe).catch((err: Error) => setError(err.message));
  }, [router]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const first = symbols.split(",")[0]?.trim().toUpperCase() || "SPY";
    const nextFocus = focus.trim().toUpperCase() || first;
    setFocus(nextFocus);
    await load(symbols, nextFocus, lookback, timeframe);
  }

  async function onSelectSymbol(sym: string) {
    setFocus(sym);
    await load(symbols, sym, lookback, timeframe);
  }

  return (
    <Shell>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-medium">Market Terminal & Technical Analysis</h1>
          <p className="text-sm text-mute">
            Live multi-asset data feeds, candlestick analytics, and indicator overlays.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {/* Timeframe Selector */}
          <div className="flex items-center gap-1 rounded-lg border border-line bg-ink-900 p-1">
            {["1m", "5m", "15m", "1h", "1d"].map((tf) => (
              <button
                key={tf}
                type="button"
                onClick={() => {
                  setTimeframe(tf);
                  load(symbols, focus, lookback, tf);
                }}
                className={`rounded px-2.5 py-1 text-xs font-mono transition-colors ${
                  timeframe === tf ? "bg-gain text-ink-950 font-bold" : "text-mute hover:text-white"
                }`}
              >
                {tf.toUpperCase()}
              </button>
            ))}
          </div>

          {/* Lookback Selector */}
          <div className="flex gap-1">
            {[60, 120, 180, 365].map((lb) => (
              <button
                key={lb}
                type="button"
                onClick={() => {
                  setLookback(lb);
                  load(symbols, focus, lb, timeframe);
                }}
                className={`rounded px-2.5 py-1 text-xs font-mono transition-colors ${
                  lookback === lb ? "bg-ink-700 text-white" : "bg-ink-900 text-mute hover:bg-ink-800"
                }`}
              >
                {lb}D
              </button>
            ))}
          </div>
        </div>
      </div>

      <form
        onSubmit={onSubmit}
        className="mb-6 flex flex-wrap items-end gap-3 rounded-lg border border-line bg-ink-900 p-4"
      >
        <label className="text-xs text-mute font-mono">
          WATCHLIST
          <input
            className="mt-1 block rounded border border-line bg-ink-800 px-3 py-2 text-sm text-white"
            value={symbols}
            onChange={(e) => setSymbols(e.target.value.toUpperCase())}
          />
        </label>
        <label className="text-xs text-mute font-mono">
          CHART FOCUS
          <input
            className="mt-1 block w-32 rounded border border-line bg-ink-800 px-3 py-2 text-sm text-white"
            value={focus}
            onChange={(e) => setFocus(e.target.value.toUpperCase())}
          />
        </label>
        <button
          disabled={busy}
          className="rounded bg-warn px-5 py-2 text-sm font-medium text-ink-950 transition-all hover:brightness-110 disabled:opacity-50"
        >
          {busy ? "Loading Feeds…" : "Fetch Market Data"}
        </button>
      </form>

      {error ? <p className="mb-6 rounded border border-loss/40 bg-loss/10 p-3 text-sm text-loss">{error}</p> : null}

      <div className="mb-6">
        <QuoteTape quotes={quotes} source={quotes[0]?.source} onSelectSymbol={onSelectSymbol} />
      </div>

      {bars.length > 0 ? (
        <section className="mb-6">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-medium text-white">
              {focus} Candlestick & Technical Indicator Workspace
            </h2>
            <span className="text-xs font-mono text-mute">
              Latest: <strong className="text-white">{formatUsd(bars[bars.length - 1].close)}</strong>
            </span>
          </div>
          <CandlestickChart
            bars={bars}
            height={420}
            showVolume={true}
            showSmaFast={true}
            showSmaSlow={true}
            showBollinger={false}
          />
        </section>
      ) : null}

      {bars.length > 0 ? (
        <section className="overflow-x-auto rounded-lg border border-line bg-ink-900">
          <div className="border-b border-line p-3">
            <h2 className="text-sm font-medium text-white">Recent OHLCV Bars ({focus})</h2>
          </div>
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-ink-950 uppercase text-mute">
              <tr>
                <th className="px-3 py-2.5">Date</th>
                <th className="px-3 py-2.5">Open</th>
                <th className="px-3 py-2.5">High</th>
                <th className="px-3 py-2.5">Low</th>
                <th className="px-3 py-2.5">Close</th>
                <th className="px-3 py-2.5">Volume</th>
              </tr>
            </thead>
            <tbody>
              {bars.slice(-10).reverse().map((bar) => {
                const isGain = bar.close >= bar.open;
                return (
                  <tr key={bar.timestamp} className="border-t border-line hover:bg-ink-800/50">
                    <td className="px-3 py-2 text-mute">{formatTs(bar.timestamp)}</td>
                    <td className="px-3 py-2">{formatUsd(bar.open)}</td>
                    <td className="px-3 py-2">{formatUsd(bar.high)}</td>
                    <td className="px-3 py-2">{formatUsd(bar.low)}</td>
                    <td className={`px-3 py-2 font-semibold ${isGain ? "text-gain" : "text-loss"}`}>
                      {formatUsd(bar.close)}
                    </td>
                    <td className="px-3 py-2 text-mute">{bar.volume ? bar.volume.toLocaleString() : "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      ) : null}
    </Shell>
  );
}
