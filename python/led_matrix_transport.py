from __future__ import annotations

import logging
from typing import Iterable

from arduino.app_utils import Bridge

from midi_live import MidiLiveEvent, NOTE_ON

logger = logging.getLogger("LED_MATRIX_TRANSPORT")


class LedMatrixTransport:
    """
    Transporte ligero Python -> MCU para visualizar note_on en la matriz LED.

    No genera notas ni modifica MIDI. Solo copia los note_on que ya vencen en
    el scheduler y los manda al handler Bridge del sketch:

        Bridge.call("led_note", pitch_midi, velocity)
    """

    def __init__(
        self,
        bridge_method: str = "led_note",
        enabled: bool = True,
        log_first_events: int = 8,
    ) -> None:
        self.bridge_method = str(bridge_method)
        self.enabled = bool(enabled)
        self.sent_events_total = 0
        self.failed_events_total = 0
        self.dropped_events_total = 0
        self._log_first_events = int(log_first_events)

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)

    def send_event(self, event: MidiLiveEvent) -> bool:
        """Envia un note_on al MCU para que aparezca en la matriz LED."""
        if event.type != NOTE_ON or int(event.data2) <= 0:
            return False

        if not self.enabled:
            self.dropped_events_total += 1
            return False

        try:
            pitch = max(0, min(127, int(event.data1)))
            velocity = max(0, min(127, int(event.data2)))

            Bridge.call(self.bridge_method, pitch, velocity)

            self.sent_events_total += 1
            if self.sent_events_total <= self._log_first_events:
                logger.info(
                    "[LED_MATRIX] sent pitch=%d velocity=%d",
                    pitch,
                    velocity,
                )
            return True

        except Exception as exc:
            self.failed_events_total += 1
            logger.exception("[LED_MATRIX] send_event failed: %s", exc)
            return False

    def send_events(self, events: Iterable[MidiLiveEvent]) -> int:
        ok = 0
        for event in events:
            if self.send_event(event):
                ok += 1
        return ok

    def get_status(self) -> dict:
        return {
            "enabled": self.enabled,
            "bridge_method": self.bridge_method,
            "sent_events_total": self.sent_events_total,
            "failed_events_total": self.failed_events_total,
            "dropped_events_total": self.dropped_events_total,
        }
