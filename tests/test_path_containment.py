"""Negative tests for sibling-prefix traversal in the demo servers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _load(name: str, relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


def test_filesystem_server_rejects_sibling_with_workspace_prefix(tmp_path, monkeypatch):
    server = _load("demo_filesystem_server", "server/server.py")
    workspace = tmp_path / "workspace"
    sibling = tmp_path / "workspace-secret"
    workspace.mkdir()
    sibling.mkdir()
    (sibling / "secret.txt").write_text("not in the workspace", encoding="utf-8")
    monkeypatch.setattr(server, "WORKSPACE", workspace)

    with pytest.raises(ValueError, match="traversal"):
        server._resolve("../workspace-secret/secret.txt")


def test_filesystem_server_accepts_actual_descendant(tmp_path, monkeypatch):
    server = _load("demo_filesystem_server_descendant", "server/server.py")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setattr(server, "WORKSPACE", workspace)

    assert server._resolve("reports/result.txt") == workspace / "reports" / "result.txt"


def test_web_server_refuses_sibling_with_web_prefix(tmp_path, monkeypatch):
    webserver = _load("demo_webserver", "web-console/webserver.py")
    web = tmp_path / "web"
    sibling = tmp_path / "web-backup"
    web.mkdir()
    sibling.mkdir()
    (sibling / "secret.txt").write_text("not a public asset", encoding="utf-8")
    monkeypatch.setattr(webserver, "WEB", web)
    response = {}
    handler = object.__new__(webserver.Handler)
    handler._send = lambda status, body, content_type: response.update(
        status=status, body=body, content_type=content_type
    )

    handler._serve("../web-backup/secret.txt")

    assert response == {"status": 404, "body": "not found", "content_type": "text/plain"}
