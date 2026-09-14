export type OrderSide = "buy" | "sell";
export type SignalSide = "buy" | "sell" | "flat";
export type OrderStatus =
  | "pending"
  | "submitted"
  | "partially_filled"
  | "filled"
  | "cancelled"
  | "rejected";

export interface AccountSnapshot {
  cash: number;
  equity: number;
  buying_power: number;
  peak_equity: number;
  daily_start_equity: number;
  drawdown_pct: number;
  daily_pnl_pct: number;
  updated_at: string;
}

export interface Position {
  symbol: string;
  quantity: number;
  avg_price: number;
  market_price: number;
  unrealized_pnl: number;
  realized_pnl: number;
  updated_at: string;
}

export interface Order {
  id: string;
  symbol: string;
  side: OrderSide;
  quantity: number;
  status: OrderStatus;
  avg_fill_price: number | null;
  submitted_at: string;
}

export interface Signal {
  id: string;
  strategy_id: string;
  symbol: string;
  side: SignalSide;
  strength: number;
  timestamp: string;
  reason: string;
}

export interface Fill {
  id: string;
  order_id: string;
  symbol: string;
  side: OrderSide;
  quantity: number;
  price: number;
  timestamp: string;
}

export interface EquityPoint {
  timestamp: string;
  equity: number;
  drawdown_pct: number;
}

export interface Bar {
  symbol: string;
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  timeframe: string;
}

export interface Quote {
  symbol: string;
  price: number;
  prev_close: number;
  change: number;
  change_pct: number;
  as_of: string;
  source: string;
}

export interface DashboardSnapshot {
  mode: string;
  persistence?: string;
  kill_switch: boolean;
  account: AccountSnapshot;
  positions: Position[];
  open_orders: Order[];
  recent_signals: Signal[];
  recent_fills: Fill[];
  equity_curve: EquityPoint[];
  quotes?: Quote[];
  data_source?: string;
}

export interface StrategyView {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  symbols: string[];
  timeframe: string;
  params: Record<string, unknown>;
}

export interface JournalEntry {
  id: string;
  event_type: string;
  timestamp: string;
  payload: Record<string, unknown>;
  correlation_id: string | null;
}

export interface MonteCarloStats {
  simulations: number;
  equity_p5: number;
  equity_p25?: number;
  equity_p50: number;
  equity_p75?: number;
  equity_p95: number;
  max_dd_p5?: number;
  max_dd_p50?: number;
  max_dd_p95?: number;
  ruin_probability_pct?: number;
}

export interface BacktestResult {
  strategy_id: string;
  starting_cash: number;
  ending_equity: number;
  total_return_pct: number;
  cagr_pct?: number;
  max_drawdown_pct: number;
  max_drawdown_duration_bars?: number;
  sharpe: number;
  sortino?: number;
  calmar?: number;
  trades: number;
  winning_trades?: number;
  losing_trades?: number;
  win_rate: number;
  profit_factor?: number;
  exposure_pct?: number;
  avg_win?: number;
  avg_loss?: number;
  expectancy?: number;
  monte_carlo?: MonteCarloStats;
  equity_curve: EquityPoint[];
  signals: number;
}

export interface WalkForwardFold {
  train_start: string;
  train_end: string;
  test_start: string;
  test_end: string;
  params: Record<string, unknown>;
  is_return_pct: number;
  is_sharpe: number;
  oos_return_pct: number;
  oos_sharpe: number;
  oos_max_drawdown_pct: number;
  oos_trades: number;
  oos_signals: number;
}

export interface WalkForwardResult {
  strategy_id: string;
  starting_cash: number;
  ending_equity: number;
  oos_return_pct: number;
  oos_max_drawdown_pct: number;
  oos_sharpe: number;
  folds: WalkForwardFold[];
  oos_equity_curve: EquityPoint[];
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface ScripInfo {
  symbol: string;
  name: string;
  exchange: string;
  sector: string;
  backend_symbol: string;
}

export interface BasketInfo {
  id: string;
  name: string;
  description: string;
  count: number;
  symbols: string[];
}

export interface ScreenerHit {
  symbol: string;
  name: string;
  exchange: string;
  strategy_id: string;
  strategy_name: string;
  side: SignalSide;
  strength: number;
  reason: string;
  ltp: number;
  change_pct: number;
  rsi?: number;
  atr?: number;
  dist_sma50_pct?: number;
  hist_win_rate_pct?: number;
  hist_sharpe?: number;
  hist_max_dd_pct?: number;
  timestamp: string;
}

export interface ScreenerRequest {
  strategy_ids?: string[];
  basket_id?: string;
  custom_symbols?: string[];
  timeframe?: string;
  min_strength?: number;
  side_filter?: string;
  limit?: number;
}

export interface ScreenerResponse {
  total_scanned: number;
  hits_count: number;
  hits: ScreenerHit[];
}

export interface StrategyAllocation {
  strategy_id: string;
  weight: number;
  params?: Record<string, unknown>;
}

export interface StrategyReturnProfile {
  strategy_id: string;
  name: string;
  weight: number;
  total_return_pct: number;
  sharpe: number;
  max_drawdown_pct: number;
  annualized_volatility: number;
  equity_curve: EquityPoint[];
}

export interface PortfolioBlendRequest {
  allocations: StrategyAllocation[];
  symbols: string[];
  start: string;
  end: string;
  starting_cash?: number;
  timeframe?: string;
  method?: "custom" | "equal_weight" | "risk_parity" | "max_sharpe";
}

export interface PortfolioBlendResponse {
  method: string;
  starting_cash: number;
  ending_equity: number;
  total_return_pct: number;
  cagr_pct: number;
  sharpe: number;
  sortino: number;
  max_drawdown_pct: number;
  annualized_volatility: number;
  diversification_ratio: number;
  drawdown_reduction_pct: number;
  blended_equity_curve: EquityPoint[];
  strategy_profiles: StrategyReturnProfile[];
  correlation_matrix: Record<string, Record<string, number>>;
}
