# ARCHITECTURE.md

> Keep this file in the repo root (or wherever your assistant can re-read it each session).
> This is the source of truth — the system prompt instructs the assistant to defer to whatever
> is written here over anything said earlier in conversation.

## 1. Overview

- **Project name:** AlphaForge
- **One-line purpose:** Production-ready systematic algorithmic trading platform covering research, walk-forward backtesting, paper trading, live multi-asset execution, portfolio construction, and institutional-grade risk controls.
- **Current phase:** MVP (foundation + paper trading path)

**Target users / scope:** Solo quant or small team. Equities, ETFs, and crypto (spot). Medium-to-low frequency systematic strategies (minutes to daily). Explicitly not HFT / microsecond latency.

**Core principles:**
1. Paper-first → Live only after proven metrics and risk gates.
2. Strategy logic is pure and side-effect free (no broker calls inside strategies).
3. Risk is an independent gate that can veto any order.
4. Every decision is journaled (append-only audit trail).
5. Same code path for backtest / paper / live as much as possible.

## 2. Tech stack

| Layer | Technology | Notes |
|---|---|---|
| Frontend | Next.js 15 (App Router) + TypeScript + Tailwind CSS + shadcn/ui + Recharts / lightweight-charts | Real-time dashboard: equity curve, positions, signals, kill-switch, backtest explorer |
| Backend | Python 3.12 + FastAPI + Uvicorn + Pydantic v2 | Async API, WebSockets for live updates, background workers |
| Research / Quant | pandas, Polars, NumPy, vectorbt, pandas-ta / TA-Lib, Optuna, scikit-learn, XGBoost, statsmodels | Fast vectorized research + parameter robustness. Optional later: NautilusTrader for event-driven high-fidelity |
| Database | PostgreSQL 16 + TimescaleDB | Time-series bars, trades, equity, signals, journals. Redis for cache, pub/sub, rate-limiting, short-lived state |
| Auth | JWT (access + refresh) + API-key scoped for internal services | Single-operator first; multi-user later. All broker credentials encrypted at rest |
| Broker / Data adapters | alpaca-py (primary equities + crypto paper/live), CCXT (crypto multi-exchange), yfinance / Polygon as fallback data | Abstracted behind a common `Broker` and `MarketData` interface |
| Execution & Risk | Custom services (Python) | Position sizing (volatility targeting / fractional Kelly), pre-trade checks, daily loss limits, max DD kill-switch, exposure limits |
| Scheduling / Jobs | APScheduler (MVP) → Celery + Redis or Prefect later | Data ingestion, rebalancing, signal generation, health checks |
| Observability | structlog (JSON) + Prometheus client + Grafana (optional) + Telegram / Discord webhooks | Alerts on risk breaches, disconnects, anomalous fills |
| Testing | pytest + pytest-asyncio + pytest-cov + hypothesis (property tests for risk) | |
| CI/CD | GitHub Actions | lint, type-check, unit + integration tests, Docker build |
| Hosting / Infra | Docker + Docker Compose (local & single-node), optional Railway / Render / Fly.io or AWS ECS | Secrets via environment / Docker secrets. Never commit .env |
| Package mgmt | uv (Python) + pnpm (frontend) | Fast, reproducible locks |

**Deliberately excluded for MVP (can be added later via Architecture Update):**
- Full Kafka / high-throughput streaming (Redis streams sufficient initially)
- Kubernetes
- C++/Rust hot-path (Python + Numba / vectorbt is enough for systematic)
- Multi-tenant SaaS features

## 3. Directory structure

```
/
├── ARCHITECTURE.md                 ← this file (source of truth)
├── README.md
├── .env.example
├── docker-compose.yml
├── pyproject.toml                  ← backend + quant dependencies (uv)
├── backend/
│   ├── src/
│   │   ├── alphaforge/             ← main Python package
│   │   │   ├── api/                ← FastAPI routers, dependencies, WebSockets
│   │   │   ├── core/               ← config, logging, security, exceptions
│   │   │   ├── models/             ← SQLAlchemy / Pydantic models
│   │   │   ├── services/
│   │   │   │   ├── data/           ← market data ingestion & storage
│   │   │   │   ├── strategy/       ← strategy registry, signal generation
│   │   │   │   ├── risk/           ← RiskManager (hard gates)
│   │   │   │   ├── execution/      ← order lifecycle, broker adapters
│   │   │   │   ├── portfolio/      → positions, PnL, allocation
│   │   │   │   ├── backtest/       ← vectorbt + custom engine wrappers
│   │   │   │   └── journal/        ← append-only decision & order log
│   │   │   ├── strategies/         ← concrete strategy implementations (pluggable)
│   │   │   └── adapters/           ← broker & data provider concrete classes
│   │   └── main.py
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── app/                    ← Next.js App Router pages
│   │   ├── components/             ← PascalCase React components
│   │   ├── hooks/
│   │   ├── lib/                    ← API client, utils
│   │   └── types/                  ← frontend-only types
│   └── package.json
├── common/                         ← shared contracts (OpenAPI-generated or hand-written)
│   └── schemas/                    ← JSON Schema / Pydantic shared where possible
├── notebooks/                      ← research only (not production path)
├── scripts/                        ← migrations, seed, one-off tools
├── data/                           ← local cache / parquet (gitignored)
└── .github/workflows/
```

