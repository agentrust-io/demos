"""Local web server for the cMCP browser console.

Serves the static UI in web/ and exposes a small JSON API that the browser
calls. The API forwards to the running cMCP gateway on :8443, holding the
bearer token here so the browser never sees it and there is no CORS to deal
with. Every response the UI shows is the gateway's real output.

Run indirectly via run.py, or standalone once the server and gateway are up:
    python webserver.py            # serves on http://localhost:8000
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = pathlib.Path(__file__).parent.resolve()
WEB = HERE / "web"
WORKSPACE = HERE.parent / "workspace"
POLICY_FILE = HERE / "policies" / "support-agent.cedar"
CATALOG_FILE = HERE / "catalog.json"
CLAIM_FILE = WORKSPACE / "web-console-claim.json"

GATEWAY = os.environ.get("CMCP_GATEWAY_URL", "http://localhost:8443")
TOKEN = os.environ.get("CMCP_BEARER_TOKEN", "demo-token")
PORT = int(os.environ.get("WEB_CONSOLE_PORT", "8000"))
SESSION_LABEL = "web-console-session"
WORKFLOW_ID = "web-console"

_CT = {".html": "text/html", ".js": "text/javascript", ".css": "text/css",
       ".svg": "image/svg+xml", ".json": "application/json"}


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
    return "cmcp"


def _gw(method: str, path: str, payload=None):
    """Call the gateway. Returns (body_dict, status_code)."""
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        GATEWAY + path, data=data, method=method,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read() or b"{}"), resp.status
    except urllib.error.HTTPError as exc:
        try:
            return json.loads(exc.read() or b"{}"), exc.code
        except json.JSONDecodeError:
            return {"error": "non-JSON error body"}, exc.code


def _tool_call(tool: str, arguments: dict):
    return _gw("POST", "/mcp", {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool,
            "arguments": arguments,
            "_cmcp": {"session_id": SESSION_LABEL, "workflow_id": WORKFLOW_ID},
        },
    })


def _close_session():
    """Resolve the internal session id from the audit export, then close it."""
    export, status = _gw("GET", f"/audit/export?session_id={SESSION_LABEL}")
    if status != 200:
        return {"error": "no session yet -- make a tool call first"}, 409
    entries = export.get("entries", [])
    if not entries:
        return {"error": "no session yet -- make a tool call first"}, 409
    internal = entries[0]["session_id"]
    claim, status = _gw("POST", f"/sessions/{internal}/close", {})
    if status == 200:
        WORKSPACE.mkdir(exist_ok=True)
        CLAIM_FILE.write_text(json.dumps(claim, indent=2))
    return claim, status


def _verify():
    if not CLAIM_FILE.exists():
        return {"error": "no claim yet -- close the session first"}, 409
    env = os.environ.copy()
    env["CMCP_DEV_MODE"] = "1"
    proc = subprocess.run([_find_cmcp(), "verify", str(CLAIM_FILE)],
                          capture_output=True, text=True, env=env)
    raw = (proc.stdout or "") + (proc.stderr or "")
    checks = [{"name": m.group(1).strip(), "status": m.group(2)}
              for m in re.finditer(r"\[cmcp verify\]\s+(.+?)\s{2,}(PASS|FAIL)", raw)]
    result = None
    m = re.search(r"RESULT:\s*(\w+)\s*\(([^)]+)\)", raw)
    if m:
        result = {"status": m.group(1), "detail": m.group(2)}
    return {"raw": raw.strip(), "checks": checks, "result": result}, 200


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # keep the terminal quiet
        pass

    def _send(self, status, body, content_type="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            return self._serve_static("index.html")
        if self.path.startswith("/web/"):
            return self._serve_static(self.path[len("/web/"):])
        if self.path == "/api/policy":
            catalog = json.loads(CATALOG_FILE.read_text())
            tools = [{"tool_name": c["tool_name"],
                      "description": c["approved_definition"]["description"]}
                     for c in catalog]
            return self._send(200, {"policy": POLICY_FILE.read_text(), "tools": tools,
                                    "gateway": GATEWAY, "workspace": str(WORKSPACE)})
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length) or b"{}") if length else {}

        if self.path == "/api/call":
            tool = payload.get("tool")
            args = payload.get("arguments", {})
            body, status = _tool_call(tool, args)
            allowed = status == 200
            decision = "allow" if allowed else (
                "deny" if body.get("error", {}).get("data", {}).get("error_code") == "POLICY_DENY"
                else "error")
            text = None
            if allowed:
                try:
                    text = body["result"]["content"][0]["text"]
                except (KeyError, IndexError, TypeError):
                    text = None
            return self._send(200, {"tool": tool, "http_status": status, "decision": decision,
                                    "text": text, "response": body})
        if self.path == "/api/close":
            body, status = _close_session()
            return self._send(200 if status == 200 else status, body)
        if self.path == "/api/verify":
            body, status = _verify()
            return self._send(status, body)
        if self.path == "/api/reset":
            # the gateway rotates its session on close; here we just clear the saved claim
            if CLAIM_FILE.exists():
                CLAIM_FILE.unlink()
            return self._send(200, {"ok": True})
        return self._send(404, {"error": "not found"})

    def _serve_static(self, rel):
        target = (WEB / rel).resolve()
        if not str(target).startswith(str(WEB.resolve())) or not target.is_file():
            return self._send(404, "not found", "text/plain")
        self._send(200, target.read_bytes(), _CT.get(target.suffix, "application/octet-stream"))


def main():
    WORKSPACE.mkdir(exist_ok=True)
    srv = ThreadingHTTPServer(("localhost", PORT), Handler)
    print(f"web console on http://localhost:{PORT}  (gateway {GATEWAY})", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
