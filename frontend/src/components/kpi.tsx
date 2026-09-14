import { cn } from "@/lib/utils";

export function Kpi({
  label,
  value,
  hint,
  tone = "neutral",
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "neutral" | "gain" | "loss" | "warn";
}) {
  return (
    <div className="rounded-lg border border-line bg-ink-900 p-4">
      <div className="text-[11px] uppercase tracking-wider text-mute">{label}</div>
      <div
        className={cn(
          "mt-1 font-mono text-2xl",
          tone === "gain" && "text-gain",
          tone === "loss" && "text-loss",
          tone === "warn" && "text-warn",
        )}
      >
        {value}
      </div>
      {hint ? <div className="mt-1 text-xs text-mute">{hint}</div> : null}
    </div>
  );
}
