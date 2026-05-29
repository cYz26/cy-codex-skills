from __future__ import annotations

import json
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .dashboard import render_dashboard_html
from .store import list_snapshots, load_snapshot


def dashboard_assets_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "web" / "dashboard" / "dist"


def serve_dashboard(
    projection: dict[str, Any],
    *,
    store_path: str | Path | None = None,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> None:
    assets = dashboard_assets_dir()
    if not (assets / "index.html").exists():
        raise FileNotFoundError("Dashboard assets are missing. Build or export the Web dashboard before serving.")
    handler = make_handler(projection, store_path, assets)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Context Fixer dashboard: http://{host}:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Context Fixer dashboard stopped.")
    finally:
        server.server_close()


def make_handler(projection: dict[str, Any], store_path: str | Path | None, assets: Path):
    class DashboardHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/dashboard":
                self.write_json(projection)
                return
            if parsed.path == "/api/history":
                self.write_json({"snapshots": list_snapshots(store_path, repo=projection.get("overview", {}).get("repo"))})
                return
            if parsed.path.startswith("/api/snapshot/"):
                snapshot_id = parsed.path.rsplit("/", 1)[-1]
                snapshot = load_snapshot(snapshot_id, store_path)
                if snapshot is None:
                    self.write_json({"error": "snapshot not found"}, status=404)
                else:
                    self.write_json(snapshot)
                return
            if parsed.path in {"/", "/index.html"}:
                index = assets / "index.html"
                data = html.escape(json.dumps(projection, ensure_ascii=False), quote=False)
                content = index.read_text(encoding="utf-8").replace("__CONTEXT_FIXER_DASHBOARD_JSON__", data)
                self.write_bytes(content.encode("utf-8"), "text/html; charset=utf-8")
                return
            candidate = (assets / parsed.path.lstrip("/")).resolve()
            if assets in candidate.parents and candidate.exists() and candidate.is_file():
                self.write_bytes(candidate.read_bytes(), content_type(candidate))
                return
            self.write_json({"error": "not found"}, status=404)

        def log_message(self, _format: str, *args) -> None:
            return

        def write_json(self, payload: dict[str, Any], status: int = 200) -> None:
            self.write_bytes(json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", status)

        def write_bytes(self, payload: bytes, content_type_value: str, status: int = 200) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type_value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return DashboardHandler


def content_type(path: Path) -> str:
    return {
        ".html": "text/html; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".json": "application/json; charset=utf-8",
    }.get(path.suffix, "application/octet-stream")
