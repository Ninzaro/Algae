# AlphaForge

Production-ready systematic algorithmic trading platform: research, walk-forward backtesting, paper trading, live multi-asset execution, portfolio construction, and institutional-grade risk controls.

**Current phase:** MVP — foundation + paper trading path.

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the source of truth.

## Principles

1. Paper-first → live only after proven metrics and risk gates.
2. Strategy logic is pure and side-effect free.
3. Risk is an independent gate that can veto any order.
4. Every decision is journaled (append-only).
5. Same code path for backtest / paper / live.

## Quick start

```bash
cp .env.example .env
# edit secrets in .env

# infrastructure
docker compose up postgres redis -d

# backend
uv sync --all-extras
uv run uvicorn alphaforge.main:app --app-dir backend/src --reload --port 8000

# frontend
cd frontend && pnpm install && pnpm dev
```

Dashboard: http://localhost:3000  
API docs: http://localhost:8000/docs

Default trading mode is **paper**. Live mode requires explicit `TRADING_MODE=live` plus broker credentials.

## Kill switch

- Dashboard button
- `POST /api/v1/risk/kill-switch`
- Flattens intent path: cancel open orders, block new ones

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 15, TypeScript, Tailwind, shadcn/ui |
| Backend | Python 3.12, FastAPI, Pydantic v2 |
| Data | PostgreSQL 16 + TimescaleDB, Redis |
| Brokers | Paper (local), Alpaca, CCXT |
