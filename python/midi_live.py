"""
midi_live.py
------------

Bloque 4 - MIDI LIVE / Scheduler

Convierte NoteEvent en eventos MIDI de tiempo real.

Este módulo NO escribe archivos .mid.
Este módulo NO usa mido.
Este módulo NO accede todavía al pin D1/TX.

Su responsabilidad es:
  - recibir NoteEvent desde music_note.py,
  - crear eventos note_on / note_off,
  - ordenarlos por tiempo,
  - entregarlos cuando toca,
  - generar panic / all_notes_off.

Más adelante, otro transporte enviará estos eventos:
  Python -> MCU -> UART MIDI 31250 baudios -> D1/TX -> MIDI OUT PCB
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, List, Optional
import heapq
import time

from music_note import NoteEvent


# ------------------------------------------------------------
# Tipos MIDI soportados
# ------------------------------------------------------------

NOTE_ON = "note_on"
NOTE_OFF = "note_off"
PROGRAM_CHANGE = "program_change"
CONTROL_CHANGE = "control_change"


# ------------------------------------------------------------
# Evento MIDI live
# ------------------------------------------------------------

@dataclass(order=True)
class MidiLiveEvent:
    """
    Evento MIDI programado.

    sort_index:
        Campo interno para heapq.
        Es igual a due_time.

    due_time:
        Tiempo absoluto monotónico en segundos.

    type:
        note_on, note_off, program_change, control_change.

    channel:
        Canal MIDI 0..15.

    data1:
        Nota, programa o CC number.

    data2:
        Velocity o CC value.
        En program_change no se usa.
    """

    sort_index: float
    due_time: float
    type: str
    channel: int
    data1: int
    data2: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convierte a dict para debug, snapshot o transporte."""
        out = asdict(self)
        out.pop("sort_index", None)
        return out


# ------------------------------------------------------------
# Helpers MIDI
# ------------------------------------------------------------

def _clamp_int(value: int, lo: int, hi: int) -> int:
    """Limita enteros a un rango seguro."""
    return max(lo, min(hi, int(value)))


def _channel(ch: int) -> int:
    """Canal MIDI seguro 0..15."""
    return _clamp_int(ch, 0, 15)


def _data7(value: int) -> int:
    """Dato MIDI seguro 0..127."""
    return _clamp_int(value, 0, 127)


def _event(
    due_time: float,
    event_type: str,
    channel: int,
    data1: int,
    data2: int = 0,
) -> MidiLiveEvent:
    """Crea un evento MIDI validado."""
    due = float(due_time)
    return MidiLiveEvent(
        sort_index=due,
        due_time=due,
        type=str(event_type),
        channel=_channel(channel),
        data1=_data7(data1),
        data2=_data7(data2),
    )


# ------------------------------------------------------------
# Conversión NoteEvent -> eventos MIDI live
# ------------------------------------------------------------

def note_to_live_events(
    note: NoteEvent,
    time_origin: float,
    now: Optional[float] = None,
) -> list[MidiLiveEvent]:
    """
    Convierte un NoteEvent en:
      - note_on
      - note_off

    NoteEvent usa tiempos musicales relativos/absolutos en segundos.
    time_origin permite traducirlos al reloj monotónico real.
    """
    if now is None:
        now = time.monotonic()

    start = float(time_origin) + max(0.0, float(note.t_start))
    end = float(time_origin) + max(0.0, float(note.t_end))

    # Seguridad: toda nota debe tener duración mínima.
    if end <= start:
        end = start + 0.03

    # Si el evento llega tarde, se dispara inmediatamente.
    start = max(float(now), start)
    end = max(start + 0.03, end)

    return [
        _event(
            due_time=start,
            event_type=NOTE_ON,
            channel=note.channel,
            data1=note.pitch_midi,
            data2=note.velocity,
        ),
        _event(
            due_time=end,
            event_type=NOTE_OFF,
            channel=note.channel,
            data1=note.pitch_midi,
            data2=0,
        ),
    ]


