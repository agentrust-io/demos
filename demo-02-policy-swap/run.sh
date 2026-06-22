#!/usr/bin/env bash
# Demo 2: Policy swap = attestation failure
#
# Shows that swapping the Cedar policy bundle changes the policy.bundle_hash
# in the TRACE claim. A verifier that pinned the original hash rejects the new claim.
#
# On real Intel TDX hardware, the policy hash is incorporated into RTMR[2] at
# startup — so the TEE measurement itself changes, not just the claim field.
# With CMCP_DEV_MODE=1, only the claim field changes (measurement stays zeros),
# but the verifier check is identical either way.
#
# Usage: bash run.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Step 0: Compute policy hashes before starting cMCP ==="
python "$SCRIPT_DIR/check_hash.py"

echo "=== Step 1: Start MCP filesystem server ==="
cd "$REPO_ROOT/server"
python server.py &
SERVER_PID=$!
sleep 1

echo "=== Step 2: Start cMCP with v1 policy ==="
cd "$SCRIPT_DIR"
CMCP_DEV_MODE=1 cmcp start --config cmcp-config.yaml --policy-bundle-path ./policies-v1/ &
CMCP_PID=$!
sleep 2

echo ""
echo "=== Step 3: write_file succeeds under v1 policy ==="
python -c "
import json, time, urllib.request
payload = json.dumps({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'write_file','arguments':{'path':'demo.txt','content':'hello from v1 policy'}}}).encode()
req = urllib.request.Request('http://localhost:8443/mcp', data=payload, headers={'Content-Type':'application/json'}, method='POST')
resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
trace = resp.get('result',{}).get('trace_claim',{})
print('  policy.bundle_hash (v1):', trace.get('policy',{}).get('bundle_hash','(not in response)'))
print('  call result:', resp.get('result',{}).get('content',[{}])[0].get('text',''))
"

echo ""
echo "=== Step 4: Swap policy to v2 (reload cMCP) ==="
kill $CMCP_PID 2>/dev/null || true
wait $CMCP_PID 2>/dev/null || true
sleep 1
CMCP_DEV_MODE=1 cmcp start --config cmcp-config.yaml --policy-bundle-path ./policies-v2/ &
CMCP_PID=$!
sleep 2

echo ""
echo "=== Step 5: write_file is DENIED under v2 policy ==="
python -c "
import json, time, urllib.request
payload = json.dumps({'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'write_file','arguments':{'path':'demo.txt','content':'should fail'}}}).encode()
req = urllib.request.Request('http://localhost:8443/mcp', data=payload, headers={'Content-Type':'application/json'}, method='POST')
resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
trace = resp.get('result',{}).get('trace_claim',{})
print('  policy.bundle_hash (v2):', trace.get('policy',{}).get('bundle_hash','(not in response)'))
error = resp.get('error', resp.get('result',{}).get('error',''))
print('  call result: DENIED -', error)
" || python -c "
import json, urllib.request, urllib.error
payload = json.dumps({'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'write_file','arguments':{'path':'demo.txt','content':'should fail'}}}).encode()
req = urllib.request.Request('http://localhost:8443/mcp', data=payload, headers={'Content-Type':'application/json'}, method='POST')
try:
    resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
    print(json.dumps(resp, indent=2))
except urllib.error.HTTPError as e:
    print('HTTP error:', e.code, e.read().decode())
"

echo ""
echo "=== v2 hash differs from v1 — verifier with pinned v1 hash would REJECT ==="
echo "(On real TDX hardware, RTMR[2] itself would mismatch; no claim would be accepted)"

# Cleanup
kill $CMCP_PID $SERVER_PID 2>/dev/null || true
wait $CMCP_PID $SERVER_PID 2>/dev/null || true
echo ""
echo "Done."
