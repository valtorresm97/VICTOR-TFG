# MIDI OUT inverted TX validation

Relevant final branches: `firmware-final-v3` and `codex/direct-band-sonification`.

## Confirmed result

The Behringer PRO VS MINI sounded correctly after enabling inverted TX on
`Serial1` / D1. This confirms that the Python MIDI messages, Bridge handler,
MCU byte transport, and MIDI message format were valid. The missing piece was
the electrical polarity expected by the MIDI OUT circuit.

## Final firmware decision

The physical MIDI output uses:

```text
UNO Q MCU -> Serial1 / D1 / USART1_TX -> N-audio MIDI OUT circuit -> DIN5
```

The N-audio transistor MIDI OUT circuit used by this PCB expects the
microcontroller signal to be inverted before the transistor stage. Therefore
TX inversion is mandatory in firmware:

```cpp
Serial1.begin(31250, SERIAL_8N1);
USART1->CR2 |= USART_CR2_TXINV;
Serial1.write(byte);
```

`Serial` remains reserved for Monitor/App Lab diagnostics and must not be used
for MIDI bytes.

## Runtime policy

- MIDI UART is enabled by default on `Serial1`.
- TX inversion is required; if `USART1` or `USART_CR2_TXINV` is unavailable,
  the firmware build fails instead of silently transmitting with wrong polarity.
- The MCU self-test arpeggio is available as a compile-time diagnostic but is
  disabled by default.
- Python MIDI live output is enabled by default again.
- The Python diagnostic MIDI loop does not autostart by default, so it will not
  mask EEG sonification.
- The WebUI panic button and MIDI test endpoints use the same `midi_bytes`
  Bridge path as live sonification.

## Validated MIDI bytes

For channel 10, the diagnostic sequence uses standard MIDI 1.0 channel voice
messages:

```text
B9 07 7F   CC7 volume 127
B9 0B 7F   CC11 expression 127
B9 40 00   sustain off
C9 09      program visible 10
99 3C 64   note on C4, velocity 100
89 3C 00   note off C4
```

No MIDI clock, PPQ, file header, or extra synchronization is required for
immediate `note_on` / `note_off` playback on the synthesizer.
