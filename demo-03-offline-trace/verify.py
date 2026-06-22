"""
Demo 3: Offline TRACE claim verification

Verifies a signed cMCP TRACE claim using ONLY:
  - the claim file (workspace/trace-claim.json, produced by demo-01)
  - the policy hash and catalog hash embedded in the claim itself

No running gateway. No server connection. No operator trust required.

Usage:
  python demo-03-offline-trace/verify.py   (from repo root)
"""

from __future__ import annotations

import json
import pathlib
import sys

CLAIM_PATH = pathlib.Path(__file__).parent.parent / "workspace" / "trace-claim.json"


def main() -> None:
    if not CLAIM_PATH.exists():
        print(f"Claim not found at {CLAIM_PATH}")
        print("Run demo-01 first:  bash demo-01-cmcp-in-action/run.sh")
        sys.exit(1)

    claim = json.loads(CLAIM_PATH.read_text())

    trace = claim.get("trace", {})
    gateway = claim.get("gateway", {})
    policy_hash = trace.get("policy", {}).get("bundle_hash", "")
    catalog_hash = gateway.get("catalog", {}).get("hash", "")

    print("=== Demo 3: Offline TRACE verification ===")
    print()
    print(f"Claim:          {CLAIM_PATH}")
    print(f"Policy hash:    {policy_hash}")
    print(f"Catalog hash:   {catalog_hash}")
    print()
    print("Running offline verification with the hashes extracted from the claim...")
    print()

    from cmcp_verify import ApprovedHashes, verify_trace_claim

    approved = ApprovedHashes(
        policy_bundle_hash=policy_hash,
        tool_catalog_hash=catalog_hash,
    )

    result = verify_trace_claim(claim, approved)

    print(f"{'='*60}")
    print("VERIFICATION RESULT")
    print(f"{'='*60}")
    print(f"  Status:           {result.status.value}")
    print(f"  Verified fields:  {', '.join(result.verified_fields)}")
    print(f"  Unverified:       {', '.join(result.unverified_fields)}")
    print(f"  Failure reason:   {result.failure_reason}")
    print(f"  Attestation age:  {result.attestation_age_seconds}s")
    print(f"  Fresh:            {result.is_attestation_fresh}")
    if result.details:
        print("  Details:")
        for k, v in result.details.items():
            print(f"    {k}: {v}")
    print(f"{'='*60}")
    print()

    if result.status.value in ("verified", "partially_verified"):
        print("Cryptographic checks passed.")
        print()
        print("'hardware_attestation' is in unverified_fields because CMCP_DEV_MODE=1")
        print("uses a software-only TEE. On real Intel TDX or AMD SEV-SNP, it would")
        print("also be verified and status would be 'verified' with full hardware provenance.")
    else:
        print(f"Verification FAILED. Reason: {result.failure_reason}")

    print()
    print("No network call was made. No gateway was contacted.")
    print("Policy hash and measurement are committed in the Ed25519 signature.")


if __name__ == "__main__":
    main()
