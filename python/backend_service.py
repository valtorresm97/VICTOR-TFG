from __future__ import annotations

import logging
import threading
import time

from arduino.app_utils import Bridge

from eeg_signal_processor import EEGSignalProcessor
from receiver import EEGReceiver
from app_state import publish_snapshot, clear_runtime_state
from sonification_features import (
    SonificationFeatureAdapter,
    build_sonification_snapshot,
)

from sonification_features import (
    SonificationFeatureAdapter,
    build_sonification_snapshot,
)

from scale_registry import build_scale_config
from music_utils import note_name_to_midi
from music_segment import MusicSegmentBuilder
from music_bar import BarGenerator
from music_note import NoteGenerator
from midi_live import MidiScheduler
from midi_byte_transport import MidiByteTransport


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EEG_BACKEND")


# ------------------------------------------------------------
# Configuración EEG / DSP
# ------------------------------------------------------------

FS_HZ = 250
NUM_CH = 4

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

MUSIC_CHANNEL = 0
MUSIC_PROGRAM = 0

MUSIC_ROOT_NOTE = "C4"
MUSIC_MAIN_NOTE = "G4"

MUSIC_SCALE_FAMILY = "Diatonic"
MUSIC_SCALE_NAME = "Major (Ionian)"

# Importante:
# - Déjalo en False hasta que el sketch Arduino exponga "midi_bytes".
# - Ponlo True cuando el MCU ya pueda recibir bytes y sacarlos por D1/TX.
MIDI_LIVE_ENABLED = False

MIDI_BRIDGE_METHOD = "midi_bytes"
MIDI_LOOKAHEAD_SEC = 0.02
MIDI_GENERATE_PERIOD_SEC = MUSIC_BAR_SEC


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

        Bridge.provide("linux_started", self.rx.linux_started)
        logger.info("[BRIDGE] registered linux_started")

        Bridge.provide("eeg_block_uV", self.rx.eeg_block_uV)
        logger.info("[BRIDGE] registered eeg_block_uV")

        # ----------------------------------------------------
        # Estado DSP / sonificación
        # ----------------------------------------------------
        self._last_features: dict = {}

        self.sonif_adapter = SonificationFeatureAdapter()
        self._last_sonification = None

        self.sonif_adapter = SonificationFeatureAdapter()
        self._last_sonification = None
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

        self._last_music_t = 0.0
        self._program_change_sent = False

        self._last_notes_count = 0
        self._last_midi_due_count = 0
        self._last_midi_sent_count = 0

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

    def _build_snapshot(self) -> dict:
        """Construye el snapshot público consumido por WebUI/disco."""
        rxm = self.rx.get_window_metrics(reset=False)

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
            "ts_monotonic": time.monotonic(),
            "config": {
                "fs_hz": FS_HZ,
                "num_ch": NUM_CH,
                "feature_window_sec": FEATURE_WINDOW_SEC,
                "feature_hop_samples": FEATURE_HOP_SAMPLES,
                "psd_method": "multitaper",
                "channel_idx": 0,
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
                "last_notes_count": self._last_notes_count,
                "generation_errors_total": self._music_generation_errors_total,
            },
            "midi": {
                "scheduler": self.midi_scheduler.get_status(),
                "transport": self.midi_transport.get_status(),
                "last_due_events": self._last_midi_due_count,
                "last_sent_events": self._last_midi_sent_count,
                "pump_errors_total": self._midi_pump_errors_total,
                "live_enabled": MIDI_LIVE_ENABLED,
                "lookahead_sec": MIDI_LOOKAHEAD_SEC,
            },
            "sonification": build_sonification_snapshot(self._last_sonification),
        }

    # --------------------------------------------------------
    # Generación musical live
    # --------------------------------------------------------

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
        _, drained_frames = self.rx.drain_blocks_to_processor(
            self.proc,
            max_blocks=16,
        )

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
                    self._last_sonification = self.sonif_adapter.update(
                        self._last_features
                    )

                    self._last_sonification = self.sonif_adapter.update(self._last_features)
                    if not self._logged_features_ready:
                        logger.info("[DSP] features ready")
                        self._logged_features_ready = True

            except Exception as e:
                logger.exception("feature computation error: %s", e)

        now = time.monotonic()

        # Música y MIDI se ejecutan en cada step, pero solo generan
        # compás nuevo cuando ha pasado MUSIC_GENERATE_PERIOD_SEC.
        self._maybe_generate_music(now=now)
        self._pump_midi(now=now)

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
