"""
Compute the cMCP policy bundle hash for a given policies/ directory.

The bundle hash is defined in cmcp_runtime.policy.bundle._canonical_bundle_hash:

  sha256(canonical_json({
    "manifest": <full manifest.json contents>,
    "policy_files": {<filename>: sha256_hex(file_bytes)},  # sorted by filename
    "schema_hash": sha256_hex(schema.cedarschema bytes)
  }, sort_keys=True, separators=(",",":")))

Usage:
  # Print hashes for both policy sets
  python check_hash.py

  # Print hash for a single bundle directory (for scripting)
  python check_hash.py ./policies-v1
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bundle_hash(policies_dir: pathlib.Path) -> str:
    manifest = json.loads((policies_dir / "manifest.json").read_bytes())
    schema_bytes = (policies_dir / "schema.cedarschema").read_bytes()

    policy_hashes: dict[str, str] = {
        p.name: sha256_hex(p.read_bytes())
        for p in sorted(policies_dir.glob("*.cedar"))
    }

    canonical = json.dumps(
        {
            "manifest": manifest,
            "policy_files": policy_hashes,
            "schema_hash": sha256_hex(schema_bytes),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return "sha256:" + sha256_hex(canonical.encode())


def main() -> None:
    # Single-arg mode: print just the hash for one directory (used in run.sh)
    if len(sys.argv) == 2:
        print(bundle_hash(pathlib.Path(sys.argv[1])))
        return

    base = pathlib.Path(__file__).parent
    h1 = bundle_hash(base / "policies-v1")
    h2 = bundle_hash(base / "policies-v2")

    print(f"v1 (allow-all):\n  {h1}\n")
    print(f"v2 (deny file.write):\n  {h2}\n")

    if h1 != h2:
        print("Hashes differ — a verifier that pinned the v1 hash will")
        print("detect POLICY_HASH_MISMATCH on any claim from the v2 gateway.")
    else:
        print("WARNING: hashes are identical (policy content unchanged)")


if __name__ == "__main__":
    main()
