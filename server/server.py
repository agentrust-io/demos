"""
Local MCP filesystem server for cMCP demos.

Exposes three tools that operate on the ../workspace/ directory:
  - write_file(path, content)  writes (or overwrites) a file
  - read_file(path)            reads a file
  - list_dir(path)             lists directory contents

Run:
  pip install mcp
  python server.py

The server starts on http://localhost:9001 using SSE transport.
"""

import pathlib
from mcp.server.fastmcp import FastMCP

WORKSPACE = pathlib.Path(__file__).parent.parent / "workspace"
WORKSPACE.mkdir(exist_ok=True)

mcp = FastMCP("demo-filesystem")


def _resolve(path: str) -> pathlib.Path:
    target = (WORKSPACE / path).resolve()
    if not str(target).startswith(str(WORKSPACE.resolve())):
        raise ValueError("path traversal not allowed")
    return target


@mcp.tool()
def write_file(path: str, content: str) -> str:
    """Write content to a file in the demo workspace."""
    target = _resolve(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Written {len(content)} bytes to {path}"


@mcp.tool()
def read_file(path: str) -> str:
    """Read a file from the demo workspace."""
    target = _resolve(path)
    return target.read_text(encoding="utf-8")


@mcp.tool()
def list_dir(path: str = "") -> str:
    """List files in the demo workspace (or a subdirectory)."""
    target = _resolve(path) if path else WORKSPACE
    entries = sorted(target.iterdir())
    return "\n".join(e.name + ("/" if e.is_dir() else "") for e in entries) or "(empty)"


if __name__ == "__main__":
    import uvicorn
    mcp.run(transport="sse", host="localhost", port=9001)
