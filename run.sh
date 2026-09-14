#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="python3"
NPM_BIN="npm"
VENV_DIR="$ROOT/.venv"
BACKEND_SRC="$ROOT/backend/src"
FRONTEND_DIR="$ROOT/frontend"
PID_FILE="/tmp/alphaforge.pids"

# ── colours ──────────────────────────────────────────────────────────
BOLD="\033[1m"
GREEN="\033[32m"
YELLOW="\033[33m"
CYAN="\033[36m"
RED="\033[31m"
RESET="\033[0m"

banner() {
  echo ""
  echo -e "${CYAN}===========================================================${RESET}"
  echo -e "${GREEN}${BOLD}           ALPHAFORGE  QUANT  TERMINAL${RESET}"
  echo -e "${CYAN}===========================================================${RESET}"
  echo ""
}

cleanup() {
  echo ""
  echo -e "${YELLOW}Shutting down AlphaForge...${RESET}"
  if [ -f "$PID_FILE" ]; then
    while read -r pid; do
      kill "$pid" 2>/dev/null || true
    done < "$PID_FILE"
    rm -f "$PID_FILE"
  fi
  echo -e "${GREEN}Done.${RESET}"
  exit 0
}
trap cleanup SIGINT SIGTERM

# ── 1. Python virtual environment ────────────────────────────────────
setup_python() {
  if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${RESET}"
    $PYTHON_BIN -m venv "$VENV_DIR"
  fi

  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"

  echo -e "${YELLOW}Installing Python dependencies (this may take a minute)...${RESET}"
  pip install -q --upgrade pip
  pip install -q \
    fastapi "uvicorn[standard]" sqlalchemy asyncpg alembic \
    "pydantic>=2" "pydantic-settings>=2" python-jose "pwdlib[argon2]" \
    python-multipart yfinance structlog "httpx>=0.27" \
    "websockets>=14" "apscheduler>=3.10" "cryptography>=43" \
    "prometheus-client>=0.21" "email-validator>=2" "numpy>=2" "pandas>=2"

  echo -e "${GREEN}Python environment ready.${RESET}"
}

# ── 2. Frontend dependencies ─────────────────────────────────────────
setup_frontend() {
  if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${RESET}"
    cd "$FRONTEND_DIR"
    $NPM_BIN install
    cd "$ROOT"
  fi
  echo -e "${GREEN}Frontend dependencies ready.${RESET}"
}

# ── 3. Start servers ─────────────────────────────────────────────────
start_servers() {
  echo ""
  echo -e "${BOLD}Launching servers...${RESET}"

  # Backend
  PYTHONPATH="$BACKEND_SRC" \
    "$VENV_DIR/bin/python" -m uvicorn alphaforge.main:app \
    --host 0.0.0.0 --port 8000 --reload \
    &>/tmp/alphaforge-backend.log &
  BACKEND_PID=$!
  echo -e "  ${GREEN}Backend  ${RESET} http://localhost:8000   (pid $BACKEND_PID)"

  # Frontend
  cd "$FRONTEND_DIR"
  $NPM_BIN run dev &>/tmp/alphaforge-frontend.log &
  FRONTEND_PID=$!
  cd "$ROOT"
  echo -e "  ${GREEN}Frontend ${RESET} http://localhost:3000   (pid $FRONTEND_PID)"

  echo "$BACKEND_PID" > "$PID_FILE"
  echo "$FRONTEND_PID" >> "$PID_FILE"

  echo ""
  echo -e "${CYAN}===========================================================${RESET}"
  echo -e "  ${BOLD}API Docs  ${RESET} http://localhost:8000/docs"
  echo -e "  ${BOLD}Dashboard ${RESET} http://localhost:3000"
  echo -e "${CYAN}===========================================================${RESET}"
  echo ""
  echo -e "${YELLOW}Press Ctrl+C to stop both servers.${RESET}"

  wait
}

# ── Main ──────────────────────────────────────────────────────────────
banner
setup_python
setup_frontend
start_servers
