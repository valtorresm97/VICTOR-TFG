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
        self._logged_first_nonempty_snapshot = False
        self._setup_routes()

    def _setup_routes(self):
        self.ui.expose_api("GET", "/status", self.get_status)
        self.ui.expose_api("GET", "/latest", self.get_latest)
        self.ui.expose_api("POST", "/music/config", self.post_music_config)
        self.ui.expose_api("POST", "/midi/panic", self.post_midi_panic)
        self.ui.on_connect(self.on_connect)
        self.ui.on_disconnect(self.on_disconnect)

    def get_status(self):
        snap = self.backend.get_latest_snapshot() or read_snapshot(default={})
        st = (snap.get("status", {}) if isinstance(snap, dict) else {}) or {}
        return {"ok": True, "state": st.get("state", "unknown"), "window_ready": st.get("window_ready", False)}

    def get_latest(self):
        return self.backend.get_latest_snapshot() or read_snapshot(default={})

    def post_midi_panic(self):
        sent_events = self.backend.send_panic()
        return {"ok": True, "sent_events": int(sent_events)}

    def post_music_config(
        self,
        root_note=None,
        main_note=None,
        scale_name=None,
        channel=None,
        program=None,
        bar_sec=None,
        **payload,
    ):
        if isinstance(root_note, dict) and main_note is None and scale_name is None:
            request = dict(root_note)
        else:
            request = {
                "root_note": root_note,
                "main_note": main_note,
                "scale_name": scale_name,
                "channel": channel,
                "program": program,
                "bar_sec": bar_sec,
            }
            for key in ("json", "body", "payload"):
                if isinstance(payload.get(key), dict):
                    request.update(payload.pop(key))
            request.update(payload)
        try:
            music = self.backend.update_music_config(request)
        except Exception as exc:
            logger.warning("[WEB] invalid music config: %s", exc)
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "music": music}

    def on_connect(self, sid):
        logger.info("[WEB] connected: %s", sid)
        snap = self.get_latest()
        if snap:
            self.ui.send_message("eeg_snapshot", snap, room=sid)

    def on_disconnect(self, sid):
        logger.info("[WEB] disconnected: %s", sid)

    def publish_snapshot(self, snapshot: dict):
        if snapshot:
            if (not self._logged_first_nonempty_snapshot) and snapshot.get("rx", {}).get("rx_blocks_total", 0):
                logger.info("[WEB] first non-empty snapshot published")
                self._logged_first_nonempty_snapshot = True
            self.ui.send_message("eeg_snapshot", snapshot)

    def start(self):
        self.ui.start()
        try:
            logger.info("[WEB] WebUI started: %s", self.ui.url)
        except Exception:
            logger.info("[WEB] WebUI started")
