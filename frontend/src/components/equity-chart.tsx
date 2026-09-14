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
import { formatInr } from "@/lib/utils";

export function EquityChart({ data }: { data: EquityPoint[] }) {
  const points = data.map((p) => ({
    t: new Date(p.timestamp).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    equity: p.equity,
  }));

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={points}>
          <defs>
            <linearGradient id="eq" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3dd68c" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#3dd68c" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="t" tick={{ fill: "#8b9bb4", fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis
            tick={{ fill: "#8b9bb4", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => `₹${(v / 1000).toFixed(0)}k`}
          />
          <Tooltip
            contentStyle={{ background: "#121821", border: "1px solid #243044", fontSize: 12 }}
            formatter={(value) => [formatInr(Number(value)), "Equity"]}
          />
          <Area type="monotone" dataKey="equity" stroke="#3dd68c" fill="url(#eq)" strokeWidth={1.6} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
