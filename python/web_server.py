from __future__ import annotations

import logging
from pathlib import Path

from arduino.app_bricks.web_ui import WebUI

from app_state import read_snapshot

logger = logging.getLogger("EEG_WEBUI")


class EEGWebServer:
    """Servidor WebUI HTML Brick para snapshots EEG."""

    def __init__(self, backend, port: int = 7000):
        self.backend = backend
        assets_dir = Path(__file__).resolve().parent.parent / "assets"
        self.ui = WebUI(port=port, assets_dir_path=str(assets_dir))
        self._setup_routes()

    def _setup_routes(self):
        self.ui.expose_api("GET", "/status", self.get_status)
        self.ui.expose_api("GET", "/latest", self.get_latest)
        self.ui.on_connect(self.on_connect)
        self.ui.on_disconnect(self.on_disconnect)

    def get_status(self):
        snap = self.backend.get_latest_snapshot() or read_snapshot(default={})
        st = (snap.get("status", {}) if isinstance(snap, dict) else {}) or {}
        return {"ok": True, "state": st.get("state", "unknown"), "window_ready": st.get("window_ready", False)}

    def get_latest(self):
        return self.backend.get_latest_snapshot() or read_snapshot(default={})

    def on_connect(self, sid):
        logger.info("[WEB] connected: %s", sid)
        snap = self.get_latest()
        if snap:
            self.ui.send_message("eeg_snapshot", snap, room=sid)

    def on_disconnect(self, sid):
        logger.info("[WEB] disconnected: %s", sid)

    def publish_snapshot(self, snapshot: dict):
        if snapshot:
            self.ui.send_message("eeg_snapshot", snapshot)

    def start(self):
        self.ui.start()
        try:
            logger.info("[WEB] WebUI started: %s", self.ui.url)
        except Exception:
            logger.info("[WEB] WebUI started")
