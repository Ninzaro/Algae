"use client";

import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { EquityPoint } from "@/types/trading";
import { formatPct } from "@/lib/utils";

interface UnderwaterChartProps {
  data: EquityPoint[];
}

export function UnderwaterChart({ data }: { data: EquityPoint[] }) {
  const points = data.map((p) => ({
    t: new Date(p.timestamp).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    drawdown: -Math.abs(p.drawdown_pct),
  }));

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={points}>
          <defs>
            <linearGradient id="drawdownGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#ff5c5c" stopOpacity={0} />
              <stop offset="100%" stopColor="#ff5c5c" stopOpacity={0.4} />
            </linearGradient>
          </defs>
          <XAxis dataKey="t" tick={{ fill: "#8b9bb4", fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis
            tick={{ fill: "#8b9bb4", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            domain={["auto", 0]}
            tickFormatter={(v: number) => `${v.toFixed(1)}%`}
          />
          <Tooltip
            contentStyle={{ background: "#121821", border: "1px solid #243044", fontSize: 12 }}
            formatter={(value) => [formatPct(Number(value)), "Underwater Drawdown"]}
          />
          <Area
            type="monotone"
            dataKey="drawdown"
            stroke="#ff5c5c"
            fill="url(#drawdownGrad)"
            strokeWidth={1.5}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
