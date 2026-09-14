"use client";

import { useEffect, useRef, useState } from "react";
import {
  ColorType,
  createChart,
  CrosshairMode,
  IChartApi,
  ISeriesApi,
  UTCTimestamp,
} from "lightweight-charts";
import type { Bar } from "@/types/trading";

export interface ChartMarker {
  timestamp: string;
  side: "buy" | "sell" | "flat";
  price?: number;
  label?: string;
}

interface CandlestickChartProps {
  bars: Bar[];
  markers?: ChartMarker[];
  height?: number;
  showVolume?: boolean;
  showSmaFast?: boolean;
  showSmaSlow?: boolean;
  showBollinger?: boolean;
  fastPeriod?: number;
  slowPeriod?: number;
}

function toUtcTimestamp(isoString: string): UTCTimestamp {
  return Math.floor(new Date(isoString).getTime() / 1000) as UTCTimestamp;
}

function calculateSma(data: { time: UTCTimestamp; value: number }[], window: number) {
  const result: { time: UTCTimestamp; value: number }[] = [];
  for (let i = window - 1; i < data.length; i++) {
    let sum = 0;
    for (let j = 0; j < window; j++) {
      sum += data[i - j].value;
    }
    result.push({ time: data[i].time, value: sum / window });
  }
  return result;
}

function calculateBollinger(
  data: { time: UTCTimestamp; value: number }[],
  window: number = 20,
  stdDevMult: number = 2.0,
) {
  const upper: { time: UTCTimestamp; value: number }[] = [];
  const lower: { time: UTCTimestamp; value: number }[] = [];

  for (let i = window - 1; i < data.length; i++) {
    let sum = 0;
    for (let j = 0; j < window; j++) {
      sum += data[i - j].value;
    }
    const mean = sum / window;
    let varianceSum = 0;
    for (let j = 0; j < window; j++) {
      varianceSum += Math.pow(data[i - j].value - mean, 2);
    }
    const std = Math.sqrt(varianceSum / window);
    upper.push({ time: data[i].time, value: mean + stdDevMult * std });
    lower.push({ time: data[i].time, value: mean - stdDevMult * std });
  }
  return { upper, lower };
}

