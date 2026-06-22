# Demo 3: Offline TRACE verification

**Duration:** ~60 seconds

A signed Trust Record is verified using only the record and the issuer's public key. No server, no cMCP runtime, no registry connection required. This is the portability property of TRACE: verification is fully self-contained.

## Setup

Run demo-01 first to produce a signed record, then copy the artifacts here:

```bash
cp ../demo-01-cmcp-in-action/trace_record.json ./trust_record.json
cp ../demo-01-cmcp-in-action/issuer_pub.pem    ./issuer_pub.pem
```

## Run

```bash
bash run.sh
```

## What to show the audience

1. The `verify.py` script loads the record and the public key — nothing else
2. All TRACE fields are printed: subject, model, runtime, policy, transparency
3. `Signature: VALID` — no network call was made
4. Point out: `runtime.measurement` and `policy.bundle_hash` are committed in the signature
   - Changing either field would break the signature
   - The verifier needs no connection to the operator who produced the record

## Key takeaway

The TRACE record is a portable proof. A regulator, auditor, or counterparty who holds the issuer's public key can verify any record independently — the operator who produced it does not need to be online or trusted.
