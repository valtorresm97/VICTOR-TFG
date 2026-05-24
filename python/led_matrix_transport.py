from __future__ import annotations

import logging
from typing import Any

from arduino.app_utils import Bridge


logger = logging.getLogger("LED_MATRIX_TRANSPORT")


class LedMatrixTransport:
    """
    Transporte Python -> MCU para la matriz LED.

    La entrada es un frame ya calculado desde recent_notes. Este bloque no
    entiende EEG ni genera musica; solo entrega bytes row-major al handler
    Arduino_LED_Matrix compatible con el ejemplo oficial.
    """

    def __init__(
        self,
        *,
        bridge_method: str = "led_matrix_frame",
        enabled: bool = False,
        width: int = 13,
        height: int = 8,
        log_first_frames: int = 4,
    ) -> None:
        self.bridge_method = str(bridge_method)
        self.enabled = bool(enabled)
        self.width = int(width)
        self.height = int(height)
        self.sent_frames_total = 0
        self.failed_frames_total = 0
        self.dropped_frames_total = 0
        self.sent_bytes_total = 0
        self.last_error = ""
        self.last_point_count = 0
        self._log_first_frames = int(log_first_frames)

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)

    def _frame_to_bytes(self, frame: dict[str, Any]) -> bytes:
        rows = frame.get("rows") if isinstance(frame, dict) else None
        if not isinstance(rows, list) or len(rows) != self.height:
            raise ValueError("LED frame rows have unexpected height")

        out: list[int] = []
        for row in rows:
            if not isinstance(row, list) or len(row) != self.width:
                raise ValueError("LED frame rows have unexpected width")
            out.extend(max(0, min(7, int(v))) for v in row)

        return bytes(out)

    def send_frame(self, frame: dict[str, Any]) -> bool:
        """
        Envia un frame completo a la matriz.

        Si enabled=False, cuenta el frame como dropped para observabilidad y
        evita cualquier llamada Bridge que pueda afectar a adquisicion/MIDI.
        """
        self.last_point_count = int(frame.get("point_count", 0) or 0)

        if not self.enabled:
            self.dropped_frames_total += 1
            return False

        try:
            payload = self._frame_to_bytes(frame)
            Bridge.call(self.bridge_method, payload)
            self.sent_frames_total += 1
            self.sent_bytes_total += len(payload)
            self.last_error = ""

            if self.sent_frames_total <= self._log_first_frames:
                logger.info(
                    "[LED] frame sent bytes=%s points=%s",
                    len(payload),
                    self.last_point_count,
                )

            return True
        except Exception as exc:
            self.failed_frames_total += 1
            self.last_error = str(exc)
            logger.exception("[LED] send_frame failed: %s", exc)
            return False

    def get_status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "bridge_method": self.bridge_method,
            "width": self.width,
            "height": self.height,
            "sent_frames_total": self.sent_frames_total,
            "failed_frames_total": self.failed_frames_total,
            "dropped_frames_total": self.dropped_frames_total,
            "sent_bytes_total": self.sent_bytes_total,
            "last_error": self.last_error,
            "last_point_count": self.last_point_count,
        }
