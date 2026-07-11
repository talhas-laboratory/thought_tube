#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PORT="${INNER_WORLD_PORT:-8422}"

export INNER_WORLD_BRIDGE_ENABLED="${INNER_WORLD_BRIDGE_ENABLED:-false}"
unset INNER_WORLD_MOBILE_PASSWORD

echo "Starting Inner World API on http://127.0.0.1:${PORT}"
echo "  bridge agent: ${INNER_WORLD_BRIDGE_ENABLED} (set INNER_WORLD_BRIDGE_ENABLED=true + OpenClaw for full agent)"
echo "  mobile auth: off (no INNER_WORLD_MOBILE_PASSWORD)"
python3 "$ROOT/tools/run_inner_world_miniapp.py" --port "$PORT" &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

sleep 1

echo "Starting Thought Capture PWA on http://localhost:5173/capture"
cd "$ROOT/product/thought_capture_pwa"
npm run dev
