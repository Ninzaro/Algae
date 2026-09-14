"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  Bar,
  BasketInfo,
  DashboardSnapshot,
  JournalEntry,
  Quote,
  ScripInfo,
  ScreenerRequest,
  ScreenerResponse,
  StrategyView,
} from "@/types/trading";

export function useDashboard(initial: DashboardSnapshot | null = null) {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api.dashboard(),
    initialData: initial ?? undefined,
    staleTime: 30_000,
  });
}

export function useStrategies() {
  return useQuery({
    queryKey: ["strategies"],
    queryFn: () => api.strategies(),
    staleTime: 60_000,
  });
}

export function useQuotes(symbols: string) {
  return useQuery({
    queryKey: ["quotes", symbols],
    queryFn: () => api.quotes(symbols),
    enabled: symbols.length > 0,
    staleTime: 15_000,
  });
}

export function useBars(symbol: string, lookback: number, timeframe: string) {
  return useQuery({
    queryKey: ["bars", symbol, lookback, timeframe],
    queryFn: () => api.bars(symbol, lookback, timeframe),
    enabled: !!symbol,
    staleTime: 30_000,
  });
}

export function useSearch(query: string) {
  return useQuery({
    queryKey: ["search", query],
    queryFn: () => api.search(query),
    enabled: query.length >= 2,
    staleTime: 60_000,
  });
}

export function useBaskets() {
  return useQuery({
    queryKey: ["baskets"],
    queryFn: () => api.baskets(),
    staleTime: 300_000,
  });
}

export function useJournal() {
  return useQuery({
    queryKey: ["journal"],
    queryFn: () => api.journal(),
    staleTime: 10_000,
  });
}

export function useScreenerScan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ScreenerRequest) => api.screenerScan(payload),
    onSuccess: (data) => {
      queryClient.setQueryData(["screener"], data);
    },
  });
}

export function useToggleStrategy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      api.toggleStrategy(id, enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["strategies"] });
    },
  });
}

export function useRunCycle() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.runCycle(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useKillSwitch() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (active: boolean) => api.killSwitch(active),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useBacktest() {
  return useMutation({
    mutationFn: (payload: {
      strategy_id: string;
      symbols: string[];
      start: string;
      end: string;
      timeframe?: string;
      starting_cash?: number;
    }) => api.backtest(payload),
  });
}

export function useWalkForward() {
  return useMutation({
    mutationFn: (payload: {
      strategy_id: string;
      symbols: string[];
      start: string;
      end: string;
      train_bars: number;
      test_bars: number;
      step_bars: number;
      anchored: boolean;
      timeframe?: string;
      starting_cash?: number;
    }) => api.walkForward(payload),
  });
}

export function usePortfolioBlend() {
  return useMutation({
    mutationFn: api.portfolioBlend,
  });
}
