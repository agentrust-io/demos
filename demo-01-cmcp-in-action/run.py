"""Demo 1: cMCP in action — cross-platform launcher (replaces run.sh).

Usage:
    python demo-01-cmcp-in-action/run.py          # from repo root
    python run.py                                  # from demo-01 directory
"""
import os
import pathlib
import shutil
import subprocess
import sys
import time

sys.stdout.reconfigure(line_buffering=True)

SCRIPT_DIR = pathlib.Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent


def _find_cmcp() -> str:
    found = shutil.which("cmcp")
    if found:
        return found
    import sysconfig
    candidates = [
        pathlib.Path(sys.executable).parent,
        pathlib.Path(sysconfig.get_path("scripts")),
        pathlib.Path(sysconfig.get_path("scripts", "nt_user")),
    ]
    for scripts in candidates:
        for name in ("cmcp.exe", "cmcp"):
            p = scripts / name
            if p.exists():
                return str(p)
    sys.exit("cmcp not found. Run: pip install cmcp-runtime")


def main() -> None:
    token = os.environ.setdefault("CMCP_BEARER_TOKEN", "demo-token")  # noqa: F841

    log_dir = SCRIPT_DIR
    server_log = open(log_dir / "server.log", "w")
    cmcp_log = open(log_dir / "cmcp.log", "w")

    server = cmcp_proc = None
    try:
        print("-- Starting MCP filesystem server on :9001 --", flush=True)
        server = subprocess.Popen(
            [sys.executable, str(REPO_ROOT / "server" / "server.py")],
            stdout=server_log, stderr=server_log,
        )
        time.sleep(1)

        print("-- Starting cMCP gateway (CMCP_DEV_MODE=1) on :8443 --", flush=True)
        env = os.environ.copy()
        env["CMCP_DEV_MODE"] = "1"
        cmcp_proc = subprocess.Popen(
            [_find_cmcp(), "start", "--config", str(SCRIPT_DIR / "cmcp-config.yaml")],
            stdout=cmcp_log, stderr=cmcp_log,
            cwd=SCRIPT_DIR, env=env,
        )
        time.sleep(2)

        print()
        subprocess.run([sys.executable, str(SCRIPT_DIR / "call.py")], check=True)

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


if __name__ == "__main__":
    main()
