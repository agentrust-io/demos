#!/usr/bin/env bash
# Demo 5: attribute-based enforcement (compliance domain / BAA coverage)
#
# Starts the local MCP filesystem server and the cMCP Runtime (CMCP_DEV_MODE=1),
# then makes three calls through the Runtime:
#   write_file  clinical, baa_covered=true            -> Cedar permits
#   read_file   clinical, baa_covered=true            -> Cedar permits
#   list_dir    external-analytics, baa_covered=false -> Cedar DENIES (HTTP 403)
#
# The deny is decided on the tool's compliance attribute (context.baa_covered),
# not on its name. One guardrail rule covers every non-BAA-covered tool.
#
# Usage: bash demo-05-compliance-domain/run.sh   (from repo root)
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
echo "=== Demo 5: attribute-based enforcement (BAA coverage) ==="
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
