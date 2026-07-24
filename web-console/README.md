# Web console -- cMCP credit-risk assessment

A browser console for showing cMCP on a screen. It runs the **real
financial-services example** from `agentrust-io/examples` (an EU corporate
credit-risk agent) unmodified, behind a small web UI. Nothing here is a copy:
the tool server, Cedar policy, catalog, and agent all come from that repo,
pulled in as a git submodule under `vendor/`.

```
pip install cmcp-runtime httpx
git clone --recurse-submodules https://github.com/agentrust-io/demos.git   # or run.py inits the submodule
python demos/web-console/run.py            # opens http://localhost:8000
```

`run.py` starts three local processes and opens the console:

- the example's mock EU credit-risk MCP server on `:8080`
- the cMCP gateway on `:8443` (`CMCP_DEV_MODE=1`, software-only TEE)
- this demo's web server on `:8000`

Ctrl+C stops all three. (If the submodule is empty, `run.py` runs
`git submodule update --init` for you.)

## What it shows

An AI agent runs a six-step credit assessment through the gateway. It reads the
client's filings, screens for sanctions, pulls a credit-bureau report,
aggregates group exposure, and runs the PD/LGD model -- then passes that outcome
into the write. Cedar enforces the bank's controls **on the result**, so the
write is only recorded if the assessment passes them. Three obligors:

| Scenario | Obligor | Write | Blocked by |
|---|---|---|---|
| Performing | Rheintal Präzisionstechnik GmbH, €250k | allowed | -- |
| Concentration breach | Nordwind Logistik AG, €750k | blocked | CRR Art. 395 / EBA/GL/2020/06 |
| Sanctions / impaired | Meridian Trading DMCC, €200k | blocked | IFRS 9 (stage 3) |

Each deny carries the regulation and reason back as structured advice. Close the
session for the signed `RuntimeClaim`, then verify it offline with `cmcp verify`
(reads `partially_verified` in software-only mode; `verified` on real TDX /
SEV-SNP).

The **Policy** tab shows the Cedar bundle the gateway loaded and maps each
guardrail to the control it enforces. **What this shows** explains the four
properties the demo proves.

## How it fits together

The browser never talks to the gateway directly. `webserver.py` serves the UI
and, on **Run**, executes the example's own agent
(`vendor/examples/financial-services/agent/credit_risk_agent.py`) as a
subprocess against the gateway, then parses its output into the step timeline.
`run.py` supplies only a loopback gateway config that points at the example's
policy and catalog where they live -- it does not copy them. Bumping the
submodule pointer updates the example.

## Files

```
web-console/
  run.py            launcher (submodule init + example server + gateway + web server)
  webserver.py      static UI + /api (runs the example agent, runs cmcp verify)
  web/              index.html, app.js, styles.css
  vendor/examples/  git submodule -> agentrust-io/examples (the real scenario)
```
