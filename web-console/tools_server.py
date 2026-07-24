"""Mock business tools for the cMCP browser console.

Plain HTTP JSON-RPC 2.0, same shape the CLI demos' filesystem server uses. These
stand in for a bank's internal MCP tools: two read tools the support agent is
allowed to use, and two write/export tools policy forbids (so they never reach
this server -- they are here only so the "allowed" path has a real upstream).

    python tools_server.py      # serves on :9001
"""
import json
import pathlib

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

# Canned records, keyed the way a real lookup would be.
ACCOUNTS = {
    "AC-4821": {"account": "AC-4821", "type": "Checking", "balance": "$4,182.55",
                "currency": "USD", "status": "active"},
    "AC-7730": {"account": "AC-7730", "type": "Savings", "balance": "$28,940.10",
                "currency": "USD", "status": "active"},
}
CUSTOMERS = {
    "C-10293": {"customer_id": "C-10293", "name": "Jordan Rivera", "tier": "Premier",
                "email": "j****@example.com", "ssn": "***-**-4821", "kyc": "verified"},
    "C-55817": {"customer_id": "C-55817", "name": "Priya Nair", "tier": "Standard",
                "email": "p****@example.com", "ssn": "***-**-9037", "kyc": "verified"},
}


def _ok(id_, obj):
    text = json.dumps(obj, indent=2) if not isinstance(obj, str) else obj
    return {"jsonrpc": "2.0", "id": id_, "result": {"content": [{"type": "text", "text": text}]}}


def _err(id_, code, msg):
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": msg}}


async def handle(request: Request) -> JSONResponse:
    if request.method == "GET":
        return JSONResponse({"status": "ok"})
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(_err(None, -32700, "parse error"), status_code=400)

    id_ = body.get("id")
    params = body.get("params", {})
    name = params.get("name", "")
    args = params.get("arguments", {})

    if body.get("method") != "tools/call":
        return JSONResponse(_err(id_, -32601, "method not found"), status_code=404)

    if name == "get_balance":
        rec = ACCOUNTS.get(args.get("account_id", ""))
        if not rec:
            return JSONResponse(_ok(id_, {"error": "account not found"}))
        return JSONResponse(_ok(id_, rec))
    if name == "get_customer":
        rec = CUSTOMERS.get(args.get("customer_id", ""))
        if not rec:
            return JSONResponse(_ok(id_, {"error": "customer not found"}))
        return JSONResponse(_ok(id_, rec))
    # These are policy-forbidden, so the gateway blocks them before they arrive.
    # Implemented anyway so the demo is honest about what the tool would do.
    if name == "transfer_funds":
        return JSONResponse(_ok(id_, {"status": "transferred", "from": args.get("from_account"),
                                      "to": args.get("to_account"), "amount": args.get("amount")}))
    if name == "export_records":
        return JSONResponse(_ok(id_, {"status": "exported", "dataset": args.get("dataset"),
                                      "rows": 128412}))
    return JSONResponse(_err(id_, -32601, f"unknown tool: {name}"), status_code=404)


app = Starlette(routes=[
    Route("/mcp", handle, methods=["GET", "POST"]),
    Route("/health", handle, methods=["GET"]),
])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=9001)
