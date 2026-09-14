"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { SymbolSearch } from "@/components/symbol-search";
import { api } from "@/lib/api";
import { formatPct, formatUsd } from "@/lib/utils";
import type { BasketInfo, Quote, ScripInfo } from "@/types/trading";

interface WatchlistProps {
  initialQuotes?: Quote[];
  onSelectScrip?: (scrip: { symbol: string; backend_symbol?: string }) => void;
}

export function Watchlist({ initialQuotes = [], onSelectScrip }: WatchlistProps) {
  const router = useRouter();
  const [baskets, setBaskets] = useState<BasketInfo[]>([]);
  const [activeBasket, setActiveBasket] = useState<string>("nifty50");
  const [customSymbols, setCustomSymbols] = useState<string[]>(["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS"]);
  const [quotes, setQuotes] = useState<Quote[]>(initialQuotes);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api
      .baskets()
      .then((b) => setBaskets(b))
      .catch(() => {});
  }, []);

  useEffect(() => {
    let symbolsToFetch: string[] = [];
    if (activeBasket === "custom") {
      symbolsToFetch = customSymbols;
    } else {
      const found = baskets.find((b) => b.id === activeBasket);
      if (found) {
        symbolsToFetch = found.symbols.slice(0, 15); // Show top constituents
      } else if (activeBasket === "nifty50") {
        symbolsToFetch = [
          "RELIANCE.NS",
          "TCS.NS",
          "HDFCBANK.NS",
          "ICICIBANK.NS",
          "INFY.NS",
          "BHARTIARTL.NS",
          "ITC.NS",
          "SBIN.NS",
          "LT.NS",
          "TATAMOTORS.NS",
          "SUNPHARMA.NS",
          "MARUTI.NS",
        ];
      }
    }

    if (symbolsToFetch.length > 0) {
      setLoading(true);
      api
        .quotes(symbolsToFetch.join(","))
        .then((q) => setQuotes(q))
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [activeBasket, baskets, customSymbols]);

  function handleAddScrip(scrip: ScripInfo) {
    if (!customSymbols.includes(scrip.backend_symbol)) {
      const next = [...customSymbols, scrip.backend_symbol];
      setCustomSymbols(next);
      setActiveBasket("custom");
    }
  }

  function handleRemoveScrip(sym: string, e: React.MouseEvent) {
    e.stopPropagation();
    setCustomSymbols((prev) => prev.filter((s) => s !== sym));
  }

  function handleRowClick(symbol: string, backendSymbol: string) {
    if (onSelectScrip) {
      onSelectScrip({ symbol, backend_symbol: backendSymbol });
    } else {
      router.push(`/market?focus=${encodeURIComponent(symbol)}`);
    }
  }

  return (
    <section className="rounded-lg border border-line bg-ink-900 p-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-medium text-white">Market Watchlist & Indices</h2>
          <p className="text-xs text-mute">
            Live prices across Nifty 50, 100, 150, 250 baskets and US Tech
          </p>
        </div>

        {/* Scrip Search without .NS */}
        <div className="w-full sm:w-72">
          <SymbolSearch onSelect={handleAddScrip} placeholder="Search scrip to add..." />
        </div>
      </div>

      {/* Basket Tabs */}
      <div className="mb-4 flex flex-wrap gap-1.5 border-b border-line pb-3 text-xs font-mono">
        <button
          type="button"
          onClick={() => setActiveBasket("nifty50")}
          className={`rounded px-3 py-1.5 transition-colors ${
            activeBasket === "nifty50"
              ? "bg-ink-700 font-semibold text-white"
              : "text-mute hover:bg-ink-800 hover:text-white"
          }`}
        >
          NIFTY 50
        </button>
        <button
          type="button"
          onClick={() => setActiveBasket("nifty100")}
          className={`rounded px-3 py-1.5 transition-colors ${
            activeBasket === "nifty100"
              ? "bg-ink-700 font-semibold text-white"
              : "text-mute hover:bg-ink-800 hover:text-white"
          }`}
        >
          NIFTY 100
        </button>
        <button
          type="button"
          onClick={() => setActiveBasket("nifty150")}
          className={`rounded px-3 py-1.5 transition-colors ${
            activeBasket === "nifty150"
              ? "bg-ink-700 font-semibold text-white"
              : "text-mute hover:bg-ink-800 hover:text-white"
          }`}
        >
          MIDCAP 150
        </button>
        <button
          type="button"
          onClick={() => setActiveBasket("nifty250")}
          className={`rounded px-3 py-1.5 transition-colors ${
            activeBasket === "nifty250"
              ? "bg-ink-700 font-semibold text-white"
              : "text-mute hover:bg-ink-800 hover:text-white"
          }`}
        >
          SMALLCAP 250
        </button>
        <button
          type="button"
          onClick={() => setActiveBasket("us_tech")}
          className={`rounded px-3 py-1.5 transition-colors ${
            activeBasket === "us_tech"
              ? "bg-ink-700 font-semibold text-white"
              : "text-mute hover:bg-ink-800 hover:text-white"
          }`}
        >
          US TECH
        </button>
        <button
          type="button"
          onClick={() => setActiveBasket("custom")}
          className={`rounded px-3 py-1.5 transition-colors ${
            activeBasket === "custom"
              ? "bg-gain/20 text-gain border border-gain/40 font-semibold"
              : "text-mute hover:bg-ink-800 hover:text-white"
          }`}
        >
          MY WATCHLIST ({customSymbols.length})
        </button>
      </div>

      {/* Stock Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-mono">
          <thead className="bg-ink-950 uppercase text-mute">
            <tr>
              <th className="px-3 py-2.5">Scrip</th>
              <th className="px-3 py-2.5">LTP</th>
              <th className="px-3 py-2.5">Day Change</th>
              <th className="px-3 py-2.5">% Change</th>
              <th className="px-3 py-2.5">Prev Close</th>
              {activeBasket === "custom" ? <th className="px-3 py-2.5 text-right">Action</th> : null}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="py-6 text-center text-mute animate-pulse">
                  Updating live prices…
                </td>
              </tr>
            ) : quotes.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-6 text-center text-mute">
                  No quotes found. Use the search box above to add scrips.
                </td>
              </tr>
            ) : (
              quotes.map((q) => {
                const isPositive = q.change >= 0;
                const cleanSym = q.symbol.replace(".NS", "").replace(".BO", "");
                return (
                  <tr
                    key={q.symbol}
                    onClick={() => handleRowClick(cleanSym, q.symbol)}
                    className="border-t border-line cursor-pointer transition-colors hover:bg-ink-800/60"
                  >
                    <td className="px-3 py-2.5">
                      <span className="font-semibold text-white">{cleanSym}</span>
                      <span className="ml-1.5 text-[10px] text-mute">
                        {q.symbol.includes(".NS") ? "NSE" : "US"}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 font-semibold text-white">
                      {formatUsd(q.price)}
                    </td>
                    <td
                      className={`px-3 py-2.5 font-medium ${
                        isPositive ? "text-gain" : "text-loss"
                      }`}
                    >
                      {isPositive ? "+" : ""}
                      {formatUsd(q.change)}
                    </td>
                    <td className="px-3 py-2.5">
                      <span
                        className={`rounded px-1.5 py-0.5 font-semibold ${
                          isPositive ? "bg-gain/15 text-gain" : "bg-loss/15 text-loss"
                        }`}
                      >
                        {formatPct(q.change_pct)}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-mute">{formatUsd(q.prev_close)}</td>
                    {activeBasket === "custom" ? (
                      <td className="px-3 py-2.5 text-right">
                        <button
                          type="button"
                          onClick={(e) => handleRemoveScrip(q.symbol, e)}
                          className="rounded px-1.5 py-0.5 text-mute hover:bg-loss/20 hover:text-loss"
                        >
                          ✕
                        </button>
                      </td>
                    ) : null}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
