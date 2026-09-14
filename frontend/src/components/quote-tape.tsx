import { formatPct, formatUsd } from "@/lib/utils";
import type { Quote } from "@/types/trading";

export function QuoteTape({
  quotes,
  source,
  onSelectSymbol,
}: {
  quotes: Quote[];
  source?: string;
  onSelectSymbol?: (symbol: string) => void;
}) {
  if (quotes.length === 0) {
    return (
      <p className="text-sm text-mute">
        No market prints yet — run a cycle or open Market.
      </p>
    );
  }
  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm text-mute">Live Ticker Tape</h2>
        {source ? <span className="font-mono text-xs text-mute">{source}</span> : null}
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {quotes.map((quote) => (
          <div
            key={quote.symbol}
            onClick={() => onSelectSymbol?.(quote.symbol)}
            className={`rounded-lg border border-line bg-ink-900 p-4 transition-all ${
              onSelectSymbol ? "cursor-pointer hover:border-gain/40 hover:bg-ink-850" : ""
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-white">
                {quote.symbol}
              </span>
              <span
                className={`font-mono text-xs font-medium ${
                  quote.change >= 0 ? "text-gain" : "text-loss"
                }`}
              >
                {formatPct(quote.change_pct)}
              </span>
            </div>
            <div className="mt-2 font-mono text-xl font-medium text-white">
              {formatUsd(quote.price)}
            </div>
            <div
              className={`mt-1 font-mono text-xs ${
                quote.change >= 0 ? "text-gain" : "text-loss"
              }`}
            >
              {quote.change >= 0 ? "+" : ""}
              {formatUsd(quote.change)} today
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
