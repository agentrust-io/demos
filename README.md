# agentrust-io demos

Runnable demos for [cMCP](https://github.com/agentrust-io/cmcp) and [TRACE](https://github.com/agentrust-io/trace-spec). Three demos, ~4 minutes total.

---

## Prerequisites

```bash
pip install cmcp-runtime
```

`cmcp-runtime` includes all dependencies (`starlette`, `uvicorn`, `cmcp-verify`). All demos use `CMCP_DEV_MODE=1` (software-only TEE, no hardware required). The local MCP server performs real filesystem operations on `./workspace/`.

Set a bearer token (the gateway requires one):

```bash
# bash / Git Bash
export CMCP_BEARER_TOKEN=demo-token
```

```powershell
# PowerShell
$env:CMCP_BEARER_TOKEN = "demo-token"
```

---

## Demo 1 -- cMCP in action (~90 seconds)

The agent calls three tools through the cMCP gateway. Cedar policy is enforced for every call. At session close, the gateway produces a signed TRACE claim carrying the policy bundle hash.

On real Intel TDX hardware, the policy bundle hash flows into RTMR[2] at startup. Here it appears in `trace.policy.bundle_hash` in the claim.

```bash
bash demo-01-cmcp-in-action/run.sh
```

What you see:
- cMCP starts, measures the policy bundle hash
- `write_file`: Cedar allows it, real file written to `workspace/hello.txt`
- `read_file`: Cedar allows it, reads the file back
- `list_dir`: **denied by Cedar policy** (HTTP 403, error_code: POLICY_DENY)
- TRACE claim shows `runtime.platform`, `runtime.measurement`, `policy.bundle_hash`
- Claim saved to `workspace/trace-claim.json` (needed by demos 2 and 3)

---

## Demo 2 -- Policy swap = attestation failure (~90 seconds)

The operator loads a different Cedar policy bundle (v1 vs v2). The claim's `policy.bundle_hash` changes. A verifier that pinned the v1 hash rejects v2 claims with `POLICY_HASH_MISMATCH`.

On real TDX hardware, the policy hash flows into RTMR[2] at startup -- the TEE measurement itself changes, not just a field in the claim.

**Requires demo 1 to have run first** (reads `workspace/trace-claim.json`).

```bash
bash demo-02-policy-swap/run.sh
```

What you see:
- v1 and v2 bundle hashes printed (visibly different SHA-256 values)
- `write_file` is DENIED under v2 policy (new Cedar forbid rule)
- `cmcp verify` on the v1 claim with v2 hash -> POLICY_HASH_MISMATCH
- `cmcp verify` on the v1 claim with v1 hash -> passes

---

## Demo 3 -- Offline TRACE verification (~60 seconds)

The signed TRACE claim from demo-01 is verified with no gateway, no server, and no network call. Only `cmcp_verify` and the hashes embedded in the claim are used.

**Requires demo 1 to have run first**.

```bash
bash demo-03-offline-trace/run.sh
```

What you see:
- Claim fields printed: `runtime.platform`, `runtime.measurement`, `policy.bundle_hash`
- All cryptographic checks pass (schema, signature, policy hash, catalog hash, audit chain)
- `hardware_attestation` is in `unverified_fields` (software-only mode -- on real TDX it would also be verified)
- No connection made to any server

---

## Structure

```
demos/
+-- README.md
+-- requirements.txt
+-- server/
|   +-- server.py               # Plain HTTP JSON-RPC 2.0 server: write_file, read_file, list_dir
|   +-- requirements.txt
+-- workspace/                  # Files written by demos (created at runtime)
+-- demo-01-cmcp-in-action/
|   +-- cmcp-config.yaml
|   +-- catalog.json            # Approves write_file, read_file, list_dir
|   +-- policies/               # Cedar: permit write_file+read_file, forbid list_dir
|   +-- call.py                 # Demo agent: calls tools, closes session, saves claim
|   +-- run.sh
+-- demo-02-policy-swap/
|   +-- catalog.json
|   +-- cmcp-config.yaml        # Points to policies-v1/
|   +-- cmcp-config-v2.yaml     # Points to policies-v2/
|   +-- policies-v1/            # Cedar: permit all
|   +-- policies-v2/            # Cedar: deny write_file (hash differs from v1)
|   +-- check_hash.py           # Computes and compares bundle hashes
|   +-- run.sh
+-- demo-03-offline-trace/
    +-- verify.py               # cmcp_verify.verify_trace_claim (no network)
    +-- run.sh
```

---

## How it connects

```
Agent (call.py)
     |
     v  POST /mcp  Authorization: Bearer <token>
[cMCP runtime :8443]  <--  Cedar policy bundle (hash -> RTMR[2] on TDX)
     |
     v  POST http://localhost:9001/mcp  (JSON-RPC 2.0)
[server/server.py :9001]  -->  workspace/ (real file writes)
     |
POST /sessions/{id}/close
     |
     v
TRACE claim (Ed25519 signed)  -->  workspace/trace-claim.json
     |
     v
cmcp_verify.verify_trace_claim()  (no network, no operator trust)
```