export function CandlestickChart({
  bars,
  markers = [],
  height = 360,
  showVolume = true,
  showSmaFast = true,
  showSmaSlow = true,
  showBollinger = false,
  fastPeriod = 10,
  slowPeriod = 30,
}: CandlestickChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<IChartApi | null>(null);
  const [activeIndicators, setActiveIndicators] = useState({
    fast: showSmaFast,
    slow: showSmaSlow,
    bb: showBollinger,
    vol: showVolume,
  });

  useEffect(() => {
    if (!chartContainerRef.current || bars.length === 0) return;

    // Deduplicate and sort bars by timestamp ascending
    const sorted = [...bars].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
    );

    const uniqueBars: Bar[] = [];
    const seenTimes = new Set<number>();
    for (const b of sorted) {
      const ts = toUtcTimestamp(b.timestamp);
      if (!seenTimes.has(ts)) {
        seenTimes.add(ts);
        uniqueBars.push(b);
      }
    }

    if (uniqueBars.length === 0) return;

    // Clean up previous instance
    if (chartInstanceRef.current) {
      chartInstanceRef.current.remove();
      chartInstanceRef.current = null;
    }

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height,
      layout: {
        background: { type: ColorType.Solid, color: "#0d1117" },
        textColor: "#8b9bb4",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "rgba(36, 48, 68, 0.45)" },
        horzLines: { color: "rgba(36, 48, 68, 0.45)" },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: "#38bdf8", width: 1, style: 3 },
        horzLine: { color: "#38bdf8", width: 1, style: 3 },
      },
      rightPriceScale: {
        borderColor: "#243044",
        scaleMargins: {
          top: 0.1,
          bottom: activeIndicators.vol ? 0.25 : 0.1,
        },
      },
      timeScale: {
        borderColor: "#243044",
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartInstanceRef.current = chart;

    // Candlestick series
    const candleSeries = chart.addCandlestickSeries({
      upColor: "#3dd68c",
      downColor: "#ff5c5c",
      borderUpColor: "#3dd68c",
      borderDownColor: "#ff5c5c",
      wickUpColor: "#3dd68c",
      wickDownColor: "#ff5c5c",
    });

    const candleData = uniqueBars.map((b) => ({
      time: toUtcTimestamp(b.timestamp),
      open: b.open,
      high: b.high,
      low: b.low,
      close: b.close,
    }));

    candleSeries.setData(candleData);

    // Volume series
    if (activeIndicators.vol) {
      const volumeSeries = chart.addHistogramSeries({
        color: "#26a69a",
        priceFormat: {
          type: "volume",
        },
        priceScaleId: "",
      });

      volumeSeries.priceScale().applyOptions({
        scaleMargins: {
          top: 0.8,
          bottom: 0,
        },
      });

      const volumeData = uniqueBars.map((b) => ({
        time: toUtcTimestamp(b.timestamp),
        value: b.volume || 0,
        color: b.close >= b.open ? "rgba(61, 214, 140, 0.35)" : "rgba(255, 92, 92, 0.35)",
      }));

      volumeSeries.setData(volumeData);
    }

    const closeData = uniqueBars.map((b) => ({
      time: toUtcTimestamp(b.timestamp),
      value: b.close,
    }));

    // SMA Fast Overlay
    if (activeIndicators.fast && uniqueBars.length >= fastPeriod) {
      const smaFastSeries = chart.addLineSeries({
        color: "#38bdf8",
        lineWidth: 2,
        title: `SMA ${fastPeriod}`,
      });
      smaFastSeries.setData(calculateSma(closeData, fastPeriod));
    }

    // SMA Slow Overlay
    if (activeIndicators.slow && uniqueBars.length >= slowPeriod) {
      const smaSlowSeries = chart.addLineSeries({
        color: "#f59e0b",
        lineWidth: 2,
        title: `SMA ${slowPeriod}`,
      });
      smaSlowSeries.setData(calculateSma(closeData, slowPeriod));
    }

    // Bollinger Bands Overlay
    if (activeIndicators.bb && uniqueBars.length >= 20) {
      const { upper, lower } = calculateBollinger(closeData, 20, 2.0);
      const upperSeries = chart.addLineSeries({
        color: "rgba(168, 85, 247, 0.75)",
        lineWidth: 1,
        lineStyle: 2,
        title: "BB Upper",
      });
      const lowerSeries = chart.addLineSeries({
        color: "rgba(168, 85, 247, 0.75)",
        lineWidth: 1,
        lineStyle: 2,
        title: "BB Lower",
      });
      upperSeries.setData(upper);
      lowerSeries.setData(lower);
    }

    // Trade and signal markers
    if (markers.length > 0) {
      const chartMarkers = markers
        .filter((m) => seenTimes.has(toUtcTimestamp(m.timestamp)))
        .map((m) => {
          const isBuy = m.side === "buy";
          const isSell = m.side === "sell";
          return {
            time: toUtcTimestamp(m.timestamp),
            position: isBuy ? ("belowBar" as const) : ("aboveBar" as const),
            color: isBuy ? "#3dd68c" : isSell ? "#ff5c5c" : "#8b9bb4",
            shape: isBuy
              ? ("arrowUp" as const)
              : isSell
                ? ("arrowDown" as const)
                : ("circle" as const),
            text: m.label || (isBuy ? "BUY" : isSell ? "SELL" : "FLAT"),
          };
        });

      // Sort markers chronologically
      chartMarkers.sort((a, b) => Number(a.time) - Number(b.time));
      candleSeries.setMarkers(chartMarkers);
    }

    chart.timeScale().fitContent();

    // Handle responsive resize
    const handleResize = () => {
      if (chartContainerRef.current && chartInstanceRef.current) {
        chartInstanceRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      if (chartInstanceRef.current) {
        chartInstanceRef.current.remove();
        chartInstanceRef.current = null;
      }
    };
  }, [bars, markers, height, activeIndicators, fastPeriod, slowPeriod]);

  return (
    <div className="relative w-full rounded-lg border border-line bg-[#0d1117] p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2 border-b border-line pb-2">
        <div className="flex items-center gap-2 text-xs font-mono text-mute">
          <span className="font-semibold text-white">OHLCV Multi-Pane</span>
          <span>· {bars.length} bars</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs font-mono">
          <button
            type="button"
            onClick={() => setActiveIndicators((prev) => ({ ...prev, fast: !prev.fast }))}
            className={`rounded px-2 py-0.5 transition-colors ${
              activeIndicators.fast
                ? "bg-[#38bdf8]/20 text-[#38bdf8] border border-[#38bdf8]/40"
                : "bg-ink-800 text-mute hover:bg-ink-700"
            }`}
          >
            SMA {fastPeriod}
          </button>
          <button
            type="button"
            onClick={() => setActiveIndicators((prev) => ({ ...prev, slow: !prev.slow }))}
            className={`rounded px-2 py-0.5 transition-colors ${
              activeIndicators.slow
                ? "bg-[#f59e0b]/20 text-[#f59e0b] border border-[#f59e0b]/40"
                : "bg-ink-800 text-mute hover:bg-ink-700"
            }`}
          >
            SMA {slowPeriod}
          </button>
          <button
            type="button"
            onClick={() => setActiveIndicators((prev) => ({ ...prev, bb: !prev.bb }))}
            className={`rounded px-2 py-0.5 transition-colors ${
              activeIndicators.bb
                ? "bg-purple-500/20 text-purple-400 border border-purple-500/40"
                : "bg-ink-800 text-mute hover:bg-ink-700"
            }`}
          >
            Bollinger (20,2)
          </button>
          <button
            type="button"
            onClick={() => setActiveIndicators((prev) => ({ ...prev, vol: !prev.vol }))}
            className={`rounded px-2 py-0.5 transition-colors ${
              activeIndicators.vol
                ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
                : "bg-ink-800 text-mute hover:bg-ink-700"
            }`}
          >
            Volume
          </button>
        </div>
      </div>
      <div ref={chartContainerRef} className="w-full" style={{ height }} />
    </div>
  );
}
