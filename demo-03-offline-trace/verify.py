"""
Demo 3: Offline TRACE verification

Verifies a signed Trust Record using ONLY:
  - the record file (trust_record.json)
  - the issuer's public key (issuer_pub.pem)

No server connection. No cMCP runtime. No registry lookup.

The signed record is produced by demo-01 or demo-02 — copy it here:
  cp ../demo-01-cmcp-in-action/trace_record.json ./trust_record.json
  cp ../demo-01-cmcp-in-action/issuer_pub.pem ./issuer_pub.pem

Usage:
  pip install agentrust-trace
  python verify.py [record.json] [public_key.pem]
"""

import json
import pathlib
import sys

from agentrust_trace.sign import verify_record, load_key


def main():
    record_path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "trust_record.json")
    key_path = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "issuer_pub.pem")

    if not record_path.exists():
        print(f"Record not found: {record_path}")
        print("Run demo-01 first and copy the output:")
        print(f"  cp ../demo-01-cmcp-in-action/trace_record.json {record_path}")
        sys.exit(1)

    if not key_path.exists():
        print(f"Public key not found: {key_path}")
        print("Copy the issuer public key from demo-01:")
        print(f"  cp ../demo-01-cmcp-in-action/issuer_pub.pem {key_path}")
        sys.exit(1)

    print("=== Demo 3: Offline TRACE Verification ===\n")
    print(f"Record:     {record_path}")
    print(f"Public key: {key_path}")
    print()

    with open(key_path, "rb") as f:
        public_key = load_key(f.read())

    with open(record_path) as f:
        record = json.load(f)

    print("Fields in record:")
    print(f"  subject:            {record.get('subject')}")
    print(f"  issued_at (iat):    {record.get('iat')}")
    print(f"  model.provider:     {record.get('model', {}).get('provider')}")
    print(f"  model.model_id:     {record.get('model', {}).get('model_id')}")
    print(f"  runtime.platform:   {record.get('runtime', {}).get('platform')}")
    print(f"  runtime.measurement:{record.get('runtime', {}).get('measurement')}")
    print(f"  policy.bundle_hash: {record.get('policy', {}).get('bundle_hash')}")
    print(f"  data_class:         {record.get('data_class')}")
    print(f"  transparency:       {record.get('transparency')}")
    print()

    try:
        verify_record(record, public_key_or_jwk=public_key)
        print("Signature: VALID")
        print()
        print("This record was signed by the holder of the provided public key.")
        print("Verification required no server, no cMCP, no network.")
    except Exception as e:
        print(f"Signature: INVALID — {e}")
        sys.exit(1)

    tt = record.get("tool_transcript")
    if tt:
        print(f"\nTool transcript:")
        print(f"  hash:        {tt.get('hash')}")
        print(f"  call_count:  {tt.get('call_count')}")
        print(f"  transcript:  {tt.get('transcript_uri')}")
        print()
        print("To verify the transcript, fetch the URI and check the hash:")
        print("  see demo-03 README for the full audit chain walkthrough")


if __name__ == "__main__":
    main()
