#!/usr/bin/env bash
# =============================================================================
# dev.sh — Smart Supply AI · Unified dev launcher
# Place this file at the project root.
#
# Usage:
#   ./dev.sh up              → build & start backend + frontend
#   ./dev.sh up backend      → backend only
#   ./dev.sh up frontend     → frontend only
#   ./dev.sh down            → stop backend + frontend
#   ./dev.sh down backend    → stop backend only
#   ./dev.sh down frontend   → stop frontend only
#   ./dev.sh reset-db        → wipe DB volumes & restart everything
#   ./dev.sh logs            → tail logs for all backend services
#   ./dev.sh status          → show running containers for both stacks
# =============================================================================

set -e

# ── Colours ──
GREEN="\033[0;32m"
CYAN="\033[0;36m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
BOLD="\033[1m"
RESET="\033[0m"

log()     { echo -e "${CYAN}[smart-supply]${RESET} $1"; }
ok()      { echo -e "${GREEN}✔ $1${RESET}"; }
warn()    { echo -e "${YELLOW}⚠ $1${RESET}"; }
err()     { echo -e "${RED}✘ $1${RESET}"; exit 1; }
section() { echo -e "\n${BOLD}── $1${RESET}"; }

# ── Resolve root directory ──
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Compose shorthand helpers ──
BACKEND_COMPOSE="docker compose --env-file $ROOT/.env -f $ROOT/infra/docker-compose.yml"
FRONTEND_COMPOSE="docker compose -f $ROOT/frontend/docker-compose.yml"

# ── Guards ──
command -v docker >/dev/null 2>&1 || err "Docker is not installed. Get it at https://docs.docker.com/get-docker/"

[ -f "$ROOT/.env" ]                         || err ".env file not found at project root"
[ -f "$ROOT/infra/docker-compose.yml" ]     || err "infra/docker-compose.yml not found"
[ -f "$ROOT/frontend/docker-compose.yml" ]  || err "frontend/docker-compose.yml not found"

# =============================================================================
# COMMANDS
# =============================================================================

cmd_up() {
  local target=${1:-all}

  if [[ "$target" == "backend" || "$target" == "all" ]]; then
    section "Starting backend services"
    $BACKEND_COMPOSE up -d --build
    ok "Backend is up"
  fi

  if [[ "$target" == "frontend" || "$target" == "all" ]]; then
    section "Starting frontend"
    # Ensure the shared network exists before attaching the frontend to it
    if [[ "$target" == "frontend" ]]; then
      docker network inspect smart-supply-net >/dev/null 2>&1 \
        || err "Backend network 'smart-supply-net' not found. Run './dev.sh up backend' first."
    fi
    $FRONTEND_COMPOSE up -d --build
    ok "Frontend is up → http://localhost:3000"
  fi

  echo ""
  cmd_status
}

cmd_down() {
  local target=${1:-all}

  if [[ "$target" == "frontend" || "$target" == "all" ]]; then
    section "Stopping frontend"
    $FRONTEND_COMPOSE down
    ok "Frontend stopped"
  fi

  if [[ "$target" == "backend" || "$target" == "all" ]]; then
    section "Stopping backend"
    $BACKEND_COMPOSE down
    ok "Backend stopped"
  fi
}

cmd_reset_db() {
  section "Resetting database"
  warn "This will DELETE all database volumes. Data will be lost."
  read -p "  Are you sure? (y/N): " confirm
  [[ "$confirm" =~ ^[Yy]$ ]] || { log "Aborted."; exit 0; }

  log "Tearing down backend (with volumes)..."
  $BACKEND_COMPOSE down -v

  log "Rebuilding backend..."
  $BACKEND_COMPOSE up -d --build

  ok "Database reset complete"
  echo ""
  cmd_status
  cmd_logs
}

cmd_logs() {
  section "Tailing backend logs (Ctrl+C to exit)"
  $BACKEND_COMPOSE logs -f db data-service ml-service alert-service
}

cmd_status() {
  section "Backend containers"
  $BACKEND_COMPOSE ps

  section "Frontend containers"
  $FRONTEND_COMPOSE ps
}

# =============================================================================
# ENTRYPOINT — parse command & optional target
# =============================================================================

COMMAND=${1:-}
TARGET=${2:-all}

case "$COMMAND" in
  up)        cmd_up "$TARGET" ;;
  down)      cmd_down "$TARGET" ;;
  reset-db)  cmd_reset_db ;;
  logs)      cmd_logs ;;
  status)    cmd_status ;;
  *)
    echo -e "\n${BOLD}Smart Supply AI — dev.sh${RESET}"
    echo ""
    echo "  Usage: ./dev.sh <command> [target]"
    echo ""
    echo "  Commands:"
    echo "    up [backend|frontend]    Build & start services (default: all)"
    echo "    down [backend|frontend]  Stop services (default: all)"
    echo "    reset-db                 Wipe DB volumes & restart backend"
    echo "    logs                     Tail backend service logs"
    echo "    status                   Show running containers"
    echo ""
    exit 1
    ;;
esac