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


class EegBlockPayloadError(ValueError):
    pass


def eeg_block_value_count(sample_count: int, num_ch: int = NUM_CH) -> int:
    return int(sample_count) * (1 + int(num_ch))


def is_valid_ads1299_status(status: int) -> bool:
    return (int(status) & STATUS_MASK) == STATUS_PREFIX


def parse_eeg_block_values(
    sample_count: int,
    vals,
    *,
    num_ch: int = NUM_CH,
    max_samples: int = BLOCK_SAMPLES,
) -> tuple[tuple[int, ...], tuple[tuple[int, ...], ...]]:
    sample_count = int(sample_count)
    num_ch = int(num_ch)
    max_samples = int(max_samples)

    if sample_count <= 0 or sample_count > max_samples:
        raise EegBlockPayloadError("invalid sample_count")
    if num_ch <= 0:
        raise EegBlockPayloadError("invalid num_ch")

    try:
        vals_tuple = tuple(int(v) for v in vals)
    except Exception as exc:
        raise EegBlockPayloadError("non-integer eeg_block_uV payload value") from exc
    expected_vals = eeg_block_value_count(sample_count, num_ch)
    if len(vals_tuple) != expected_vals:
        raise EegBlockPayloadError("invalid eeg_block_uV payload length")

    statuses: list[int] = []
    samples: list[tuple[int, ...]] = []
    stride = 1 + num_ch
    for i in range(sample_count):
        base = i * stride
        statuses.append(vals_tuple[base])
        samples.append(tuple(vals_tuple[base + 1: base + 1 + num_ch]))

    return tuple(statuses), tuple(samples)


def iter_eeg_block_samples(
    first_sample_idx: int,
    statuses,
    samples,
    *,
    num_ch: int = NUM_CH,
):
    first_sample_idx = int(first_sample_idx)
    statuses_tuple = tuple(int(s) for s in statuses)
    samples_tuple = tuple(tuple(int(v) for v in sample) for sample in samples)

    if len(statuses_tuple) != len(samples_tuple):
        raise EegBlockPayloadError("statuses/samples length mismatch")

    for sample_in_block, (status, sample) in enumerate(zip(statuses_tuple, samples_tuple)):
        if len(sample) != int(num_ch):
            raise EegBlockPayloadError("invalid channel count in sample")
        yield first_sample_idx + sample_in_block, sample_in_block, status, sample
