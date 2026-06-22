#!/usr/bin/env bash
# Demo 3: Offline TRACE verification
#
# Verifies a signed Trust Record with no server connection.
# Only the record and the issuer's public key are needed.
#
# Prerequisites:
#   1. Run demo-01 first to produce a signed record.
#   2. Copy the record and public key here:
#        cp ../demo-01-cmcp-in-action/trace_record.json ./trust_record.json
#        cp ../demo-01-cmcp-in-action/issuer_pub.pem    ./issuer_pub.pem
#
# Usage: bash run.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -f "$SCRIPT_DIR/trust_record.json" ]]; then
  echo "No trust_record.json found. Run demo-01 first:"
  echo "  bash ../demo-01-cmcp-in-action/run.sh"
  echo "Then copy the output:"
  echo "  cp ../demo-01-cmcp-in-action/trace_record.json trust_record.json"
  echo "  cp ../demo-01-cmcp-in-action/issuer_pub.pem    issuer_pub.pem"
  exit 1
fi

echo "=== Verifying offline (no server, no cMCP, no registry) ==="
python "$SCRIPT_DIR/verify.py" "$SCRIPT_DIR/trust_record.json" "$SCRIPT_DIR/issuer_pub.pem"
