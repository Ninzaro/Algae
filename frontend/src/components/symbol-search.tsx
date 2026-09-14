"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { ScripInfo } from "@/types/trading";

interface SymbolSearchProps {
  onSelect: (scrip: ScripInfo) => void;
  placeholder?: string;
  className?: string;
}

export function SymbolSearch({
  onSelect,
  placeholder = "Search scrips (e.g. RELIANCE, TCS, HDFCBANK, SPY)...",
  className = "",
}: SymbolSearchProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ScripInfo[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      setIsOpen(false);
      return;
    }

    const timer = setTimeout(() => {
      setLoading(true);
      api
        .search(query, 12)
        .then((items) => {
          setResults(items);
          setIsOpen(items.length > 0);
        })
        .catch(() => setResults([]))
        .finally(() => setLoading(false));
    }, 150);

    return () => clearTimeout(timer);
  }, [query]);

  // Click outside to close dropdown
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function handleSelect(scrip: ScripInfo) {
    onSelect(scrip);
    setQuery("");
    setIsOpen(false);
  }

  return (
    <div ref={dropdownRef} className={`relative ${className}`}>
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => query.trim() && results.length > 0 && setIsOpen(true)}
          placeholder={placeholder}
          className="w-full rounded-lg border border-line bg-ink-800 px-3.5 py-2 text-sm text-white placeholder-mute transition-colors focus:border-gain focus:outline-none"
        />
        {loading ? (
          <div className="absolute right-3 top-2.5 text-xs text-mute animate-pulse font-mono">
            Searching…
          </div>
        ) : null}
      </div>

      {isOpen && (
        <div className="absolute z-50 mt-1 max-h-64 w-full overflow-y-auto rounded-lg border border-line bg-ink-900 shadow-2xl">
          {results.map((scrip) => (
            <button
              key={`${scrip.exchange}-${scrip.symbol}`}
              type="button"
              onClick={() => handleSelect(scrip)}
              className="flex w-full items-center justify-between border-b border-line/40 px-3.5 py-2.5 text-left text-xs transition-colors hover:bg-ink-800"
            >
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono font-semibold text-white">{scrip.symbol}</span>
                  <span className="rounded bg-ink-950 px-1.5 py-0.5 text-[10px] font-mono text-mute">
                    {scrip.exchange}
                  </span>
                </div>
                <div className="text-[11px] text-mute">{scrip.name}</div>
              </div>
              {scrip.sector ? (
                <span className="text-[10px] text-mute/80">{scrip.sector}</span>
              ) : null}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
