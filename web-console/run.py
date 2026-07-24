"""cMCP browser console -- one-command launcher (cross-platform).

Starts three local processes and opens the console in your browser:
    - the demo MCP filesystem server on :9001 (shared server/server.py)
    - the cMCP gateway on :8443 (CMCP_DEV_MODE=1, software-only TEE)
    - this demo's web server on :8000

Everything the browser shows comes from the real gateway. Ctrl+C stops it all.

    python web-console/run.py      # from repo root
    python run.py                  # from the web-console directory
"""
import os
import pathlib
import shutil
import subprocess
import sys
import time
import webbrowser

sys.stdout.reconfigure(line_buffering=True)

HERE = pathlib.Path(__file__).parent.resolve()
REPO_ROOT = HERE.parent
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
    sys.exit("cmcp not found. Run: pip install cmcp-runtime")


def main():
    os.environ.setdefault("CMCP_BEARER_TOKEN", "demo-token")
    server_log = open(HERE / "server.log", "w")
    cmcp_log = open(HERE / "cmcp.log", "w")
    procs = []
    try:
        print("-- MCP filesystem server on :9001", flush=True)
        procs.append(subprocess.Popen(
            [sys.executable, str(REPO_ROOT / "server" / "server.py")],
            stdout=server_log, stderr=server_log))
        time.sleep(1)

        print("-- cMCP gateway on :8443 (CMCP_DEV_MODE=1)", flush=True)
        env = os.environ.copy()
        env["CMCP_DEV_MODE"] = "1"
        procs.append(subprocess.Popen(
            [_find_cmcp(), "start", "--config", str(HERE / "cmcp-config.yaml")],
            stdout=cmcp_log, stderr=cmcp_log, cwd=HERE, env=env))
        time.sleep(2)

        print(f"-- web console on http://localhost:{PORT}", flush=True)
        web = subprocess.Popen([sys.executable, str(HERE / "webserver.py")], env=os.environ.copy())
        procs.append(web)
        time.sleep(1)

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
