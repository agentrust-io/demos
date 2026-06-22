#!/usr/bin/env bash
# Demo 1: cMCP in action
# Cedar enforced in enclave; TRACE claim carries policy hash.
#
# On real Intel TDX hardware, policy.bundle_hash is incorporated into RTMR[2]
# at startup. With CMCP_DEV_MODE=1 the TEE is software-only (measurement = zeros)
# but the policy hash is still committed in the TRACE claim.
#
# Usage: bash run.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Starting MCP filesystem server on :9001 ==="
cd "$REPO_ROOT/server"
python server.py &
SERVER_PID=$!
sleep 1  # let server start

echo "=== Starting cMCP (CMCP_DEV_MODE=1) on :8443 ==="
cd "$SCRIPT_DIR"
CMCP_DEV_MODE=1 cmcp start --config cmcp-config.yaml &
CMCP_PID=$!
sleep 2  # let cMCP start and compute policy hash

echo "=== Making tool calls through cMCP ==="
python call.py

echo ""
echo "=== Workspace after call ==="
ls -la "$REPO_ROOT/workspace/"

# Cleanup
kill $CMCP_PID $SERVER_PID 2>/dev/null || true
wait $CMCP_PID $SERVER_PID 2>/dev/null || true
echo ""
echo "Done."
