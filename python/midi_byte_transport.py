# midi_byte_transport.py
# ------------------------------------------------------------
# Transporte Python -> MCU para MIDI live.
#
# Responsabilidad:
#   - Recibir MidiLiveEvent desde midi_live.py.
#   - Convertirlo a bytes MIDI reales.
#   - Enviar esos bytes al MCU mediante Bridge.call(...).
#
# Arquitectura:
#   Python controla:
#       - generación musical,
#       - note_on/note_off,
#       - program_change,
#       - control_change,
#       - formación de bytes MIDI.
#
#   MCU controla:
#       - recibir los bytes,
#       - escribirlos por UART MIDI hacia D1/TX,
#       - usar 31250 baudios si es MIDI DIN tradicional.
#
# Protocolo Bridge propuesto:
#   Bridge.call("midi_bytes", n, b0, b1, b2)
#
# Donde:
#   n  = número de bytes válidos: 2 o 3
#   b0 = status byte
#   b1 = data byte 1
#   b2 = data byte 2, o 0 si n == 2
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Iterable

from arduino.app_utils import Bridge

from midi_live import MidiLiveEvent, event_to_midi_bytes

logger = logging.getLogger("MIDI_TRANSPORT")


class MidiByteTransport:
    """
    Transporte de eventos MIDI live desde Python hacia el MCU.

    Este bloque NO genera música.
    Este bloque NO schedulea notas.
    Este bloque NO accede directamente a D1/TX.

    Solo hace:
        MidiLiveEvent -> bytes MIDI -> Bridge.call("midi_bytes", ...)
    """

    def __init__(
        self,
        bridge_method: str = "midi_bytes",
        enabled: bool = False,
        log_first_events: int = 8,
    ) -> None:
        """
        Args:
            bridge_method:
                Nombre del handler expuesto por el sketch Arduino.

            enabled:
                Si False, no envía nada al MCU.
                Recomendado False hasta que el sketch tenga midi_bytes.

            log_first_events:
                Número de eventos iniciales que se imprimen para depuración.
        """
        self.bridge_method = str(bridge_method)
        self.enabled = bool(enabled)

        self.sent_events_total = 0
        self.failed_events_total = 0
        self.bridge_rejected_events_total = 0
        self.sent_bytes_total = 0
        self.dropped_events_total = 0

        self._log_first_events = int(log_first_events)

    @staticmethod
    def _bridge_call_succeeded(result) -> bool:
        """
        Interpreta el retorno de Bridge.call sin acoplarse a una version concreta
        de App Lab. Algunas versiones devuelven el valor del handler y otras no
        exponen resultado util desde Python.
        """
        if result is None:
            return True
        if isinstance(result, bool):
            return result
        if isinstance(result, tuple) and result:
            first = result[0]
            if isinstance(first, bool):
                return first
        return True

    def set_enabled(self, enabled: bool) -> None:
        """Activa o desactiva el envío físico al MCU."""
        self.enabled = bool(enabled)

    def send_event(self, event: MidiLiveEvent) -> bool:
        """
        Envía un único evento MIDI al MCU.

        Devuelve:
            True si se envió correctamente.
            False si está desactivado o si falló.
        """
        if not self.enabled:
            self.dropped_events_total += 1
            return False

        try:
            data = event_to_midi_bytes(event)
            n = len(data)

            b0 = int(data[0]) if n > 0 else 0
            b1 = int(data[1]) if n > 1 else 0
            b2 = int(data[2]) if n > 2 else 0

            # Handler esperado en el sketch:
            #   midi_bytes(n, b0, b1, b2)
            result = Bridge.call(
                self.bridge_method,
                int(n),
                int(b0),
                int(b1),
                int(b2),
            )

            if not self._bridge_call_succeeded(result):
                self.failed_events_total += 1
                self.bridge_rejected_events_total += 1
                if self.bridge_rejected_events_total <= self._log_first_events:
                    logger.warning(
                        "[MIDI] bridge handler rejected type=%s bytes=%s result=%r",
                        event.type,
                        [int(x) for x in data],
                        result,
                    )
                return False

            self.sent_events_total += 1
            self.sent_bytes_total += n

            if self.sent_events_total <= self._log_first_events:
                logger.info(
                    "[MIDI] sent type=%s bytes=%s",
                    event.type,
                    [int(x) for x in data],
                )

            return True

        except Exception as exc:
            self.failed_events_total += 1
            logger.exception("[MIDI] send_event failed: %s", exc)
            return False

    def send_events(self, events: Iterable[MidiLiveEvent]) -> int:
        """
        Envía varios eventos.

        Returns:
            Número de eventos enviados correctamente.
        """
        ok = 0

        for event in events:
            if self.send_event(event):
                ok += 1

        return ok

    def get_status(self) -> dict:
        """Estado ligero para snapshot/debug."""
        return {
            "enabled": self.enabled,
            "bridge_method": self.bridge_method,
            "sent_events_total": self.sent_events_total,
            "failed_events_total": self.failed_events_total,
            "bridge_rejected_events_total": self.bridge_rejected_events_total,
            "sent_bytes_total": self.sent_bytes_total,
            "dropped_events_total": self.dropped_events_total,
        }
