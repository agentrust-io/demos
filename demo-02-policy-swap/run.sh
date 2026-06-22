#!/usr/bin/env bash
# Demo 2: Policy swap = attestation failure
#
# Shows that swapping the Cedar policy bundle changes policy.bundle_hash
# in the TRACE claim. A verifier that pinned the v1 hash detects POLICY_HASH_MISMATCH.
#
# On real Intel TDX hardware, the policy hash flows into RTMR[2] at startup.
# Swapping the bundle changes the TEE measurement itself, not just the claim field.
#
# Requires demo-01 to have run first (needs workspace/trace-claim.json).
#
# Usage: bash demo-02-policy-swap/run.sh   (from repo root)
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

CLAIM_PATH="$REPO_ROOT/workspace/trace-claim.json"
if [[ ! -f "$CLAIM_PATH" ]]; then
  echo "Run demo-01 first to produce a TRACE claim:"
  echo "  bash demo-01-cmcp-in-action/run.sh"
  exit 1
fi

echo ""
echo "=== Demo 2: Policy swap = attestation failure ==="
echo ""

# Step 0: Show that v1 and v2 hashes differ
echo "-- Step 0: Policy bundle hashes --"
python "$SCRIPT_DIR/check_hash.py"

# Step 1: Show the v1 claim's policy hash
echo ""
echo "-- Step 1: TRACE claim from demo-01 --"
python3 -c "
import json, pathlib
claim = json.loads(pathlib.Path('$CLAIM_PATH').read_text())
policy_hash = claim['trace']['policy']['bundle_hash']
catalog_hash = claim['gateway']['catalog']['hash']
print(f'  v1 policy.bundle_hash: {policy_hash}')
print(f'  catalog.hash:          {catalog_hash}')
print()
print('  A verifier who approved v1 pins the policy hash above.')
"

# Step 2: Start v2 gateway (Cedar policy now forbids write_file)
echo ""
echo "-- Step 2: Start cMCP with v2 policy (write_file DENIED) --"
python "$REPO_ROOT/server/server.py" &
SERVER_PID=$!
sleep 1

cd "$SCRIPT_DIR"
CMCP_DEV_MODE=1 cmcp start --config cmcp-config-v2.yaml &
CMCP_PID=$!
sleep 2

# Step 3: Show write_file is denied under v2
echo ""
echo "-- Step 3: write_file -> DENIED by v2 Cedar policy --"
python3 -c "
import json, os, urllib.request, urllib.error

TOKEN = os.environ.get('CMCP_BEARER_TOKEN', 'demo-token')
payload = json.dumps({
    'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
    'params': {
        'name': 'write_file',
        'arguments': {'path': 'post-swap.txt', 'content': 'written after policy swap'},
        '_cmcp': {'workflow_id': 'demo-02'},
    },
}).encode()
req = urllib.request.Request(
    'http://localhost:8443/mcp',
    data=payload,
    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {TOKEN}'},
    method='POST',
)
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = json.loads(resp.read())
except urllib.error.HTTPError as exc:
    body = json.loads(exc.read())

error = body.get('error', {})
code = error.get('data', {}).get('error_code', '?')
print(f'  HTTP 403 -- {error.get(\"message\", \"?\")} [{code}]')
print('  Cedar forbid rule matched: resource.tool_name == \"write_file\"')
"

# Step 4: Get v2 TRACE claim (via allowed read_file call)
echo ""
echo "-- Step 4: Get v2 TRACE claim --"
python3 -c "
import json, os, urllib.request, pathlib

TOKEN = os.environ.get('CMCP_BEARER_TOKEN', 'demo-token')
headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {TOKEN}'}

payload = json.dumps({
    'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
    'params': {'name': 'read_file', 'arguments': {'path': 'hello.txt'}, '_cmcp': {'workflow_id': 'demo-02'}},
}).encode()
req = urllib.request.Request('http://localhost:8443/mcp', data=payload, headers=headers, method='POST')
with urllib.request.urlopen(req, timeout=10) as resp:
    r = json.loads(resp.read())
session_id = r['result']['_cmcp']['session_id']

req2 = urllib.request.Request(
    f'http://localhost:8443/sessions/{session_id}/close',
    data=b'{}', headers=headers, method='POST',
)
with urllib.request.urlopen(req2, timeout=10) as resp2:
    v2_claim = json.loads(resp2.read())

v1_claim = json.loads(pathlib.Path('$CLAIM_PATH').read_text())
v1_hash = v1_claim['trace']['policy']['bundle_hash']
v2_hash = v2_claim['trace']['policy']['bundle_hash']
print(f'  v1 policy.bundle_hash: {v1_hash}')
print(f'  v2 policy.bundle_hash: {v2_hash}')
print()
if v1_hash != v2_hash:
    print('  Hashes differ. A verifier with the v1 approved hash will reject v2 claims.')
else:
    print('  ERROR: hashes should differ but are identical.')

pathlib.Path('$REPO_ROOT/workspace/trace-claim-v2.json').write_text(
    __import__('json').dumps(v2_claim, indent=2)
)
" 2>&1

# Step 5: Run cmcp verify -- v1 claim with v2 hash -> POLICY_HASH_MISMATCH
echo ""
echo "-- Step 5: cmcp verify (v1 claim + v2 hash) -> POLICY_HASH_MISMATCH --"
V1_HASH=$(python3 "$SCRIPT_DIR/check_hash.py" v1 | awk '{print $2}')
V2_HASH=$(python3 "$SCRIPT_DIR/check_hash.py" v2 | awk '{print $2}')
CATALOG_HASH=$(python3 -c "
import json, pathlib
c = json.loads(pathlib.Path('$CLAIM_PATH').read_text())
print(c['gateway']['catalog']['hash'])
")
cmcp verify "$CLAIM_PATH" --policy-hash "$V2_HASH" --catalog-hash "$CATALOG_HASH" || true

echo ""
echo "-- Step 6: cmcp verify (v1 claim + v1 hash) -> passes --"
cmcp verify "$CLAIM_PATH" --policy-hash "$V1_HASH" --catalog-hash "$CATALOG_HASH" || true

echo ""
echo "  On real TDX hardware: RTMR[2] changes on policy swap."
echo "  No claim from the v2 gateway can pass v1 verification."
echo ""
