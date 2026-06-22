# agentrust-io demos

Runnable demos for [cMCP](https://github.com/agentrust-io/cmcp) and [TRACE](https://github.com/agentrust-io/trace-spec). Three demos, ~4 minutes total.

---

## Prerequisites

```bash
pip install cmcp-runtime agentrust-trace mcp uvicorn
```

All demos use `CMCP_DEV_MODE=1` (software-only TEE, no hardware required). The local MCP server performs real filesystem operations on `./workspace/`.

---

## Demo 1 — cMCP in action (~90 seconds)

Cedar policy is enforced by the cMCP runtime. Every tool call produces a TRACE claim carrying the policy bundle hash. On real Intel TDX hardware, this hash is incorporated into RTMR[2] at startup; here it appears in `policy.bundle_hash` in the claim.

```bash
cd demo-01-cmcp-in-action
bash run.sh
```

What you see:
- cMCP starts, computes the policy bundle hash
- `write_file` call is evaluated against the Cedar policy (allowed)
- TRACE claim shows `runtime.platform`, `runtime.measurement`, `policy.bundle_hash`
- The file appears in `./workspace/hello.txt`

---

## Demo 2 — Policy swap = attestation failure (~90 seconds)

The operator swaps the Cedar policy bundle (v1 → v2). The TRACE claim's `policy.bundle_hash` changes. A verifier that pinned the v1 hash rejects all claims from the reloaded runtime.

On real TDX hardware, swapping the policy at startup changes RTMR[2] — the measurement itself mismatches, so the TEE attestation quote is rejected before any claim is evaluated.

```bash
cd demo-02-policy-swap
bash run.sh
```

What you see:
- v1 and v2 policy hashes printed side-by-side (visibly different)
- `write_file` succeeds under v1, is DENIED under v2 (different Cedar rule)
- TRACE claims from each run carry different `policy.bundle_hash` values

---

## Demo 3 — Offline TRACE verification (~60 seconds)

A signed Trust Record is verified using only the record file and the issuer's public key. No server, no cMCP runtime, no network connection required.

```bash
# First run demo-01 and copy its output here:
cp demo-01-cmcp-in-action/trace_record.json demo-03-offline-trace/trust_record.json
cp demo-01-cmcp-in-action/issuer_pub.pem    demo-03-offline-trace/issuer_pub.pem

cd demo-03-offline-trace
bash run.sh
```

What you see:
- All TRACE fields printed (subject, model, runtime, policy, transparency)
- `Signature: VALID` with no server call
- Tool transcript hash and call count from the record

---

## Structure

```
demos/
├── server/                     # Local MCP filesystem server (runs on :9001)
│   ├── server.py               # FastMCP server: write_file, read_file, list_dir
│   └── requirements.txt
├── demo-01-cmcp-in-action/
│   ├── cmcp-config.yaml
│   ├── catalog.json            # Approves write_file and read_file
│   ├── policies/               # Cedar: permit write_file and read_file
│   ├── call.py                 # MCP client that calls through cMCP
│   └── run.sh
├── demo-02-policy-swap/
│   ├── policies-v1/            # Cedar: permit all
│   ├── policies-v2/            # Cedar: permit read_file only, forbid write_file
│   ├── check_hash.py           # Prints bundle hashes for both policy sets
│   └── run.sh
├── demo-03-offline-trace/
│   ├── verify.py               # agentrust-trace verify_record (no network)
│   └── run.sh
└── workspace/                  # Files written by demos live here
```

---

## How it connects

```
LLM / client
     |
     v
[cMCP runtime]  ←  Cedar policy bundle (hash → RTMR[2] on TDX)
     |
     v
[Local MCP server]  →  workspace/ (real file writes)
     |
     v
TRACE claim (signed)  →  offline verification with public key only
```
