"""cMCP browser console -- one-command launcher (cross-platform).

Runs the real financial-services example from the agentrust-io/examples repo
(pulled in as a git submodule under vendor/) behind a small web console. Nothing
is copied: the tool server, Cedar policy, catalog, and agent all come from the
submodule and run unmodified. This launcher only supplies a loopback gateway
config (tokenless dev mode binds to loopback) and starts:

    - the example's mock EU credit-risk MCP server on :8080
    - the cMCP gateway on :8443 (CMCP_DEV_MODE=1, software-only TEE)
    - this demo's web server on :8000

Then it opens http://localhost:8000. Ctrl+C stops everything.

    python web-console/run.py       # from repo root
    python run.py                   # from the web-console directory
"""
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import time
import webbrowser

sys.stdout.reconfigure(line_buffering=True)

HERE = pathlib.Path(__file__).parent.resolve()
REPO_ROOT = HERE.parent
EXAMPLE = HERE / "vendor" / "examples" / "financial-services"
WORKSPACE = REPO_ROOT / "workspace"
GATEWAY_CFG = WORKSPACE / "fs-gateway.yaml"
PORT = os.environ.get("WEB_CONSOLE_PORT", "8000")


def _find_cmcp() -> str:
    found = shutil.which("cmcp")
    if found:
        return found
    import sysconfig
    for scripts in (pathlib.Path(sys.executable).parent,
                    pathlib.Path(sysconfig.get_path("scripts"))):
        for name in ("cmcp.exe", "cmcp"):
            if (scripts / name).exists():
                return str(scripts / name)
    sys.exit("cmcp not found. Run: pip install cmcp-runtime httpx")


def _log_tail(what: str, lines: int = 15) -> str:
    """Return the tail of the log for `what`, or "" if there is nothing to show.

    A service that fails to bind has already written the reason to its log. The
    launcher used to point at the file and leave; printing the tail turns a 60
    second wait plus a scavenger hunt into the actual error.
    """
    name = "cmcp.log" if "cMCP" in what or "cmcp" in what else "server.log"
    path = pathlib.Path(__file__).parent.resolve() / name
    try:
        tail = path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]
    except OSError:
        return ""
    if not tail:
        return ""
    body = "\n".join("    " + line for line in tail)
    return f"\n\nLast {len(tail)} lines of {name}:\n{body}"


def _wait_for_port(port: int, what: str, process=None, timeout: float = 60.0) -> None:
    """Block until something is listening on 127.0.0.1:port.

    A fixed sleep used to be enough; cMCP Runtime now does attestation and audit
    setup before it binds, so the console raced startup and the first assessment
    failed on a refused connection.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            sys.exit(f"{what} exited with code {process.returncode} before listening on :{port}."
                     + _log_tail(what))
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return
        except OSError:
            time.sleep(0.25)
    sys.exit(f"{what} did not start listening on :{port} within {timeout:.0f}s."
             + _log_tail(what))


def _ensure_submodule() -> None:
    if (EXAMPLE / "agent" / "credit_risk_agent.py").exists():
        return
    print("-- fetching the examples submodule (first run)", flush=True)
    subprocess.run(["git", "submodule", "update", "--init", "--depth", "1",
                    "web-console/vendor/examples"], cwd=REPO_ROOT, check=True)
    if not (EXAMPLE / "agent" / "credit_risk_agent.py").exists():
        sys.exit("submodule missing. Run: git submodule update --init")


def _gateway_env(base_env: dict) -> dict:
    """Env for the approved gateway subprocess: software-only TEE, and no
    inherited bearer token -- see the CMCP_BEARER_TOKEN.pop comment at the
    call site for why."""
    env = dict(base_env)
    env["CMCP_DEV_MODE"] = "1" 
    # loopback demo, tokenless: the vendored credit_risk_agent.py never sends
    # an Authorization header. If CMCP_BEARER_TOKEN is inherited from the
    # shell -- e.g. left set from the terminal demos' README step -- cmcp
    # starts requiring it anyway and every /api/run call fails.
    env.pop("CMCP_BEARER_TOKEN", None)
    return env


def _write_gateway_config() -> None:
    # A loopback config pointing at the submodule example's own policy and
    # catalog. We do not copy them -- we reference them where they live.
    WORKSPACE.mkdir(exist_ok=True)
    GATEWAY_CFG.write_text(
        f"policy_bundle_path: {(EXAMPLE / 'policy').as_posix()}\n"
        f"catalog_path: {(EXAMPLE / 'catalog.json').as_posix()}\n"
        f"listen_addr: 127.0.0.1:8443\n"
        f"max_response_size_bytes: 2097152\n"
        f"audit_db_path: {(WORKSPACE / 'fs-audit.db').as_posix()}\n"
        f"attestation:\n"
        f"  provider: auto\n"
        f"  enforcement_mode: enforcing\n"
    )


def main() -> None:
    _ensure_submodule()
    _write_gateway_config()
    server_log = open(HERE / "server.log", "w")
    cmcp_log = open(HERE / "cmcp.log", "w")
    procs = []
    try:
        print("-- EU credit-risk MCP server on :8080", flush=True)
        procs.append(subprocess.Popen(
            [sys.executable, str(EXAMPLE / "server" / "mock_mcp_server.py")],
            stdout=server_log, stderr=server_log))
        _wait_for_port(8080, "EU credit-risk MCP server", procs[-1])

        print("-- cMCP gateway on :8443 (CMCP_DEV_MODE=1)", flush=True)
        procs.append(subprocess.Popen(
            [_find_cmcp(), "start", "--config", str(GATEWAY_CFG)],
            stdout=cmcp_log, stderr=cmcp_log, env=_gateway_env(os.environ)))
        _wait_for_port(8443, "cMCP gateway", procs[-1])

        print(f"-- web console on http://localhost:{PORT}", flush=True)
        web = subprocess.Popen([sys.executable, str(HERE / "webserver.py")], env=os.environ.copy())
        procs.append(web)
        _wait_for_port(int(PORT), "web console", web)

        url = f"http://localhost:{PORT}"
        print(f"\nOpen {url} (opening it for you now). Ctrl+C to stop.\n", flush=True)
        try:
            webbrowser.open(url)
        except Exception:
            pass
        web.wait()
    except KeyboardInterrupt:
        print("\nstopping...", flush=True)
    finally:
        for p in reversed(procs):
            if p and p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.kill()
        server_log.close()
        cmcp_log.close()


if __name__ == "__main__":
    main()
