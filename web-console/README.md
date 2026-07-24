# Web console -- cMCP in the browser

The same enforcement the other demos show on the command line, in a small web UI
you can click through in front of an audience. Every number on the page comes
from the real gateway: real tool calls, real Cedar decisions, the real signed
TRACE record, and the real `cmcp verify` output.

```
pip install cmcp-runtime
python web-console/run.py
```

`run.py` starts three local processes and opens the console at
`http://localhost:8000`:

- the shared MCP filesystem server on `:9001` (`server/server.py`)
- the cMCP gateway on `:8443` (`CMCP_DEV_MODE=1`, software-only TEE)
- this demo's web server on `:8000`

Press Ctrl+C in the terminal to stop all three.

## What to click

1. **`write_file`** and **`read_file`** -- Cedar permits them. The call is
   forwarded to the tool and you see the real result.
2. **`list_dir`** -- Cedar forbids it. The gateway returns HTTP 403
   (`POLICY_DENY`) and the tool is never contacted.
3. **Close session -> TRACE record** -- the gateway signs a `GatewayClaim`:
   which tools ran, which were denied, the policy bundle hash, an Ed25519
   signature. Saved to `workspace/web-console-claim.json`.
4. **Verify record offline** -- runs `cmcp verify` against the saved record.
   In software-only mode the result is `partially_verified`: every
   cryptographic field checks out, only the hardware root is absent. On real
   TDX / SEV-SNP that last check passes too and it reads `verified`.

The **Policy** tab shows the exact Cedar bundle the gateway loaded. Its hash is
measured into the attestation at startup, so the policy that ran is provably the
one you approved.

## How it fits together

The browser never talks to the gateway directly. `webserver.py` serves the UI
and forwards to the gateway server-side, holding the bearer token so it stays
out of the browser and there is no CORS to configure. It is a thin proxy over
the same HTTP endpoints the CLI demos use (`POST /mcp`,
`GET /audit/export`, `POST /sessions/{id}/close`).

The Cedar policy uses the action dialect the runtime evaluates
(`write_file -> Action::"WriteFile"`), the same as `demo-01`. Nothing here is
mocked.

## Files

```
web-console/
  run.py            launcher (server + gateway + web server)
  webserver.py      static UI + /api proxy to the gateway
  cmcp-config.yaml  gateway config (enforcing, software-only)
  catalog.json      approved tools
  policies/         Cedar bundle
  web/              index.html, app.js, styles.css
```
