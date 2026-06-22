# agentrust-io demos

Runnable demos for [cMCP](https://github.com/agentrust-io/cmcp). Three demos, ~4 minutes total.

---

## Prerequisites

```bash
pip install cmcp-runtime cmcp-verify starlette uvicorn
```

All demos use `CMCP_DEV_MODE=1` (software-only TEE, no hardware required). The local MCP server performs real filesystem operations on `./workspace/`.

---

## Demo 1 — cMCP in action (~90 seconds)

Cedar policy is enforced by the cMCP runtime. Three tool calls route through the gateway. On real Intel TDX hardware, the policy bundle hash is committed into RTMR[2] at startup; in dev mode it appears only in the claim field.

```bash
bash demo-01-cmcp-in-action/run.sh
```

What you see:
- `file.write` — ALLOWED by Cedar policy, file appears in `workspace/hello.txt`
- `file.read` — ALLOWED, reads the file back
- `file.list` — DENIED (HTTP 403, Cedar forbid rule matches)
- Signed TRACE claim with `runtime.platform`, `runtime.measurement`, `policy.bundle_hash`

---

## Demo 2 — Policy swap = attestation failure (~60 seconds)

Two Cedar policy bundles are compared. v1 allows all tools; v2 denies `file.write`. Their hashes differ. A verifier that pinned the v1 hash detects `POLICY_HASH_MISMATCH` on any claim produced by a v2 gateway.

On real TDX hardware, swapping the policy at startup changes RTMR[2] — the TEE measurement itself mismatches, so the attestation quote is rejected before any claim is evaluated.

Requires demo-01 to have run first (uses `workspace/trace-claim.json`).

```bash
bash demo-02-policy-swap/run.sh
```

What you see:
- v1 and v2 bundle hashes printed side-by-side (visibly different)
- `cmcp verify` with v1 hash → passes
- `cmcp verify` with v2 hash → `POLICY_HASH_MISMATCH`

---

## Demo 3 — Offline TRACE verification (~60 seconds)

A signed TRACE claim is verified using only the claim file and the hashes embedded in it. No running gateway, no server connection, no operator trust required.

Requires demo-01 to have run first (uses `workspace/trace-claim.json`).

```bash
bash demo-03-offline-trace/run.sh
```

What you see:
- TRACE claim fields displayed (eat_profile, runtime, policy, audit_chain)
- Verification status with `cmcp_verify` — no network call made
- Explanation of why hardware_attestation is unverified in dev mode

---

## Structure

```
demos/
├── server/                        # Local MCP filesystem server (runs on :9001)
│   ├── server.py                  # Starlette HTTP: file.write, file.read, file.list
│   └── requirements.txt
├── demo-01-cmcp-in-action/
│   ├── cmcp-config.yaml
│   ├── catalog.json               # Approves file.write, file.read, file.list
│   ├── policies/                  # Cedar: permit file.write + file.read, forbid file.list
│   ├── call.py                    # MCP client calling through cMCP
│   └── run.sh
├── demo-02-policy-swap/
│   ├── cmcp-config.yaml           # Points to policies-v1/
│   ├── cmcp-config-v2.yaml        # Points to policies-v2/
│   ├── catalog.json
│   ├── policies-v1/               # Cedar: permit all
│   ├── policies-v2/               # Cedar: deny file.write
│   ├── check_hash.py              # Computes bundle hash matching cMCP's algorithm
│   └── run.sh
├── demo-03-offline-trace/
│   ├── verify.py                  # cmcp_verify offline claim verification
│   └── run.sh
└── workspace/                     # Files written by demos live here
```

---

## How it connects

```
LLM / client
     |
     v
[cMCP runtime]  ←  Cedar policy bundle (hash committed in RTMR[2] on TDX)
     |
     v
[Local MCP server]  →  workspace/ (real file writes)
     |
     v
TRACE claim (signed Ed25519)  →  offline verification with cmcp_verify
```
