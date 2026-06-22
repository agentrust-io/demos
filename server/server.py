"""
Local MCP filesystem server for cMCP demos.

Plain HTTP JSON-RPC 2.0 server. cMCP's proxy posts directly to the URL
in the catalog entry, so the server must accept plain POST (not SSE).

Tools:
  write_file(path, content)  -- writes a file to ../workspace/
  read_file(path)            -- reads a file from ../workspace/

Run:
  python server.py
"""
import json
import pathlib

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

WORKSPACE = pathlib.Path(__file__).parent.parent / "workspace"
WORKSPACE.mkdir(exist_ok=True)


def _resolve(path: str) -> pathlib.Path:
    target = (WORKSPACE / path).resolve()
    if not str(target).startswith(str(WORKSPACE.resolve())):
        raise ValueError("path traversal not allowed")
    return target


def _ok(id_, result) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "result": {"content": [{"type": "text", "text": str(result)}]}}


def _err(id_, code: int, msg: str) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": msg}}


async def handle(request: Request) -> JSONResponse:
    if request.method == "GET":
        return JSONResponse({"status": "ok"})

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(_err(None, -32700, "parse error"), status_code=400)

    id_ = body.get("id")
    method = body.get("method", "")
    params = body.get("params", {})

    if method == "initialize":
        return JSONResponse({
            "jsonrpc": "2.0", "id": id_,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "demo-filesystem", "version": "0.1.0"},
            },
        })

    if method == "tools/list":
        return JSONResponse({"jsonrpc": "2.0", "id": id_, "result": {"tools": [
            {"name": "write_file", "description": "Write content to a file in the demo workspace",
             "inputSchema": {"type": "object", "required": ["path", "content"],
                             "properties": {"path": {"type": "string"}, "content": {"type": "string"}}}},
            {"name": "read_file", "description": "Read a file from the demo workspace",
             "inputSchema": {"type": "object", "required": ["path"],
                             "properties": {"path": {"type": "string"}}}},
            {"name": "list_dir", "description": "List files in the demo workspace",
             "inputSchema": {"type": "object",
                             "properties": {"path": {"type": "string", "default": ""}}}},
        ]}})

    if method != "tools/call":
        return JSONResponse(_err(id_, -32601, f"method not found: {method}"), status_code=404)

    name = params.get("name", "")
    args = params.get("arguments", {})

    try:
        if name == "write_file":
            target = _resolve(args["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(args["content"], encoding="utf-8")
            return JSONResponse(_ok(id_, f"Written {len(args['content'])} bytes to {args['path']}"))
        elif name == "read_file":
            target = _resolve(args["path"])
            return JSONResponse(_ok(id_, target.read_text(encoding="utf-8")))
        elif name == "list_dir":
            path = args.get("path", "")
            target = _resolve(path) if path else WORKSPACE
            entries = sorted(target.iterdir())
            listing = "\n".join(e.name + ("/" if e.is_dir() else "") for e in entries) or "(empty)"
            return JSONResponse(_ok(id_, listing))
        else:
            return JSONResponse(_err(id_, -32601, f"unknown tool: {name}"), status_code=404)
    except KeyError as exc:
        return JSONResponse(_err(id_, -32602, f"missing argument: {exc}"), status_code=400)
    except ValueError as exc:
        return JSONResponse(_err(id_, -32602, str(exc)), status_code=400)
    except FileNotFoundError as exc:
        return JSONResponse(_err(id_, -32603, str(exc)), status_code=404)
    except Exception as exc:
        return JSONResponse(_err(id_, -32603, str(exc)), status_code=500)


app = Starlette(routes=[
    Route("/mcp", handle, methods=["GET", "POST"]),
    Route("/health", handle, methods=["GET"]),
])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=9001)
