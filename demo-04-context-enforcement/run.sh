#!/usr/bin/env bash
# Demo 4: context-aware enforcement
#
# Starts the local MCP filesystem server and the cMCP Runtime (CMCP_DEV_MODE=1),
# then makes three calls through the Runtime:
#   write_file  workflow=invoice-run    -> Cedar permits (approved workflow)
#   write_file  workflow=chat-freeform  -> Cedar DENIES  (same tool + args, HTTP 403)
#   read_file   workflow=chat-freeform  -> Cedar permits (reads allowed anywhere)
#
# The point: the same capability is scoped by the call's declared workflow, not
# by the tool's identity. The agent cannot widen its authority by restating intent.
#
# Usage: bash demo-04-context-enforcement/run.sh   (from repo root)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

CMCP_BEARER_TOKEN="${CMCP_BEARER_TOKEN:-demo-token}"
export CMCP_BEARER_TOKEN

cleanup() {
  kill "${CMCP_PID:-}" "${SERVER_PID:-}" 2>/dev/null || true
  wait "${CMCP_PID:-}" "${SERVER_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT

echo ""
echo "=== Demo 4: context-aware enforcement ==="
echo ""

echo "-- Starting MCP filesystem server on :9001 --"
python "$REPO_ROOT/server/server.py" &
SERVER_PID=$!
sleep 1

echo "-- Starting cMCP Runtime (CMCP_DEV_MODE=1) on :8443 --"
cd "$SCRIPT_DIR"
CMCP_DEV_MODE=1 cmcp start --config cmcp-config.yaml &
CMCP_PID=$!
sleep 2

echo ""
python "$SCRIPT_DIR/call.py"
