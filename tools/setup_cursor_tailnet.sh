#!/usr/bin/env bash
# Join a Cursor Cloud (or other remote) agent host to the private tailnet and
# point workspace tooling at the canonical SQLite service.
set -euo pipefail

WORKSPACE_API_BASE="${INNER_WORLD_WORKSPACE_API_BASE:-https://talhas-laboratory.tailefe062.ts.net/workspace}"
TAILSCALE_AUTHKEY="${TAILSCALE_AUTHKEY:-${TS_AUTHKEY:-}}"
CONFIG_PATH="${INNER_SPACE_WORKSPACE_ENV:-${HOME}/.config/inner-space-workspace.env}"
TAILSCALE_STATE_DIR="${TAILSCALE_STATE_DIR:-${HOME}/.cache/inner-space-tailscale}"
TAILSCALE_SOCKET="${TAILSCALE_SOCKET:-${TAILSCALE_STATE_DIR}/tailscaled.sock}"

if [[ -z "${TAILSCALE_AUTHKEY}" ]]; then
  echo "error: set TAILSCALE_AUTHKEY (or TS_AUTHKEY) to a tagged ephemeral Tailscale auth key" >&2
  exit 1
fi

if ! command -v tailscale >/dev/null 2>&1; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi

HOSTNAME="cursor-${CURSOR_AGENT_ID:-agent}"
UP_ARGS=(
  --auth-key="${TAILSCALE_AUTHKEY}"
  --hostname="${HOSTNAME}"
  --advertise-tags=tag:cursor-agent
  --accept-dns=false
)

tailscale_cmd() {
  if [[ -n "${TS_SOCKET:-}" && -S "${TS_SOCKET}" ]]; then
    tailscale --socket="${TS_SOCKET}" "$@"
  else
    tailscale "$@"
  fi
}

start_userspace_tailscaled() {
  mkdir -p "${TAILSCALE_STATE_DIR}"
  if [[ -S "${TAILSCALE_SOCKET}" ]]; then
    export TS_SOCKET="${TAILSCALE_SOCKET}"
    return
  fi
  echo "starting tailscaled in userspace mode"
  tailscaled \
    --tun=userspace-networking \
    --state="${TAILSCALE_STATE_DIR}/tailscaled.state" \
    --socket="${TAILSCALE_SOCKET}" &
  TAILSCALED_PID=$!
  trap 'kill "${TAILSCALED_PID}" 2>/dev/null || true' EXIT
  for _ in $(seq 1 30); do
    if [[ -S "${TAILSCALE_SOCKET}" ]]; then
      export TS_SOCKET="${TAILSCALE_SOCKET}"
      return
    fi
    sleep 1
  done
  echo "error: tailscaled did not become ready" >&2
  exit 1
}

join_tailnet() {
  if sudo -n true 2>/dev/null; then
    sudo tailscale up "${UP_ARGS[@]}"
    return
  fi
  if tailscale_cmd status >/dev/null 2>&1; then
    tailscale_cmd up "${UP_ARGS[@]}"
    return
  fi
  start_userspace_tailscaled
  tailscale_cmd up "${UP_ARGS[@]}"
}

write_workspace_config() {
  mkdir -p "$(dirname "${CONFIG_PATH}")"
  umask 077
  printf 'INNER_WORLD_WORKSPACE_API_BASE=%s\n' "${WORKSPACE_API_BASE}" > "${CONFIG_PATH}"
  export INNER_WORLD_WORKSPACE_API_BASE="${WORKSPACE_API_BASE}"
}

verify_workspace_api() {
  local health_url="${WORKSPACE_API_BASE%/}/health"
  echo "verifying canonical workspace API at ${health_url}"
  curl --fail --silent --show-error --max-time 20 "${health_url}"
  echo ""
  local catalog_url="${WORKSPACE_API_BASE%/}/api/workspaces"
  curl --fail --silent --show-error --max-time 20 "${catalog_url}" >/dev/null
  echo "workspace catalog reachable"
}

join_tailnet
write_workspace_config
verify_workspace_api

echo "configured ${CONFIG_PATH}"
echo "export INNER_WORLD_WORKSPACE_API_BASE=${WORKSPACE_API_BASE}"
