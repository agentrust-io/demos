"""
Demo 1 client — calls write_file then read_file through cMCP.

cMCP must be running on localhost:8443 before this script runs.
The MCP filesystem server must be running on localhost:9001.

Usage:
  python call.py

Output: the tool result plus the full TRACE claim from cMCP.
"""

import json
import sys
import time
import urllib.request

CMCP_URL = "http://localhost:8443"


def call_tool(tool_name: str, arguments: dict) -> dict:
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": int(time.time() * 1000),
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments,
        },
    }).encode()

    req = urllib.request.Request(
        f"{CMCP_URL}/mcp",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def main():
    print("=== Demo 1: cMCP in action ===\n")

    # Write a file through cMCP (Cedar policy must allow write_file)
    print(">> Calling write_file ...")
    result = call_tool("write_file", {
        "path": "hello.txt",
        "content": "Written under Cedar enforcement at agentrust CC Summit 2026\n",
    })
    print(json.dumps(result, indent=2))

    trace = result.get("result", {}).get("trace_claim")
    if trace:
        print("\n=== TRACE claim ===")
        print(f"  subject:              {trace['subject']}")
        print(f"  runtime.platform:     {trace['runtime']['platform']}")
        print(f"  runtime.measurement:  {trace['runtime']['measurement']}")
        print(f"  policy.bundle_hash:   {trace['policy']['bundle_hash']}")
        print(f"  policy.mode:          {trace['policy']['enforcement_mode']}")
        print(f"  transparency:         {trace.get('transparency', '(not set)')}")
        print("\nPolicy hash above is what goes into RTMR[2] on real TDX hardware.")
    else:
        print("\n(No trace_claim in response — check cMCP version)")

    print("\n>> Calling read_file ...")
    result2 = call_tool("read_file", {"path": "hello.txt"})
    content = result2.get("result", {}).get("content", [])
    if content:
        print("File content:", content[0].get("text", ""))


if __name__ == "__main__":
    main()
