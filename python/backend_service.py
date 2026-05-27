from __future__ import annotations

import logging
import os
import re
import threading
import time

from arduino.app_utils import Bridge

from eeg_signal_processor import EEGSignalProcessor
from receiver import EEGReceiver
from app_state import publish_snapshot, clear_runtime_state
from capture_manager import CaptureManager
from sonification_features import (
    SonificationFeatureAdapter,
    build_sonification_snapshot,
)
from spectral_quality import compute_spectral_quality

from scale_registry import build_scale_config
from music_utils import note_name_to_midi
from music_segment import MusicSegmentBuilder
from music_bar import BarGenerator
from music_note import NoteGenerator
from midi_live import (
    MidiLiveEvent,
    MidiScheduler,
    NOTE_OFF,
    NOTE_ON,
    PROGRAM_CHANGE,
    event_to_midi_bytes,
)
from midi_byte_transport import MidiByteTransport
from led_matrix_visualizer import LedMatrixConfig, build_led_matrix_frame
from led_matrix_transport import LedMatrixTransport
from eeg_contract import EEG_BLOCK_EVENT, FS_HZ, NUM_CH
from runtime_config import EEG_LED_MATRIX_ENABLED_ENV, EEG_MIDI_LIVE_ENABLED_ENV, env_bool


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EEG_BACKEND")


_NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def _midi_to_note_name(midi_note: int) -> str:
    note = max(0, min(127, int(midi_note)))
    octave = (note // 12) - 1
    return f"{_NOTE_NAMES[note % 12]}{octave}"


FEATURE_WINDOW_SEC = 4.0
FEATURE_HOP_SAMPLES = 64

SNAPSHOT_PUBLISH_PERIOD_SEC = 0.2
DISK_PUBLISH_PERIOD_SEC = 1.0


# ------------------------------------------------------------
# Configuración musical inicial fija
#
# De momento NO hay controles WebUI.
# Estos valores se cambiarán después desde la interfaz.
# ------------------------------------------------------------

MUSIC_BAR_SEC = 2.0

# MIDI usa canales internos 0..15. 9 corresponde al canal MIDI 10.
MUSIC_CHANNEL = 9
MUSIC_PROGRAM = 0

MUSIC_ROOT_NOTE = "C4"
MUSIC_MAIN_NOTE = "G4"

MUSIC_SCALE_FAMILY = "Diatonic"
MUSIC_SCALE_NAME = "Major (Ionian)"

RECENT_NOTES_MAX = 96
RECENT_NOTES_WINDOW_SEC = 20.0

MIDI_TEST_PROGRAM = 9  # Programa visible 10 en sintetizadores 1..128.
MIDI_TEST_LOOP_AUTOSTART = env_bool("EEG_MIDI_TEST_LOOP_AUTOSTART", True)
MIDI_TEST_LOOP_CHANNEL = max(1, min(16, int(os.environ.get("EEG_MIDI_TEST_LOOP_CHANNEL", "10"))))
MIDI_TEST_LOOP_NOTES = [60, 64, 67, 72]
MIDI_TEST_LOOP_NOTE_SEC = 0.08
MIDI_TEST_LOOP_GAP_SEC = 0.02


# Rama midi-config-v2: enviar MIDI live por defecto para validar la salida DIN.
# Se puede desactivar en placa con EEG_MIDI_LIVE_ENABLED=0.
MIDI_LIVE_ENABLED = env_bool(EEG_MIDI_LIVE_ENABLED_ENV, True)

MIDI_BRIDGE_METHOD = "midi_bytes"
MIDI_LOOKAHEAD_SEC = 0.02
MIDI_GENERATE_PERIOD_SEC = MUSIC_BAR_SEC


def _read_ads_diagnostic_mode(project_root: str) -> int | None:
    sketch_path = os.path.join(project_root, "sketch", "sketch.ino")
    try:
        with open(sketch_path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return None

    m = re.search(r"^\s*#define\s+ADS_DIAGNOSTIC_MODE\s+(\d+)\s*$", text, re.MULTILINE)
    return int(m.group(1)) if m else None


def _channel_status_for_ads_mode(mode: int | None) -> list[dict]:
    mode_value = int(mode) if mode is not None else None
    channels = []
    for idx in range(NUM_CH):
        active = not (mode_value == 5 and idx > 0)
        if mode_value == 5:
            role = "active_eeg" if idx == 0 else "powered_down"
        elif mode_value == 1:
            role = "shorted_input"
        elif mode_value == 2:
            role = "internal_test_signal"
        else:
            role = "active_eeg"
        channels.append(
            {
                "index": idx,
                "name": f"CH{idx + 1}",
                "active": active,
                "role": role,
            }
        )
    return channels


class BackendService:
    """
    Orquesta:

      1. Recepción EEG por Bridge.
      2. Buffer DSP.
      3. Cálculo de features.
      4. Conversión a sonification_features.
      5. Generación musical live.
      6. Scheduler MIDI live.
      7. Envío opcional de bytes MIDI al MCU.
      8. Publicación de snapshots ligeros.
    """

    def __init__(self):
        # ----------------------------------------------------
        # DSP / recepción
        # ----------------------------------------------------
        self.proc = EEGSignalProcessor(
            fs=FS_HZ,
            num_channels=NUM_CH,
            buffer_sec=10.0,
            psd_window_sec=FEATURE_WINDOW_SEC,
            window_type="hann",
            welch_overlap=0.5,
        )

        self.rx = EEGReceiver(
            fs_hz=FS_HZ,
            num_ch=NUM_CH,
            queue_max=512,
        )
        self.capture_manager = CaptureManager(
            project_root=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        self.project_root = self.capture_manager.project_root
        self.ads_diagnostic_mode = _read_ads_diagnostic_mode(self.project_root)
        self.channel_status = _channel_status_for_ads_mode(self.ads_diagnostic_mode)

        Bridge.provide("linux_started", self.rx.linux_started)
        logger.info("[BRIDGE] registered linux_started")

        Bridge.provide(EEG_BLOCK_EVENT, self.rx.eeg_block_uV)
        logger.info("[BRIDGE] registered %s", EEG_BLOCK_EVENT)

        # ----------------------------------------------------
        # Estado DSP / sonificación
        # ----------------------------------------------------
        self._last_features: dict = {}

        self.sonif_adapter = SonificationFeatureAdapter()
        self._last_sonification = None
        self._last_quality_rx_totals: dict[str, int] = {}
        self._last_spectral_quality: dict = {
            "score": 0.0,
            "state": "no_features",
            "gate_factor": 0.0,
            "valid_for_sonification": False,
            "freeze_recommended": True,
            "warnings": ["no_features"],
            "penalties": {},
            "inputs": {},
        }
        self._samples_since_feature = 0
        self._window_was_ready = False

        # ----------------------------------------------------
        # Estado musical live
        # ----------------------------------------------------
        self.music_scale = build_scale_config(
            MUSIC_SCALE_FAMILY,
            MUSIC_SCALE_NAME,
            MUSIC_ROOT_NOTE,
        )
        self.music_main_note_midi = note_name_to_midi(MUSIC_MAIN_NOTE)

        self.music_segment_builder = MusicSegmentBuilder(fs=FS_HZ)
        self.bar_gen = BarGenerator(random_seed=123)
        self.note_gen = NoteGenerator(
            default_channel=MUSIC_CHANNEL,
            default_program=MUSIC_PROGRAM,
        )

        self.midi_scheduler = MidiScheduler()
        self.midi_transport = MidiByteTransport(
            bridge_method=MIDI_BRIDGE_METHOD,
            enabled=MIDI_LIVE_ENABLED,
        )

        self.led_matrix_config = LedMatrixConfig.from_env(
            default_pitch_center=self.music_main_note_midi
        )
        self.led_matrix_transport = LedMatrixTransport(
            bridge_method=self.led_matrix_config.bridge_method,
            enabled=self.led_matrix_config.enabled,
            width=self.led_matrix_config.width,
            height=self.led_matrix_config.height,
        )
        self._last_led_frame_t = 0.0

        self._last_music_t = 0.0
        self._program_change_sent = False
        self._midi_direct_test_active = False
        self._midi_test_loop = {
            "active": bool(MIDI_TEST_LOOP_AUTOSTART),
            "channel": MIDI_TEST_LOOP_CHANNEL,
            "channel_zero_based": MIDI_TEST_LOOP_CHANNEL - 1,
            "notes": list(MIDI_TEST_LOOP_NOTES),
            "note_idx": 0,
            "phase": "program",
            "next_due": 0.0,
            "note_duration_sec": MIDI_TEST_LOOP_NOTE_SEC,
            "gap_sec": MIDI_TEST_LOOP_GAP_SEC,
            "program": MIDI_TEST_PROGRAM,
            "sent_events": 0,
            "failed_events": 0,
            "cycles": 0,
            "last_bytes": [],
            "last_event": None,
            "active_note": None,
        }

        self._last_notes_count = 0
        self._last_midi_due_count = 0
        self._last_midi_sent_count = 0
        self._last_rhythm_cadence = None
        self._last_chord_root_midi = None
        self._last_chord_pitches: list[int] = []
        self._recent_notes: list[dict] = []

        self._music_generation_errors_total = 0
        self._midi_pump_errors_total = 0

        # ----------------------------------------------------
        # Snapshot / publicación
        # ----------------------------------------------------
        self._last_snapshot_t = 0.0
        self._last_disk_publish_t = 0.0

        self._snapshot_lock = threading.Lock()
        self._latest_snapshot: dict = {}

        self._logged_first_snapshot = False
        self._logged_features_ready = False
        self._logged_first_music = False

    # --------------------------------------------------------
    # Snapshot
    # --------------------------------------------------------

    def _midi_mode(self) -> str:
        if self._midi_direct_test_active:
            return "diagnostic_direct_sequence"
        if self._midi_test_loop.get("active"):
            return "diagnostic_test_loop"
        return "eeg_live"

    def _build_quality_rx_delta_metrics(self, rxm: dict) -> dict[str, int]:
        """Calcula eventos RX desde la ultima ventana de features."""
        total_keys = (
            "invalid_status_total",
            "lost_frames_total",
            "lost_blocks_total",
            "queue_drops_frames_total",
            "queue_drops_blocks_total",
            "malformed_blocks_total",
        )
        out: dict[str, int] = {}
        next_totals: dict[str, int] = {}

        for key in total_keys:
            current = int(rxm.get(key, 0) or 0)
            previous = self._last_quality_rx_totals.get(key, current)
            delta_key = key.replace("_total", "_delta")
            out[delta_key] = max(0, current - previous)
            out[key] = current
            next_totals[key] = current

        self._last_quality_rx_totals = next_totals
        return out

    def _build_snapshot(self) -> dict:
        """Construye el snapshot público consumido por WebUI/disco."""
        rxm = self.rx.get_window_metrics(reset=False)
        now = time.monotonic()

        window_ready = self.proc.is_window_ready(FEATURE_WINDOW_SEC)
        rx_blocks_total = int(rxm.get("rx_blocks_total", 0) or 0)
        has_features = bool(self._last_features)

        if rx_blocks_total <= 0:
            state = "waiting_for_data"
        elif not window_ready:
            state = "waiting_for_window"
        elif has_features:
            state = "features_ready"
        else:
            state = "receiving"

        status = {
            "state": state,
            "window_ready": window_ready,
            "last_sample_idx": self.rx.last_idx,
        }

        feats = self._last_features or {}
        bp_rel = feats.get("bandpower_rel", {}) or {}
        bp_abs = feats.get("bandpower_abs", {}) or {}
        diagnostics = self.proc.compute_quality_diagnostics(
            channel_idx=0,
            window_sec=min(4.0, max(0.1, self.proc.available_seconds())),
            waveform_sec=2.0,
        )

        alpha_rel = float(bp_rel.get("alpha", 0.0) or 0.0)
        beta_rel = float(bp_rel.get("beta", 0.0) or 0.0)
        alpha_beta_ratio = (alpha_rel / beta_rel) if beta_rel > 1e-12 else None

        dominant_band = None
        if bp_rel:
            dominant_band = max(
                bp_rel.items(),
                key=lambda kv: float(kv[1] or 0.0),
            )[0]

        return {
            "ts_monotonic": now,
            "config": {
                "fs_hz": FS_HZ,
                "num_ch": NUM_CH,
                "feature_window_sec": FEATURE_WINDOW_SEC,
                "feature_hop_samples": FEATURE_HOP_SAMPLES,
                "psd_method": "multitaper",
                "channel_idx": 0,
                "ads_diagnostic_mode": self.ads_diagnostic_mode,
                "channels": self.channel_status,
            },
            "status": status,
            "rx": {
                "rx_frame_rate_hz": rxm.get("rx_frame_rate_hz", 0.0),
                "rx_block_rate_hz": rxm.get("rx_block_rate_hz", 0.0),
                "rx_frames_total": rxm.get("rx_frames_total", 0),
                "rx_blocks_total": rxm.get("rx_blocks_total", 0),
                "queue_frames_current": rxm.get("queue_frames_current", 0),
                "queue_blocks_current": rxm.get("queue_blocks_current", 0),
                "lost_frames_total": rxm.get("lost_frames_total", 0),
                "lost_blocks_total": rxm.get("lost_blocks_total", 0),
                "malformed_blocks_total": rxm.get("malformed_blocks_total", 0),
                "invalid_status_total": rxm.get("invalid_status_total", 0),
                "queue_drops_frames_total": rxm.get("queue_drops_frames_total", 0),
                "queue_drops_blocks_total": rxm.get("queue_drops_blocks_total", 0),
            },
            "features": {
                "rms": feats.get("rms"),
                "peak_freq": feats.get("peak_freq"),
                "peak_delta": feats.get("peak_delta"),
                "peak_theta": feats.get("peak_theta"),
                "peak_alpha": feats.get("peak_alpha"),
                "peak_beta": feats.get("peak_beta"),
                "peak_gamma": feats.get("peak_gamma"),
                "dominant_band": dominant_band,
                "alpha_beta_ratio": alpha_beta_ratio,
                "bandpower_rel": bp_rel,
                "bandpower_abs": bp_abs,
            },
            "diagnostics": diagnostics,
            "spectral_quality": self._last_spectral_quality,
            "capture": self.capture_manager.get_status(),
            "sonification": build_sonification_snapshot(
                self._last_sonification
            ),
            "music": {
                "bar_sec": MUSIC_BAR_SEC,
                "channel": MUSIC_CHANNEL,
                "program": MUSIC_PROGRAM,
                "root_note": MUSIC_ROOT_NOTE,
                "main_note": MUSIC_MAIN_NOTE,
                "scale_family": MUSIC_SCALE_FAMILY,
                "scale_name": MUSIC_SCALE_NAME,
                "rhythm_cadence": self._last_rhythm_cadence,
                "current_chord_root_midi": self._last_chord_root_midi,
                "current_chord_pitches": list(self._last_chord_pitches),
                "current_chord_notes": [
                    _midi_to_note_name(p) for p in self._last_chord_pitches
                ],
                "last_notes_count": self._last_notes_count,
                "recent_notes": list(self._recent_notes),
                "generation_errors_total": self._music_generation_errors_total,
            },
            "midi": {
                "mode": self._midi_mode(),
                "scheduler": self.midi_scheduler.get_status(),
                "transport": self.midi_transport.get_status(),
                "test_loop": self.get_midi_test_loop_status(),
                "last_due_events": self._last_midi_due_count,
                "last_sent_events": self._last_midi_sent_count,
                "pump_errors_total": self._midi_pump_errors_total,
                "live_enabled": MIDI_LIVE_ENABLED,
                "lookahead_sec": MIDI_LOOKAHEAD_SEC,
                "mcu_handler": MIDI_BRIDGE_METHOD,
                "enabled_source": EEG_MIDI_LIVE_ENABLED_ENV,
            },
            "led_matrix": {
                "config": self.led_matrix_config.to_dict(),
                "transport": self.led_matrix_transport.get_status(),
                "enabled_source": EEG_LED_MATRIX_ENABLED_ENV,
                "mcu_handler": self.led_matrix_config.bridge_method,
            },
            "performance": {
                "snapshot_publish_period_sec": SNAPSHOT_PUBLISH_PERIOD_SEC,
                "disk_publish_period_sec": DISK_PUBLISH_PERIOD_SEC,
                "midi_generate_period_sec": MIDI_GENERATE_PERIOD_SEC,
                "recent_notes_window_sec": RECENT_NOTES_WINDOW_SEC,
                "led_matrix_refresh_rate_hz": self.led_matrix_config.refresh_rate_hz,
            },
            "errors": {
                "music_generation_errors_total": self._music_generation_errors_total,
                "midi_pump_errors_total": self._midi_pump_errors_total,
            },
        }

    # --------------------------------------------------------
    # Generación musical live
    # --------------------------------------------------------

    def _remember_recent_notes(self, notes, time_origin: float) -> None:
        """Guarda una ventana pequeña de notas para debug/piano roll UI."""
        cutoff = float(time_origin) - RECENT_NOTES_WINDOW_SEC

        recent = [
            note
            for note in self._recent_notes
            if float(note.get("abs_end", 0.0) or 0.0) >= cutoff
        ]

        for note in notes:
            abs_start = float(time_origin) + float(note.t_start)
            abs_end = float(time_origin) + float(note.t_end)
            recent.append(
                {
                    "abs_start": abs_start,
                    "abs_end": abs_end,
                    "t_start": float(note.t_start),
                    "t_end": float(note.t_end),
                    "pitch_midi": int(note.pitch_midi),
                    "note_name": _midi_to_note_name(note.pitch_midi),
                    "velocity": int(note.velocity),
                    "channel": int(note.channel),
                    "program": int(note.program),
                }
            )

        recent.sort(key=lambda n: (n["abs_start"], n["pitch_midi"]))
        self._recent_notes = recent[-RECENT_NOTES_MAX:]
        self._last_notes_count = len(self._recent_notes)

    def _remember_midi_test_note(
        self,
        *,
        pitch_midi: int,
        velocity: int,
        channel: int,
        program: int,
        abs_start: float,
        abs_end: float,
    ) -> None:
        """Añade notas del loop diagnóstico al mismo piano roll web."""
        cutoff = float(abs_end) - RECENT_NOTES_WINDOW_SEC
        recent = [
            note
            for note in self._recent_notes
            if float(note.get("abs_end", 0.0) or 0.0) >= cutoff
        ]
        recent.append(
            {
                "abs_start": float(abs_start),
                "abs_end": max(float(abs_start) + 0.03, float(abs_end)),
                "t_start": 0.0,
                "t_end": max(0.03, float(abs_end) - float(abs_start)),
                "pitch_midi": int(pitch_midi),
                "note_name": _midi_to_note_name(int(pitch_midi)),
                "velocity": int(velocity),
                "channel": int(channel),
                "program": int(program),
                "source": "midi_test_loop",
            }
        )
        recent.sort(key=lambda n: (n["abs_start"], n["pitch_midi"]))
        self._recent_notes = recent[-RECENT_NOTES_MAX:]

    def _maybe_generate_music(self, now: float) -> None:
        """
        Genera un compás musical cada MUSIC_GENERATE_PERIOD_SEC.

        Requisitos:
          - Ya debe existir self._last_sonification.
          - Debe ser válida.
          - No debe bloquear la recepción EEG.
        """
        if self._last_sonification is None:
            return

        if not getattr(self._last_sonification, "valid", False):
            return

        if (now - self._last_music_t) < MIDI_GENERATE_PERIOD_SEC:
            return

        try:
            music_segment = self.music_segment_builder.build_live_segment(
                sonification_features=self._last_sonification,
                user_scale=self.music_scale,
                user_main_note_midi=self.music_main_note_midi,
                eeg_features=self._last_features,
                t_start=0.0,
                duration_sec=MUSIC_BAR_SEC,
            )

            bar = self.bar_gen.generate_live_bar(
                segment=music_segment,
                index=0,
            )
            self._last_rhythm_cadence = music_segment.rhythm_cadence.name
            self._last_chord_root_midi = int(bar.chord_root_midi)
            self._last_chord_pitches = [int(p) for p in bar.chord_pitches]

            notes = self.note_gen.generate_notes_for_bar(
                segment=music_segment,
                bar=bar,
                channel=MUSIC_CHANNEL,
                program=MUSIC_PROGRAM,
            )

            # Enviar program_change una sola vez al inicio.
            if not self._program_change_sent:
                self.midi_scheduler.schedule_program_change(
                    program=MUSIC_PROGRAM,
                    channel=MUSIC_CHANNEL,
                    due_time=now,
                )
                self._program_change_sent = True

            # Los NoteEvent tienen tiempos 0..MUSIC_BAR_SEC.
            # time_origin=now los convierte al reloj monotónico actual.
            self.midi_scheduler.schedule_notes(
                notes=notes,
                time_origin=now,
            )

            self._last_notes_count = len(notes)
            self._remember_recent_notes(notes, time_origin=now)
            self._last_music_t = now

            if not self._logged_first_music:
                logger.info(
                    "[MUSIC] first live bar generated: notes=%s",
                    len(notes),
                )
                self._logged_first_music = True

        except Exception as exc:
            self._music_generation_errors_total += 1
            logger.exception("[MUSIC] generation error: %s", exc)

    # --------------------------------------------------------
    # LED matrix piano scroll
    # --------------------------------------------------------

    def _maybe_update_led_matrix(self, now: float) -> None:
        """
        Calcula y, si esta activado, envia un frame LED desde recent_notes.

        Usa exactamente la misma lista que consume el piano roll web para que
        la matriz fisica sea una vista compacta, no otro pipeline musical.
        """
        if not self.led_matrix_transport.enabled:
            return

        period = 1.0 / max(1.0, float(self.led_matrix_config.refresh_rate_hz))
        if (float(now) - self._last_led_frame_t) < period:
            return

        frame = build_led_matrix_frame(
            self._recent_notes,
            now=float(now),
            window_sec=RECENT_NOTES_WINDOW_SEC,
            config=self.led_matrix_config,
        )
        self._last_led_frame_t = float(now)

        self.led_matrix_transport.send_frame(frame)

    # --------------------------------------------------------
    # MIDI pump
    # --------------------------------------------------------

    def _pump_midi(self, now: float) -> None:
        """
        Extrae eventos MIDI vencidos del scheduler y los manda al transporte.

        Si MIDI_LIVE_ENABLED=False:
          - Los eventos vencidos se extraen igualmente.
          - El transporte los cuenta como dropped.
          - Esto permite validar generación/scheduler sin sketch.
        """
        try:
            due_events = self.midi_scheduler.pop_due_events(
                now=now,
                lookahead_sec=MIDI_LOOKAHEAD_SEC,
                max_events=64,
            )

            self._last_midi_due_count = len(due_events)

            if due_events:
                self._last_midi_sent_count = self.midi_transport.send_events(
                    due_events
                )
            else:
                self._last_midi_sent_count = 0

        except Exception as exc:
            self._midi_pump_errors_total += 1
            logger.exception("[MIDI] pump error: %s", exc)

    def _send_midi_test_event(self, event: MidiLiveEvent) -> bool:
        data = event_to_midi_bytes(event)
        ok = self.midi_transport.send_event(event)
        self._midi_test_loop["last_bytes"] = [int(x) for x in data]
        self._midi_test_loop["last_event"] = event.type
        if ok:
            self._midi_test_loop["sent_events"] += 1
        else:
            self._midi_test_loop["failed_events"] += 1
        return ok

    def _pump_midi_test_loop(self, now: float) -> None:
        """Emite una secuencia MIDI diagnóstica desde el loop App Lab."""
        if not self._midi_test_loop.get("active"):
            return
        if now < float(self._midi_test_loop.get("next_due", 0.0) or 0.0):
            return

        channel_zero = int(self._midi_test_loop["channel_zero_based"])
        phase = str(self._midi_test_loop.get("phase", "program"))
        notes = list(self._midi_test_loop.get("notes", MIDI_TEST_LOOP_NOTES)) or [60]

        try:
            if phase == "program":
                event = MidiLiveEvent(
                    sort_index=now,
                    due_time=now,
                    type=PROGRAM_CHANGE,
                    channel=channel_zero,
                    data1=int(self._midi_test_loop.get("program", MIDI_TEST_PROGRAM)),
                    data2=0,
                )
                self._send_midi_test_event(event)
                self._midi_test_loop["phase"] = "note_on"
                self._midi_test_loop["next_due"] = now + 0.02
                return

            note_idx = int(self._midi_test_loop.get("note_idx", 0)) % len(notes)
            note = int(notes[note_idx])

            if phase == "note_on":
                event = MidiLiveEvent(
                    sort_index=now,
                    due_time=now,
                    type=NOTE_ON,
                    channel=channel_zero,
                    data1=note,
                    data2=100,
                )
                self._send_midi_test_event(event)
                self._midi_test_loop["active_note"] = {
                    "pitch_midi": note,
                    "velocity": 100,
                    "channel": channel_zero,
                    "program": int(self._midi_test_loop.get("program", MIDI_TEST_PROGRAM)),
                    "abs_start": now,
                }
                self._midi_test_loop["phase"] = "note_off"
                self._midi_test_loop["next_due"] = now + float(self._midi_test_loop["note_duration_sec"])
                return

            event = MidiLiveEvent(
                sort_index=now,
                due_time=now,
                type=NOTE_OFF,
                channel=channel_zero,
                data1=note,
                data2=0,
            )
            self._send_midi_test_event(event)
            active_note = self._midi_test_loop.get("active_note") or {}
            self._remember_midi_test_note(
                pitch_midi=int(active_note.get("pitch_midi", note)),
                velocity=int(active_note.get("velocity", 100)),
                channel=int(active_note.get("channel", channel_zero)),
                program=int(active_note.get("program", MIDI_TEST_PROGRAM)),
                abs_start=float(active_note.get("abs_start", now)),
                abs_end=now,
            )
            self._midi_test_loop["active_note"] = None

            note_idx = (note_idx + 1) % len(notes)
            if note_idx == 0:
                self._midi_test_loop["cycles"] += 1
            self._midi_test_loop["note_idx"] = note_idx
            self._midi_test_loop["phase"] = "note_on"
            self._midi_test_loop["next_due"] = now + float(self._midi_test_loop["gap_sec"])

        except Exception as exc:
            self._midi_pump_errors_total += 1
            self._midi_test_loop["failed_events"] += 1
            logger.exception("[MIDI] test loop error: %s", exc)

    # --------------------------------------------------------
    # Loop principal
    # --------------------------------------------------------

    def step(self):
        """
        Paso principal del backend.

        Orden:
          1. Drena recepción EEG.
          2. Calcula features cuando toca.
          3. Actualiza sonification features.
          4. Genera música live si toca.
          5. Bombea MIDI live.
          6. Publica snapshot.
        """
        self.capture_manager.poll_request()
        _, drained_frames = self.rx.drain_blocks_to_processor(
            self.proc,
            max_blocks=16,
            block_sink=self.capture_manager.add_block,
        )
        self.capture_manager.step()

        window_ready = self.proc.is_window_ready(
            window_sec=FEATURE_WINDOW_SEC
        )
        need_feature = False

        if window_ready:
            if not self._window_was_ready:
                self._window_was_ready = True
                self._samples_since_feature = 0
                need_feature = True
            else:
                self._samples_since_feature += drained_frames
                if self._samples_since_feature >= FEATURE_HOP_SAMPLES:
                    self._samples_since_feature -= FEATURE_HOP_SAMPLES
                    need_feature = True
        else:
            self._window_was_ready = False
            self._samples_since_feature = 0

        if need_feature and drained_frames > 0:
            try:
                feats = self.proc.compute_live_features(
                    channel_idx=0,
                    window_sec=FEATURE_WINDOW_SEC,
                    psd_method="multitaper",
                )

                if feats:
                    self._last_features = feats
                    diagnostics = self.proc.compute_quality_diagnostics(
                        channel_idx=0,
                        window_sec=FEATURE_WINDOW_SEC,
                        waveform_sec=2.0,
                    )
                    rxm = self.rx.get_window_metrics(reset=False)
                    quality_rxm = self._build_quality_rx_delta_metrics(rxm)
                    quality = compute_spectral_quality(
                        self._last_features,
                        diagnostics,
                        quality_rxm,
                        window_ready=True,
                    )
                    self._last_spectral_quality = quality.to_dict()
                    self._last_sonification = self.sonif_adapter.update(
                        self._last_features,
                        quality=self._last_spectral_quality,
                    )

                    if not self._logged_features_ready:
                        logger.info("[DSP] features ready")
                        self._logged_features_ready = True

            except Exception as e:
                logger.exception("feature computation error: %s", e)

        now = time.monotonic()

        # El loop diagnóstico MIDI sale desde App Lab sin depender de shell ni
        # EEG. Mientras esté activo no mezclamos la sonificación musical live.
        if self._midi_test_loop.get("active"):
            self._pump_midi_test_loop(now=now)
        elif self._midi_direct_test_active:
            self._last_midi_due_count = 0
            self._last_midi_sent_count = 0
        else:
            self._maybe_generate_music(now=now)
            self._pump_midi(now=now)
        self._maybe_update_led_matrix(now=now)

        if (now - self._last_snapshot_t) >= SNAPSHOT_PUBLISH_PERIOD_SEC:
            snap = self._build_snapshot()

            with self._snapshot_lock:
                self._latest_snapshot = snap

            if (
                not self._logged_first_snapshot
                and int(snap.get("rx", {}).get("rx_blocks_total", 0) or 0) > 0
            ):
                logger.info("[BACKEND] first snapshot published")
                self._logged_first_snapshot = True

            self._last_snapshot_t = now

        if (now - self._last_disk_publish_t) >= DISK_PUBLISH_PERIOD_SEC:
            with self._snapshot_lock:
                snap = dict(self._latest_snapshot)

            if snap:
                publish_snapshot(snap)

            self._last_disk_publish_t = now

    def start(self):
        """Hook explícito de arranque para main.py."""
        return None

    def send_panic(self) -> int:
        """Envía All Sound Off / All Notes Off si el transporte MIDI está activo."""
        try:
            events = self.midi_scheduler.panic()
            if not self.midi_transport.enabled:
                return 0
            return self.midi_transport.send_events(events)
        except Exception as exc:
            self._midi_pump_errors_total += 1
            logger.exception("[MIDI] panic error: %s", exc)
            return 0

    def start_midi_test_loop(self, channel: int = 1) -> dict:
        channel_human = max(1, min(16, int(channel)))
        self._midi_test_loop.update(
            {
                "active": True,
                "channel": channel_human,
                "channel_zero_based": channel_human - 1,
                "notes": list(MIDI_TEST_LOOP_NOTES),
                "note_idx": 0,
                "phase": "program",
                "next_due": 0.0,
                "sent_events": 0,
                "failed_events": 0,
                "cycles": 0,
                "last_bytes": [],
                "last_event": None,
                "active_note": None,
            }
        )
        self.midi_scheduler.clear()
        return self.get_midi_test_loop_status()

    def stop_midi_test_loop(self) -> dict:
        self._midi_test_loop["active"] = False
        self.send_panic()
        return self.get_midi_test_loop_status()

    def get_midi_test_loop_status(self) -> dict:
        return {
            "active": bool(self._midi_test_loop.get("active")),
            "autostart": MIDI_TEST_LOOP_AUTOSTART,
            "channel": int(self._midi_test_loop.get("channel", MIDI_TEST_LOOP_CHANNEL)),
            "channel_zero_based": int(self._midi_test_loop.get("channel_zero_based", MIDI_TEST_LOOP_CHANNEL - 1)),
            "notes": list(self._midi_test_loop.get("notes", MIDI_TEST_LOOP_NOTES)),
            "program": int(self._midi_test_loop.get("program", MIDI_TEST_PROGRAM)),
            "phase": self._midi_test_loop.get("phase"),
            "note_idx": int(self._midi_test_loop.get("note_idx", 0)),
            "cycles": int(self._midi_test_loop.get("cycles", 0)),
            "sent_events": int(self._midi_test_loop.get("sent_events", 0)),
            "failed_events": int(self._midi_test_loop.get("failed_events", 0)),
            "last_event": self._midi_test_loop.get("last_event"),
            "last_bytes": list(self._midi_test_loop.get("last_bytes", [])),
            "note_duration_sec": float(self._midi_test_loop.get("note_duration_sec", MIDI_TEST_LOOP_NOTE_SEC)),
            "gap_sec": float(self._midi_test_loop.get("gap_sec", MIDI_TEST_LOOP_GAP_SEC)),
        }

    def send_test_note(
        self,
        channel: int = 10,
        note: int = 60,
        velocity: int = 100,
        duration_sec: float = 0.5,
        program: int | None = MIDI_TEST_PROGRAM,
    ) -> dict:
        """
        Envía una nota MIDI fija sin depender de EEG, DSP ni scheduler musical.

        channel usa numeración humana 1..16. Internamente MIDI codifica 0..15.
        Internamente reutiliza la ruta de secuencia para evitar divergencias.
        """
        return self.send_test_sequence(
            channel=channel,
            notes=[note],
            velocity=velocity,
            note_duration_sec=duration_sec,
            gap_sec=0.0,
            program=program,
        )

    def send_test_sequence(
        self,
        channel: int = 10,
        notes: list[int] | None = None,
        velocity: int = 100,
        note_duration_sec: float = 0.08,
        gap_sec: float = 0.02,
        program: int | None = MIDI_TEST_PROGRAM,
        repeat: int = 1,
    ) -> dict:
        """
        Envía una secuencia fija de notas sin depender de EEG.

        La secuencia por defecto es C4-E4-G4-C5, util para distinguir una
        prueba melodica de un golpe percusivo en canal 10.
        """
        channel_human = max(1, min(16, int(channel)))
        channel_zero = channel_human - 1
        velocity_value = max(1, min(127, int(velocity)))
        duration = max(0.03, min(2.0, float(note_duration_sec)))
        gap = max(0.0, min(2.0, float(gap_sec)))
        repeat_count = max(1, min(64, int(repeat)))
        note_values = notes if notes is not None else [60, 64, 67, 72]
        note_values = [max(0, min(127, int(n))) for n in note_values][:32]
        if not note_values:
            note_values = [60]

        sent = 0
        failed = 0
        bytes_sent: list[list[int]] = []
        now = time.monotonic()
        restore_loop = bool(self._midi_test_loop.get("active"))

        try:
            if restore_loop:
                self._midi_test_loop["active"] = False
                self._midi_test_loop["active_note"] = None
                self.midi_scheduler.clear()
            self._midi_direct_test_active = True

            if program is not None:
                program_event = MidiLiveEvent(
                    sort_index=now,
                    due_time=now,
                    type=PROGRAM_CHANGE,
                    channel=channel_zero,
                    data1=max(0, min(127, int(program))),
                    data2=0,
                )
                data = event_to_midi_bytes(program_event)
                if self.midi_transport.send_event(program_event):
                    sent += 1
                    bytes_sent.append([int(x) for x in data])
                else:
                    failed += 1

            for _ in range(repeat_count):
                for note_value in note_values:
                    note_on = MidiLiveEvent(
                        sort_index=now,
                        due_time=now,
                        type=NOTE_ON,
                        channel=channel_zero,
                        data1=note_value,
                        data2=velocity_value,
                    )
                    note_off = MidiLiveEvent(
                        sort_index=now + duration,
                        due_time=now + duration,
                        type=NOTE_OFF,
                        channel=channel_zero,
                        data1=note_value,
                        data2=0,
                    )

                    data = event_to_midi_bytes(note_on)
                    if self.midi_transport.send_event(note_on):
                        sent += 1
                        bytes_sent.append([int(x) for x in data])
                    else:
                        failed += 1

                    time.sleep(duration)

                    data = event_to_midi_bytes(note_off)
                    if self.midi_transport.send_event(note_off):
                        sent += 1
                        bytes_sent.append([int(x) for x in data])
                    else:
                        failed += 1

                    if gap > 0.0:
                        time.sleep(gap)

        except Exception as exc:
            self._midi_pump_errors_total += 1
            logger.exception("[MIDI] test sequence error: %s", exc)
            failed += 1
        finally:
            self._midi_direct_test_active = False
            if restore_loop:
                self._midi_test_loop.update(
                    {
                        "active": True,
                        "phase": "program",
                        "next_due": 0.0,
                        "active_note": None,
                    }
                )

        return {
            "ok": failed == 0,
            "midi_mode": self._midi_mode(),
            "paused_test_loop": restore_loop,
            "channel": channel_human,
            "channel_zero_based": channel_zero,
            "notes": note_values,
            "velocity": velocity_value,
            "note_duration_sec": duration,
            "gap_sec": gap,
            "repeat": repeat_count,
            "program": None if program is None else max(0, min(127, int(program))),
            "sent_events": sent,
            "failed_events": failed,
            "bytes": bytes_sent,
            "transport": self.midi_transport.get_status(),
        }

    def stop(self):
        """Hook explícito de parada: evita notas colgadas si MIDI físico está activo."""
        self.send_panic()

    def loop(self):
        """Alias semántico para App.run(user_loop=...)."""
        self.step()

    def get_latest_snapshot(self) -> dict:
        """Devuelve el último snapshot de forma thread-safe."""
        with self._snapshot_lock:
            return dict(self._latest_snapshot)


def create_backend_service() -> BackendService:
    clear_runtime_state()
    return BackendService()
