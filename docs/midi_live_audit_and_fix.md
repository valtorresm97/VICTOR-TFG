# MIDI live audit and build fix

## Scope

Audited the live MIDI path without changing ADS1299 acquisition, DRDY, SPI,
filters, DSP, `eeg_block_uV`, or the EEG Bridge contract.

## End-to-end flow

```text
SonificationFeatures
   -> MusicSegmentBuilder
   -> BarGenerator
   -> NoteGenerator
   -> NoteEvent
   -> MidiScheduler
   -> MidiLiveEvent
   -> event_to_midi_bytes()
   -> MidiByteTransport
   -> Bridge.call("midi_bytes", n, b0, b1, b2)
   -> MCU midi_bytes()
   -> UART TX/D1 if MIDI UART is enabled and configured
   -> MIDI OUT PCB
```

## Python modules

| File | Role | Input | Output | Default state |
| --- | --- | --- | --- | --- |
| `sonification_features.py` | Converts DSP features and quality gate into stable musical controls. | `EEGSignalProcessor.compute_live_features()` dict. | `SonificationFeatures`. | Active. |
| `music_segment.py` | Converts sonification controls into one live musical window. | `SonificationFeatures`, scale, main note. | `MusicSegment`. | Active. |
| `music_bar.py` | Chooses chord, note slots and musical envelope. | `MusicSegment`. | `Bar`. | Active. |
| `music_note.py` | Converts a bar into high-level notes. | `MusicSegment`, `Bar`, channel, program. | `NoteEvent` list. | Active. |
| `midi_live.py` | Schedules live MIDI events and converts them to bytes. | `NoteEvent` list or program/CC/panic request. | `MidiLiveEvent` and MIDI bytes. | Active. |
| `midi_byte_transport.py` | Sends MIDI bytes to the MCU handler. | `MidiLiveEvent`. | `Bridge.call("midi_bytes", n,b0,b1,b2)`. | Disabled by default. |
| `backend_service.py` | Orchestrates EEG, DSP, sonification, music, scheduler, MIDI pump and snapshots. | Receiver/DSP state. | Web snapshots and optional MIDI Bridge calls. | MIDI live disabled by `EEG_MIDI_LIVE_ENABLED` default. |
| `web_server.py` | Exposes dashboard routes and MIDI panic. | HTTP `POST /midi/panic`. | Calls `BackendService.send_panic()`. | Active, panic sends only if transport enabled. |
| `assets/app.js` | Renders MIDI status, piano roll and panic button. | Snapshot `music.*` and `midi.*`. | UI only. | Active; no acquisition/DSP logic. |

## MIDI byte contract

`midi_live.py::event_to_midi_bytes()` emits standard short MIDI messages:

| Event | Status byte | Data bytes | Length |
| --- | --- | --- | --- |
| `note_on` | `0x90 | channel` | pitch, velocity | 3 |
| `note_off` | `0x80 | channel` | pitch, velocity | 3 |
| `control_change` | `0xB0 | channel` | controller, value | 3 |
| `program_change` | `0xC0 | channel` | program | 2 |

Channels are clamped to `0..15`; pitch, velocity, controller, value and
program are clamped to `0..127`.

Safety messages:

- `all_notes_off_events()` sends CC 123 value 0 for channels 0..15.
- `panic_events()` sends CC 120 value 0 and CC 123 value 0 for channels 0..15.

`python/tools/test_midi_bytes.py` validates this contract without hardware.

## Transport behavior

`MidiByteTransport` is controlled by `EEG_MIDI_LIVE_ENABLED`. In branch
`midi-config`, the Python transport defaults to enabled for the physical MIDI
test. Set `EEG_MIDI_LIVE_ENABLED=0` to return to dry-run mode.

- If disabled, `send_event()` does not call Bridge and increments
  `dropped_events_total`.
- If enabled, it converts the event to bytes and calls
  `Bridge.call("midi_bytes", n, b0, b1, b2)`.
- Exceptions from Bridge increment `failed_events_total`.
- Successful Bridge calls increment `sent_events_total` and `sent_bytes_total`.

Important residual risk: the current transport does not inspect a boolean
return value from the MCU handler, so an MCU dry-run handler can look like a
successful Python-side call if Bridge itself does not raise.

