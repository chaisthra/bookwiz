#!/usr/bin/env bash
# BookWiz — start frontend + backend with one command
# Usage: ./start.sh

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

echo -e "\n${BOLD}📚 BookWiz — starting up...${RESET}\n"

# Add Node to PATH if needed
export PATH="$PATH:/c/Program Files/nodejs"

# ── Preflight checks ──────────────────────────────────────────────────────────

if [ ! -f "$BACKEND/.env" ]; then
  echo -e "${RED}✗ backend/.env not found. Copy .env.example and fill in your keys.${RESET}"
  exit 1
fi

if [ ! -f "$BACKEND/venv/Scripts/uvicorn" ]; then
  echo -e "${RED}✗ Python venv not found. Run: cd backend && python -m venv venv && pip install -r requirements.txt${RESET}"
  exit 1
fi

if [ ! -d "$FRONTEND/node_modules" ]; then
  echo -e "${YELLOW}⚠ node_modules missing — running npm install...${RESET}"
  cd "$FRONTEND" && npm install
fi

# ── Start backend ─────────────────────────────────────────────────────────────

echo -e "${CYAN}[backend]${RESET} Starting FastAPI on http://localhost:8001"
cd "$BACKEND"
./venv/Scripts/uvicorn main:app --reload --port 8001 2>&1 \
  | sed "s/^/$(echo -e "${CYAN}[backend]${RESET}") /" &
BACKEND_PID=$!

# Wait for backend to be ready
echo -e "${CYAN}[backend]${RESET} Waiting for server..."
for i in $(seq 1 15); do
  if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo -e "${GREEN}[backend]${RESET} ✓ Ready at http://localhost:8001"
    break
  fi
  sleep 1
done

# ── Start frontend ────────────────────────────────────────────────────────────

echo -e "${YELLOW}[frontend]${RESET} Starting Next.js on http://localhost:3000"
cd "$FRONTEND"
npm run dev 2>&1 \
  | sed "s/^/$(echo -e "${YELLOW}[frontend]${RESET}") /" &
FRONTEND_PID=$!

# ── Trap Ctrl+C to kill both ──────────────────────────────────────────────────

cleanup() {
  echo -e "\n${BOLD}Shutting down...${RESET}"
  kill $BACKEND_PID 2>/dev/null
  kill $FRONTEND_PID 2>/dev/null
  # Kill any child processes too
  pkill -P $BACKEND_PID 2>/dev/null
  pkill -P $FRONTEND_PID 2>/dev/null
  echo -e "${GREEN}Done.${RESET}"
  exit 0
}
trap cleanup SIGINT SIGTERM

echo -e "\n${BOLD}${GREEN}✓ BookWiz running${RESET}"
echo -e "  Frontend → ${YELLOW}http://localhost:3000${RESET}"
echo -e "  Backend  → ${CYAN}http://localhost:8001${RESET}"
echo -e "  API docs → ${CYAN}http://localhost:8001/docs${RESET}"
echo -e "\n  Press ${BOLD}Ctrl+C${RESET} to stop both\n"

# Keep script alive
wait
