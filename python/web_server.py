from __future__ import annotations

import logging
from pathlib import Path

from arduino.app_bricks.web_ui import WebUI

from app_state import read_snapshot

logger = logging.getLogger("EEG_WEBUI")


_NOTE_ENDPOINTS = {
    f"{name.lower()}{octave}": f"{note}{octave}"
    for octave in (3, 4, 5)
    for name, note in (
        ("c", "C"),
        ("cs", "C#"),
        ("d", "D"),
        ("ds", "D#"),
        ("e", "E"),
        ("f", "F"),
        ("fs", "F#"),
        ("g", "G"),
        ("gs", "G#"),
        ("a", "A"),
        ("as", "A#"),
        ("b", "B"),
    )
}


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
        self.ui.expose_api("POST", "/midi/panic", self.post_midi_panic)
        self.ui.expose_api("POST", "/midi/test-note", self.post_midi_test_note)
        self.ui.expose_api("POST", "/midi/test-note-ch1", self.post_midi_test_note_ch1)
        self.ui.expose_api("POST", "/midi/test-note-ch10", self.post_midi_test_note_ch10)
        self.ui.expose_api("POST", "/midi/test-sequence", self.post_midi_test_sequence)
        self.ui.expose_api("POST", "/midi/test-sequence-ch1", self.post_midi_test_sequence_ch1)
        self.ui.expose_api("POST", "/midi/test-sequence-ch10", self.post_midi_test_sequence_ch10)
        self.ui.expose_api("POST", "/midi/test-sequence-30s", self.post_midi_test_sequence_30s)
        self.ui.expose_api("POST", "/midi/test-sequence-30s-ch1", self.post_midi_test_sequence_30s_ch1)
        self.ui.expose_api("POST", "/midi/test-sequence-30s-ch10", self.post_midi_test_sequence_30s_ch10)
        self.ui.expose_api("POST", "/midi/test-loop/start", self.post_midi_test_loop_start)
        self.ui.expose_api("POST", "/midi/test-loop/start-ch1", self.post_midi_test_loop_start_ch1)
        self.ui.expose_api("POST", "/midi/test-loop/start-ch10", self.post_midi_test_loop_start_ch10)
        self.ui.expose_api("POST", "/midi/test-loop/stop", self.post_midi_test_loop_stop)
        self.ui.expose_api("POST", "/music/config", self.post_music_config)
        for scale_key in (
            "major",
            "minor",
            "blues",
            "spanish",
            "arabic",
            "harmonic_minor",
            "phrygian_dominant",
            "minor_pentatonic",
            "major_pentatonic",
        ):
            self.ui.expose_api("POST", f"/music/scale/{scale_key}", self._music_scale_handler(scale_key))
        for key, note in _NOTE_ENDPOINTS.items():
            self.ui.expose_api("POST", f"/music/root/{key}", self._music_root_handler(note))
            self.ui.expose_api("POST", f"/music/main/{key}", self._music_main_handler(note))
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

    def post_midi_test_note(self):
        return self.backend.send_test_note(channel=10, note=60, velocity=100, duration_sec=0.5)

    def post_midi_test_note_ch1(self):
        return self.backend.send_test_note(channel=1, note=60, velocity=100, duration_sec=0.5)

    def post_midi_test_note_ch10(self):
        return self.backend.send_test_note(channel=10, note=60, velocity=100, duration_sec=0.5)

    def post_midi_test_sequence(self):
        return self.backend.send_test_sequence(channel=10)

    def post_midi_test_sequence_ch1(self):
        return self.backend.send_test_sequence(channel=1)

    def post_midi_test_sequence_ch10(self):
        return self.backend.send_test_sequence(channel=10)

    def post_midi_test_sequence_30s(self):
        return self.backend.send_test_sequence(channel=10, repeat=75)

    def post_midi_test_sequence_30s_ch1(self):
        return self.backend.send_test_sequence(channel=1, repeat=75)

    def post_midi_test_sequence_30s_ch10(self):
        return self.backend.send_test_sequence(channel=10, repeat=75)

    def post_midi_test_loop_start(self):
        return self.backend.start_midi_test_loop(channel=1)

    def post_midi_test_loop_start_ch1(self):
        return self.backend.start_midi_test_loop(channel=1)

    def post_midi_test_loop_start_ch10(self):
        return self.backend.start_midi_test_loop(channel=10)

    def post_midi_test_loop_stop(self):
        return self.backend.stop_midi_test_loop()

    def post_music_config(self, *args, **kwargs):
        payload = {}
        for arg in args:
            if isinstance(arg, dict):
                payload.update(arg)
        payload.update(kwargs)
        return self.backend.update_music_config(
            root_note=payload.get("root_note"),
            main_note=payload.get("main_note"),
            scale_key=payload.get("scale_key"),
        )

    def _music_scale_handler(self, scale_key: str):
        def handler():
            return self.backend.update_music_config(scale_key=scale_key)
        return handler

    def _music_root_handler(self, note: str):
        def handler():
            return self.backend.update_music_config(root_note=note)
        return handler

    def _music_main_handler(self, note: str):
        def handler():
            return self.backend.update_music_config(main_note=note)
        return handler

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