## MCU handler

`sketch/sketch.ino::midi_bytes(int n, int b0, int b1, int b2)` accepts short
MIDI messages with `n` in `1..3`. It masks each byte to `uint8_t`.

- With `MIDI_UART_CONFIGURED=1`, it writes the first `n` bytes to
  `MIDI_SERIAL` and returns `true`.
- With `MIDI_UART_CONFIGURED=0`, it does not write UART and returns `false`.

`MIDI_UART_CONFIGURED` is derived from:

```cpp
#ifndef MIDI_UART_ENABLED
#define MIDI_UART_ENABLED 0
#endif

#if (MIDI_UART_ENABLED != 0)
#ifndef MIDI_SERIAL
#error "Define MIDI_SERIAL as the hardware UART verified for D1/TX MIDI OUT."
#endif
#define MIDI_UART_CONFIGURED 1
#else
#define MIDI_UART_CONFIGURED 0
#endif
```

In branch `midi-config`, the firmware defaults to `MIDI_UART_ENABLED=1` and
`MIDI_SERIAL=Serial` for the D1/TX test. Set `MIDI_UART_ENABLED=0` to return to
dry-run mode. The guard still only requires a serial object when physical UART
output is enabled.

## Build failures fixed

### `Arduino_LED_Matrix@latest` not found

Cause: `sketch/sketch.yaml` listed `Arduino_LED_Matrix` as a required library
even though `LED_MATRIX_ENABLED=0` by default and the firmware include is guarded.

Fix: removed `Arduino_LED_Matrix` from the default library list. The
`led_matrix_frame` handler remains compiled as dry-run when `LED_MATRIX_ENABLED=0`.
If physical LED matrix support is enabled later, add the correct UNO Q compatible
library/dependency back deliberately.

### `Define MIDI_SERIAL...`

Cause: `MIDI_SERIAL` must not be required while MIDI UART is disabled. The sketch
now uses the derived `MIDI_UART_CONFIGURED` macro for all UART writes and init.
In branch `midi-config`, `MIDI_SERIAL` is temporarily defined as `Serial` and
`MIDI_UART_ENABLED` defaults to `1`. If this interferes with Bridge/Monitor or
does not drive D1/TX, set `MIDI_UART_ENABLED=0` again and test the correct
serial object separately.

## Future activation of physical MIDI

Before enabling, verify the Arduino object that maps to UNO Q `D1/TX`.
Arduino documentation confirms `D1/TX` is `PB6 / UART TX`, but the firmware
must still avoid stealing any serial object used by App Lab Bridge.

Relevant Arduino references checked on 2026-05-26:

- UNO Q user manual / pinout: `D1/TX` is `PB6 / UART TX`.
  https://docs.arduino.cc/tutorials/uno-q/user-manual/
- UNO Q Zephyr 0.55 migration note: hardware UART pins 0/1 use `Serial1`
  after the migration.
  https://support.arduino.cc/hc/en-us/articles/27251870677916-Migrating-to-Zephyr-core-0-55-0-on-UNO-Q
- Bridge API reference: Bridge infrastructure reserves `/dev/ttyHS1` and
  `Serial1`; application code must not open them.
  https://docs.arduino.cc/software/app-lab/bridge/bridge-api/

Because this project depends on RouterBridge for EEG and MIDI commands, the
safe firmware default is to keep MIDI UART disabled until a direct UNO Q test
confirms which serial object can drive D1/TX without breaking Bridge.

This branch currently builds with:

```cpp
#define MIDI_UART_ENABLED 1
#define MIDI_SERIAL Serial
```

Python live MIDI defaults to enabled in this branch. To force it explicitly:

```bash
EEG_MIDI_LIVE_ENABLED=1
```

The musical channel is currently `MUSIC_CHANNEL = 0` in `backend_service.py`,
which means MIDI channel 1. Use `1..15` for MIDI channels 2..16.

## Pending risks

- No electrical ACK confirms bytes left D1/TX.
- No firmware-side autonomous panic if Python/App Lab dies.
- Bridge EEG, MIDI and LED share communication resources; measure EEG drops and
  MIDI latency before long physical sessions.
- Python transport should eventually inspect MCU handler return values if the
  Bridge API exposes them reliably.