def notes_to_live_events(
    notes: list[NoteEvent],
    time_origin: float,
    now: Optional[float] = None,
) -> list[MidiLiveEvent]:
    """Convierte una lista de NoteEvent en eventos MIDI live ordenados."""
    events: list[MidiLiveEvent] = []

    for note in notes:
        events.extend(
            note_to_live_events(
                note=note,
                time_origin=time_origin,
                now=now,
            )
        )

    # Si coinciden en tiempo, note_off antes que note_on.
    priority = {NOTE_OFF: 0, NOTE_ON: 1, CONTROL_CHANGE: 2, PROGRAM_CHANGE: 3}
    events.sort(key=lambda e: (e.due_time, priority.get(e.type, 9)))

    return events


def program_change_event(
    program: int,
    channel: int = 0,
    due_time: Optional[float] = None,
) -> MidiLiveEvent:
    """Crea evento program_change."""
    if due_time is None:
        due_time = time.monotonic()

    return _event(
        due_time=due_time,
        event_type=PROGRAM_CHANGE,
        channel=channel,
        data1=program,
        data2=0,
    )


def control_change_event(
    cc: int,
    value: int,
    channel: int = 0,
    due_time: Optional[float] = None,
) -> MidiLiveEvent:
    """Crea evento control_change."""
    if due_time is None:
        due_time = time.monotonic()

    return _event(
        due_time=due_time,
        event_type=CONTROL_CHANGE,
        channel=channel,
        data1=cc,
        data2=value,
    )


def all_notes_off_events(
    due_time: Optional[float] = None,
    channels: range = range(16),
) -> list[MidiLiveEvent]:
    """
    Genera CC 123 All Notes Off para todos los canales.

    CC 123:
      channel, controller=123, value=0
    """
    if due_time is None:
        due_time = time.monotonic()

    return [
        control_change_event(
            cc=123,
            value=0,
            channel=ch,
            due_time=due_time,
        )
        for ch in channels
    ]


def panic_events(
    due_time: Optional[float] = None,
    channels: range = range(16),
) -> list[MidiLiveEvent]:
    """
    Genera mensajes de seguridad.

    CC 120 = All Sound Off.
    CC 123 = All Notes Off.
    """
    if due_time is None:
        due_time = time.monotonic()

    events: list[MidiLiveEvent] = []

    for ch in channels:
        events.append(control_change_event(120, 0, ch, due_time))
        events.append(control_change_event(123, 0, ch, due_time))

    return events


# ------------------------------------------------------------
# Scheduler MIDI live
# ------------------------------------------------------------

