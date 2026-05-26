from __future__ import annotations

"""
Constantes del contrato EEG MCU -> Python.

El firmware sigue siendo la fuente de verdad del payload que emite por Bridge.
Este modulo evita repetir a mano los mismos valores en backend, receiver,
capturas y tools offline.
"""

EEG_BLOCK_EVENT = "eeg_block_uV"

FS_HZ = 250
NUM_CH = 4
BLOCK_SAMPLES = 8

ADS1299_FRAME_BYTES = 3 + 3 * NUM_CH
STATUS_PREFIX = 0xC00000
STATUS_MASK = 0xF00000
LSB_V = 2.235e-8
PGA_GAIN = 24

EEG_BLOCK_HEADER_FIELDS = 3
EEG_BLOCK_FIELDS_PER_SAMPLE = 1 + NUM_CH
EEG_BLOCK_FULL_PAYLOAD_FIELDS = EEG_BLOCK_HEADER_FIELDS + BLOCK_SAMPLES * EEG_BLOCK_FIELDS_PER_SAMPLE

