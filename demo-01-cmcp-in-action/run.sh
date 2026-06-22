#!/usr/bin/env bash
# Demo 1: cMCP in action
#
# Three tool calls route through the cMCP gateway:
#   file.write → ALLOWED by Cedar policy
#   file.read  → ALLOWED by Cedar policy
#   file.list  → DENIED  by Cedar policy (HTTP 403)
#
# The session is then closed and a signed TRACE claim is retrieved.
# The claim carries the policy bundle hash committed at startup (in RTMR[2]
# on real Intel TDX hardware; zeroes in CMCP_DEV_MODE=1).
#
# The claim is saved to workspace/trace-claim.json for use by demo-02 and demo-03.
#
# Usage: bash demo-01-cmcp-in-action/run.sh   (from repo root)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cleanup() {
  kill "${CMCP_PID:-}" "${SERVER_PID:-}" 2>/dev/null || true
  wait "${CMCP_PID:-}" "${SERVER_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT

echo ""
echo "=== Demo 1: cMCP in action ==="
echo ""

echo "-- Starting demo filesystem server on :9001 --"
python "$REPO_ROOT/server/server.py" &
SERVER_PID=$!
sleep 1

echo "-- Starting cMCP gateway (CMCP_DEV_MODE=1) on :8443 --"
cd "$SCRIPT_DIR"
CMCP_DEV_MODE=1 cmcp start --config cmcp-config.yaml &
CMCP_PID=$!
sleep 2

echo ""
echo "-- Making tool calls through cMCP --"
python "$SCRIPT_DIR/call.py"

echo ""
echo "-- Workspace after demo --"
ls -la "$REPO_ROOT/workspace/" 2>/dev/null || echo "(workspace not yet created)"
echo ""
