#!/bin/zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${INNER_SPACE_META_ENV_FILE:-$HOME/.config/inner-space-meta.env}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

export PYTHONPATH="${PYTHONPATH:-$ROOT/src}"

exec "${PYTHON_BIN:-python3}" \
  "$ROOT/tools/run_telegram_meta_agent.py" \
  --poll-forever \
  --poll-interval-seconds "${INNER_SPACE_META_POLL_INTERVAL_SECONDS:-2.0}"
