"""
Compute the policy bundle hash for a given policies/ directory.

cMCP computes the bundle hash as:
  sha256(sorted JSON of all .cedar file contents + manifest.json)

This script computes and prints the hash for both policy sets,
so you can show the mismatch in the demo before starting cMCP.

Usage:
  python check_hash.py
"""

import hashlib
import json
import pathlib
import sys


def bundle_hash(policies_dir: pathlib.Path) -> str:
    manifest = json.loads((policies_dir / "manifest.json").read_text())
    # Build a deterministic representation: manifest + sorted policy content
    bundle = {
        "manifest": manifest,
        "policies": {
            name: (policies_dir / name).read_text()
            for name in sorted(manifest["policies"])
        },
        "schema": (policies_dir / manifest["schema"]).read_text(),
    }
    raw = json.dumps(bundle, sort_keys=True, ensure_ascii=True).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def main():
    base = pathlib.Path(__file__).parent
    for label, path in [("v1 (allow-all)", base / "policies-v1"),
                        ("v2 (deny-write)", base / "policies-v2")]:
        h = bundle_hash(path)
        print(f"{label}:\n  {h}\n")

    h1 = bundle_hash(base / "policies-v1")
    h2 = bundle_hash(base / "policies-v2")
    if h1 != h2:
        print("Hashes differ — policy swap is detectable by any verifier")
        print("that pinned the v1 hash in expected_policy_hash.")
    else:
        print("WARNING: hashes are identical (policy files have same content)")


if __name__ == "__main__":
    main()
