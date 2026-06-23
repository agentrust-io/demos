"""Demo 2: Policy swap = attestation failure — cross-platform launcher (replaces run.sh).

Usage:
    python demo-02-policy-swap/run.py          # from repo root
    python run.py                              # from demo-02 directory
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(line_buffering=True)

SCRIPT_DIR = pathlib.Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
WORKSPACE = REPO_ROOT / "workspace"
CLAIM_PATH = WORKSPACE / "trace-claim.json"
V2_CLAIM_PATH = WORKSPACE / "trace-claim-v2.json"


def _find_cmcp() -> str:
    found = shutil.which("cmcp")
    if found:
        return found
    scripts = pathlib.Path(sys.executable).parent
    for name in ("cmcp.exe", "cmcp"):
        p = scripts / name
        if p.exists():
            return str(p)
    sys.exit("cmcp not found. Run: pip install cmcp-runtime")


def _post(url: str, payload: dict, token: str) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as exc:
        return json.loads(exc.read())


def main() -> None:
    if not CLAIM_PATH.exists():
        sys.exit("Run demo-01 first to produce a TRACE claim:\n  python demo-01-cmcp-in-action/run.py")

    token = os.environ.setdefault("CMCP_BEARER_TOKEN", "demo-token")

    print()
    print("=== Demo 2: Policy swap = attestation failure ===")
    print()

    # Step 0: bundle hashes
    print("-- Step 0: Policy bundle hashes --")
    sys.stdout.flush()
    subprocess.run([sys.executable, str(SCRIPT_DIR / "check_hash.py")], check=True)

    # Step 1: show v1 claim's policy hash
    print()
    print("-- Step 1: TRACE claim from demo-01 --")
    v1_claim = json.loads(CLAIM_PATH.read_text())
    v1_policy_hash = v1_claim["trace"]["policy"]["bundle_hash"]
    catalog_hash = v1_claim["gateway"]["catalog"]["hash"]
    print(f"  v1 policy.bundle_hash: {v1_policy_hash}")
    print(f"  catalog.hash:          {catalog_hash}")
    print()
    print("  A verifier who approved v1 pins the policy hash above.")

    log_dir = SCRIPT_DIR
    server_log = open(log_dir / "server.log", "w")
    cmcp_log = open(log_dir / "cmcp.log", "w")

    server = cmcp_proc = None
    try:
        # Step 2: start v2 gateway
        print()
        print("-- Step 2: Start cMCP with v2 policy (write_file DENIED) --")
        server = subprocess.Popen(
            [sys.executable, str(REPO_ROOT / "server" / "server.py")],
            stdout=server_log, stderr=server_log,
        )
        time.sleep(1)

        env = os.environ.copy()
        env["CMCP_DEV_MODE"] = "1"
        cmcp_proc = subprocess.Popen(
            [_find_cmcp(), "start", "--config", str(SCRIPT_DIR / "cmcp-config-v2.yaml")],
            stdout=cmcp_log, stderr=cmcp_log,
            cwd=SCRIPT_DIR, env=env,
        )
        time.sleep(2)

        # Step 3: write_file denied
        print()
        print("-- Step 3: write_file -> DENIED by v2 Cedar policy --")
        body = _post("http://localhost:8443/mcp", {
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {
                "name": "write_file",
                "arguments": {"path": "post-swap.txt", "content": "written after policy swap"},
                "_cmcp": {"workflow_id": "demo-02"},
            },
        }, token)
        error = body.get("error", {})
        code = error.get("data", {}).get("error_code", "?")
        print(f'  HTTP 403 -- {error.get("message", "?")} [{code}]')
        print('  Cedar forbid rule matched: Action::"WriteFile" denied by v2 policy')

        # Step 4: get v2 TRACE claim via read_file
        print()
        print("-- Step 4: Get v2 TRACE claim --")
        r1 = _post("http://localhost:8443/mcp", {
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "read_file", "arguments": {"path": "hello.txt"}, "_cmcp": {"workflow_id": "demo-02"}},
        }, token)
        session_id = r1["result"]["_cmcp"]["session_id"]

        close_req = urllib.request.Request(
            f"http://localhost:8443/sessions/{session_id}/close",
            data=b"{}", headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            method="POST",
        )
        with urllib.request.urlopen(close_req, timeout=10) as r2:
            v2_claim = json.loads(r2.read())

        v2_policy_hash = v2_claim["trace"]["policy"]["bundle_hash"]
        print(f"  v1 policy.bundle_hash: {v1_policy_hash}")
        print(f"  v2 policy.bundle_hash: {v2_policy_hash}")
        print()
        if v1_policy_hash != v2_policy_hash:
            print("  Hashes differ. A verifier with the v1 approved hash will reject v2 claims.")
        else:
            print("  ERROR: hashes should differ but are identical.")

        V2_CLAIM_PATH.write_text(json.dumps(v2_claim, indent=2))
        print("  v2 claim saved.")

    finally:
        for proc in (cmcp_proc, server):
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        server_log.close()
        cmcp_log.close()

    # Steps 5-6: verify (servers now stopped)
    v1_hash_out = subprocess.check_output(
        [sys.executable, str(SCRIPT_DIR / "check_hash.py"), "v1"], text=True
    ).split()[1]
    v2_hash_out = subprocess.check_output(
        [sys.executable, str(SCRIPT_DIR / "check_hash.py"), "v2"], text=True
    ).split()[1]
    cat_hash = json.loads(V2_CLAIM_PATH.read_text())["gateway"]["catalog"]["hash"]
    cmcp = _find_cmcp()

    print()
    print("-- Step 5: Verify v2 claim with v1 (pinned) hash -> POLICY_HASH_MISMATCH --")
    print("   A verifier that approved v1 now rejects any claim from the v2 gateway.")
    sys.stdout.flush()
    subprocess.run(
        [cmcp, "verify", str(V2_CLAIM_PATH), "--policy-hash", v1_hash_out, "--catalog-hash", cat_hash],
    )

    print()
    print("-- Step 6: Verify v2 claim with v2 hash -> passes --")
    print("   (Confirms the v2 claim itself is well-formed; only the pinned hash differs.)")
    sys.stdout.flush()
    subprocess.run(
        [cmcp, "verify", str(V2_CLAIM_PATH), "--policy-hash", v2_hash_out, "--catalog-hash", cat_hash],
    )

    print()
    print("  On real TDX hardware: RTMR[2] changes on policy swap.")
    print("  No claim from the v2 gateway can pass v1 verification.")
    print()


if __name__ == "__main__":
    main()