(The assistant must treat the structure above as binding. New modules go into the appropriate `services/` or `strategies/` folder.)

## 4. Naming conventions

- **Python:** snake_case for functions, variables, modules, files. PascalCase for classes. Private with leading underscore.
- **TypeScript / React:** camelCase for functions/variables, PascalCase for components and types, kebab-case for file names only when required by Next.js conventions.
- **Database tables / columns:** snake_case.
- **Strategy identifiers:** kebab-case or snake_case unique IDs (e.g. `mean-reversion-v2`).
- **Branch names:** `feat/`, `fix/`, `chore/`, `arch/` prefixes.
- **Commit messages:** Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`).

## 5. Layer boundaries & data flow

**High-level flow (must remain true):**

```
Market Data → Strategy (pure signal) → Risk Gate → Execution → Broker
                     ↓                       ↓
                 Journal                 Portfolio / Positions
                     ↓
              Dashboard / Alerts
```

- Frontend talks to Backend exclusively via REST + WebSocket (no direct broker or DB access).
- Shared contracts live in `common/schemas` and are mirrored by Pydantic models (backend) and TypeScript types (frontend). Prefer generating OpenAPI → TS client when the API stabilizes.
- `/api` = thin controllers / route handlers only. Business logic belongs in `/services`.
- `/models` = persistence + domain objects. No business rules beyond validation.
- Strategies implement a strict interface (`generate_signals(context) → list[Signal]`). They never import brokers or risk.
- RiskManager is the only component allowed to approve or reject an `OrderIntent`. It is called synchronously before any broker call.
- All state mutations that affect capital (orders, fills, cancellations) go through the journal.

## 6. Coding standards

- **Python:** Ruff (lint + format) + mypy (strict) + basedpyright optional. Config in `pyproject.toml`.
- **TypeScript:** ESLint + Prettier + `strict: true` in tsconfig.
- **Docstrings:** Google style for public functions and classes. Inline comments only for non-obvious “why”.
- Every public function has full type hints. No `Any` without explicit justification and a `# type: ignore` comment with reason.
- Prefer composition and dependency injection. Services receive their collaborators via constructor or FastAPI Depends.
- Error handling: custom exception hierarchy under `core.exceptions`. Never swallow exceptions silently. Log + re-raise or convert to HTTPException at the API boundary.

## 7. Security & auth model

- **Auth mechanism:** JWT bearer tokens for the dashboard and internal API. Short-lived access tokens + refresh tokens. Service-to-service uses scoped API keys.
- **Secrets management:** All secrets (broker keys, DB URL, JWT secret, Telegram token) come from environment variables. `.env` is gitignored. Production uses Docker secrets or a secrets manager. Never log secret values.
- **Encryption at rest:** Broker API keys and any PII encrypted with Fernet (or equivalent) using a key derived from `MASTER_KEY` env var.
- **Risk of capital:** Hard kill-switch (dashboard + API endpoint + Telegram command) that immediately cancels open orders and can flatten positions. Daily loss limit and max drawdown limit are enforced in RiskManager and cannot be bypassed by strategies.
- **Input validation:** Pydantic models on every API boundary. SQL injection impossible (ORM only). Rate limiting on public-facing endpoints.
- **Compliance note (MVP):** System is for personal / proprietary use. No multi-client advisory features. Paper trading mode is the default until explicitly switched.

## 8. Testing conventions

- **Framework:** pytest + pytest-asyncio + pytest-cov. Hypothesis for property-based testing of risk and sizing logic.
- **Location:** `backend/tests/` mirrors the package structure (`tests/services/risk/test_risk_manager.py` etc.). Frontend uses Vitest + React Testing Library under `frontend/`.
- **Minimum expectations:**
  - RiskManager: 100% coverage of gate logic + property tests.
  - Execution adapters: unit tests with mocked broker + one integration test against paper accounts (CI can skip if no credentials).
  - Strategies: pure unit tests with synthetic data.
  - Critical path (signal → risk → order intent): integration tests.
- Before any feature is considered done: types pass (`mypy` / `tsc`), lint passes, tests exist and pass, no hardcoded secrets.

## 9. Known technical debt

| Item | Location | Why it exists | Priority |
|---|---|---|---|
| APScheduler instead of Celery/Prefect | services/ | Simpler for MVP single-node | Medium – replace when multi-process needed |
| vectorbt primary backtester | services/backtest | Extremely fast for research; lower fidelity on order-book realism | Medium – add NautilusTrader path later |
| Single-operator auth only | api/auth | Scope | Low |
| No formal FIX / institutional OMS | execution/ | Not needed for retail systematic | Low |

## 10. Changelog

| Date | Change | Reason |
|---|---|---|
| 2026-08-13 | Initial architecture created from template | Project kickoff – systematic algo trading system |