class MidiScheduler:
    """
    Scheduler simple para eventos MIDI live.

    Uso típico:
      scheduler = MidiScheduler()
      scheduler.schedule_notes(notes, time_origin=time.monotonic())
      due = scheduler.pop_due_events()
      transport.send_many(due)

    El scheduler no envía nada por sí mismo.
    Solo decide qué eventos ya deben salir.
    """

    def __init__(self, max_queue: int = 2048) -> None:
        self.max_queue = int(max_queue)
        self._heap: list[MidiLiveEvent] = []
        self._active_notes: set[tuple[int, int]] = set()

    def clear(self) -> None:
        """Vacía la cola sin generar mensajes."""
        self._heap.clear()
        self._active_notes.clear()

    def schedule_event(self, event: MidiLiveEvent) -> None:
        """Añade un evento a la cola."""
        if len(self._heap) >= self.max_queue:
            # En saturación, se descarta el evento más lejano.
            self._heap.sort(key=lambda e: e.due_time)
            self._heap.pop()

        heapq.heappush(self._heap, event)

    def schedule_events(self, events: list[MidiLiveEvent]) -> None:
        """Añade varios eventos."""
        for ev in events:
            self.schedule_event(ev)

    def schedule_notes(
        self,
        notes: list[NoteEvent],
        time_origin: Optional[float] = None,
    ) -> None:
        """Convierte NoteEvent a MIDI live y los mete en cola."""
        if time_origin is None:
            time_origin = time.monotonic()

        events = notes_to_live_events(
            notes=notes,
            time_origin=time_origin,
            now=time.monotonic(),
        )
        self.schedule_events(events)

    def schedule_program_change(
        self,
        program: int,
        channel: int = 0,
        due_time: Optional[float] = None,
    ) -> None:
        """Programa cambio de instrumento."""
        self.schedule_event(
            program_change_event(
                program=program,
                channel=channel,
                due_time=due_time,
            )
        )

    def panic(self) -> list[MidiLiveEvent]:
        """
        Limpia la cola y devuelve eventos panic inmediatos.

        El backend/transporte debe enviarlos inmediatamente.
        """
        self.clear()
        return panic_events()

    def pop_due_events(
        self,
        now: Optional[float] = None,
        lookahead_sec: float = 0.0,
        max_events: int = 128,
    ) -> list[MidiLiveEvent]:
        """
        Extrae eventos cuyo due_time ya llegó.

        lookahead_sec:
            Permite adelantar un poco la entrega para que el transporte
            o MCU puedan temporizar con margen.
        """
        if now is None:
            now = time.monotonic()

        deadline = float(now) + max(0.0, float(lookahead_sec))
        out: list[MidiLiveEvent] = []

        while self._heap and len(out) < max_events:
            if self._heap[0].due_time > deadline:
                break

            ev = heapq.heappop(self._heap)
            self._track_active_note(ev)
            out.append(ev)

        return out

    def _track_active_note(self, ev: MidiLiveEvent) -> None:
        """Mantiene estado aproximado de notas activas."""
        key = (ev.channel, ev.data1)

        if ev.type == NOTE_ON and ev.data2 > 0:
            self._active_notes.add(key)

        elif ev.type == NOTE_OFF:
            self._active_notes.discard(key)

        elif ev.type == CONTROL_CHANGE and ev.data1 in (120, 123):
            if ev.channel in range(16):
                self._active_notes = {
                    k for k in self._active_notes if k[0] != ev.channel
                }

    def active_notes_count(self) -> int:
        """Número aproximado de notas activas."""
        return len(self._active_notes)

    def queued_events_count(self) -> int:
        """Número de eventos pendientes."""
        return len(self._heap)

    def get_status(self) -> dict[str, int]:
        """Estado ligero para snapshot/debug."""
        return {
            "queued_events": self.queued_events_count(),
            "active_notes": self.active_notes_count(),
        }


# ------------------------------------------------------------
# Conversión futura a bytes MIDI
# ------------------------------------------------------------

def event_to_midi_bytes(event: MidiLiveEvent) -> bytes:
    """
    Convierte un MidiLiveEvent a bytes MIDI estándar.

    Esto será útil para el transporte MCU/D1.

    Nota:
      - No lo usamos todavía para enviar por D1.
      - Sirve como formato claro y testeable.
    """
    ch = _channel(event.channel)

    if event.type == NOTE_ON:
        return bytes([0x90 | ch, _data7(event.data1), _data7(event.data2)])

    if event.type == NOTE_OFF:
        return bytes([0x80 | ch, _data7(event.data1), _data7(event.data2)])

    if event.type == CONTROL_CHANGE:
        return bytes([0xB0 | ch, _data7(event.data1), _data7(event.data2)])

    if event.type == PROGRAM_CHANGE:
        return bytes([0xC0 | ch, _data7(event.data1)])

    raise ValueError(f"Tipo MIDI no soportado: {event.type}")


# ------------------------------------------------------------
# Prueba rápida local
# ------------------------------------------------------------

if __name__ == "__main__":
    now = time.monotonic()

    notes = [
        NoteEvent(
            t_start=0.0,
            t_end=0.5,
            pitch_midi=60,
            velocity=100,
            channel=0,
            program=0,
        ),
        NoteEvent(
            t_start=0.5,
            t_end=1.0,
            pitch_midi=64,
            velocity=90,
            channel=0,
            program=0,
        ),
    ]

    scheduler = MidiScheduler()
    scheduler.schedule_program_change(program=0, channel=0, due_time=now)
    scheduler.schedule_notes(notes, time_origin=now)

    print("Estado inicial:", scheduler.get_status())

    due = scheduler.pop_due_events(now=now, lookahead_sec=0.01)
    for ev in due:
        print(ev.to_dict(), list(event_to_midi_bytes(ev)))

    print("Estado final:", scheduler.get_status())
