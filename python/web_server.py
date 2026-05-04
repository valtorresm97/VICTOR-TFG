from __future__ import annotations

import json
import logging
from pathlib import Path

from app_state import read_snapshot

logger = logging.getLogger("EEG_WEBUI")


class EEGWebServer:
    """Adaptador WebUI HTML Brick + websocket de snapshots."""

    def __init__(self, ui, backend):
        self.ui = ui
        self.backend = backend
        self.assets_dir = Path(__file__).resolve().parent.parent / "assets"

    def setup_routes(self):
        @self.ui.get("/")
        def index():
            return (self.assets_dir / "index.html").read_text(encoding="utf-8")

        @self.ui.get("/assets/{name}")
        def assets(name: str):
            p = self.assets_dir / name
            if not p.exists() or not p.is_file():
                return "", 404
            return p.read_text(encoding="utf-8")

        @self.ui.get("/status")
        def status():
            snap = self.backend.get_latest_snapshot() or read_snapshot(default={})
            return {"ok": True, "state": snap.get("status", {}).get("state", "unknown")}

        @self.ui.get("/latest")
        def latest():
            return self.backend.get_latest_snapshot() or read_snapshot(default={})

        @self.ui.websocket("/ws")
        def ws_handler(ws):
            while True:
                snap = self.backend.get_latest_snapshot()
                if snap:
                    self.ui.send_message(ws, json.dumps(snap))
                self.ui.sleep(0.2)
