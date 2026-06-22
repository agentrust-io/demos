#!/usr/bin/env bash
# Demo 1: cMCP in action
#
# Starts the local MCP filesystem server and the cMCP gateway (CMCP_DEV_MODE=1),
# then calls three tools through the gateway:
#   file.write  -> Cedar allows it, real file written to workspace/hello.txt
#   file.read   -> Cedar allows it, reads file back
#   file.list   -> Cedar DENIES it (HTTP 403)
#
# On real Intel TDX hardware, the policy bundle hash flows into RTMR[2]
# at startup. Here it appears in trace.policy.bundle_hash in the TRACE claim.
#
# Usage: bash demo-01-cmcp-in-action/run.sh   (from repo root)
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
echo "=== Demo 1: cMCP in action ==="
echo ""

echo "-- Starting MCP filesystem server on :9001 --"
python "$REPO_ROOT/server/server.py" &
SERVER_PID=$!
sleep 1

echo "-- Starting cMCP gateway (CMCP_DEV_MODE=1) on :8443 --"
cd "$SCRIPT_DIR"
CMCP_DEV_MODE=1 cmcp start --config cmcp-config.yaml &
CMCP_PID=$!
sleep 2

echo ""
python "$SCRIPT_DIR/call.py"
