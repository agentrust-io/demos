#!/usr/bin/env bash
# Demo 2: Policy swap = attestation failure
#
# Shows that swapping the Cedar policy bundle changes policy.bundle_hash
# in the TRACE claim. A verifier that pinned the v1 hash will detect
# POLICY_HASH_MISMATCH on any claim produced after the policy was swapped.
#
# On real Intel TDX hardware, the policy hash flows into RTMR[2] at startup —
# the TEE measurement itself changes, not just the claim field.
# With CMCP_DEV_MODE=1, only the claim field changes (measurement stays zeros),
# but the verifier check is identical either way.
#
# Depends on demo-01 having been run first (workspace/trace-claim.json needed).
#
# Usage: bash demo-02-policy-swap/run.sh   (from repo root)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

CLAIM_PATH="$REPO_ROOT/workspace/trace-claim.json"
if [[ ! -f "$CLAIM_PATH" ]]; then
  echo "Run demo-01 first to produce a TRACE claim:"
  echo "  bash demo-01-cmcp-in-action/run.sh"
  exit 1
fi

echo ""
echo "=== Demo 2: Policy swap = attestation failure ==="
echo ""

echo "-- Step 1: Policy bundle hashes --"
python "$SCRIPT_DIR/check_hash.py"

# Extract hashes for use in verification (avoid fragile grep)
V1_HASH=$(python "$SCRIPT_DIR/check_hash.py" "$SCRIPT_DIR/policies-v1")
V2_HASH=$(python "$SCRIPT_DIR/check_hash.py" "$SCRIPT_DIR/policies-v2")

echo ""
echo "-- Step 2: v1 TRACE claim from demo-01 --"
python3 -c "
import json, pathlib
claim = json.loads(pathlib.Path('$CLAIM_PATH').read_text())
bundle_hash = claim['trace']['policy']['bundle_hash']
print(f'  claim.trace.policy.bundle_hash: {bundle_hash}')
print()
print('  This hash was committed at cMCP startup (in RTMR[2] on real TDX).')
print('  A verifier who approved the v1 bundle pins this value.')
"

echo ""
echo "-- Step 3: Verify v1 claim with v1 hash → passes --"
cmcp verify "$CLAIM_PATH" --policy-hash "$V1_HASH" || true

echo ""
echo "-- Step 4: Verify v1 claim with v2 hash → POLICY_HASH_MISMATCH --"
echo "  (Simulates a verifier that approved v1 being shown a claim from"
echo "   a gateway that loaded the swapped v2 bundle)"
cmcp verify "$CLAIM_PATH" --policy-hash "$V2_HASH" || true

echo ""
echo "  On real TDX hardware: swapping the policy bundle changes RTMR[2]."
echo "  No claim from the v2 gateway can pass v1 verification — the TEE"
echo "  measurement itself is different, not just a claim field."
echo ""
