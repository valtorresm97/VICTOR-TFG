# Auditoria firmware-final-v1

## Objetivo

Crear un punto de partida estable para la fase final del TFG, sin simplificar ni refactorizar codigo. Esta auditoria documenta firmware, ADS1299, Bridge, backend Python, DSP, sonificacion, MIDI live, Web UI, LED matrix, tools, capturas, configuraciones, redundancias, controles faltantes y criticidad.

## Rama

- Rama solicitada como base: `matrix-scroll`.
- Rama base real encontrada: `matrixz-scroll`.
- Nueva rama creada: `firmware-final-v1`.

`matrix-scroll` no existia local ni remota en este checkout. La rama activa `matrixz-scroll` contenia los commits finales de matrix scroll y se uso como base segura.

## Estado del sistema

El sistema integra adquisicion real ADS1299-4PAG a 250 Hz, streaming por bloques de 8 muestras, backend Python con DSP multitaper, quality gate, sonificacion live, scheduler MIDI, piano roll web y soporte de LED matrix desactivado por defecto.

Arquitectura resumida:

```text
ADS1299 RDATAC
→ MCU filtros HP/notch/LP
→ Bridge.notify("eeg_block_uV")
→ receiver.py
→ EEGSignalProcessor/DSPCore
→ spectral_quality
→ SonificationFeatures
→ MusicSegment/Bar/NoteEvent
→ MidiScheduler/MidiByteTransport
→ Web UI piano roll
→ LED matrix frame opcional
```

## Documentos creados

| Documento | Contenido |
| --- | --- |
| `00_inventario_proyecto.md` | Inventario por archivo/familias y capturas. |
| `01_arquitectura_global.md` | Flujos end-to-end real, offline, UI, MIDI y LED. |
| `02_auditoria_firmware_mcu.md` | Firmware, ADS1299, pines, funciones criticas y riesgos. |
| `03_auditoria_python_backend.md` | Backend, receiver, buffer, snapshot, capture manager. |
| `04_auditoria_dsp_features.md` | DSP, multitaper, bandpowers, quality gate y controles. |
| `05_auditoria_sonificacion_midi.md` | Segmentos, barras, notas, scheduler, transporte MIDI. |
| `06_auditoria_led_matrix_scroll.md` | LED matrix 13x8, mapeo, transporte y limites. |
| `07_auditoria_web_ui.md` | WebUI, paneles, claves snapshot y riesgos. |
| `08_auditoria_tools_capturas_docs.md` | Tools CLI, capturas, reports y docs existentes. |
| `09_mapa_configuraciones.md` | Flags/macro/env enabled/disabled. |
| `10_redundancias_y_deuda_tecnica.md` | Duplicaciones y deuda para refactor futuro. |
| `11_controles_faltantes_y_riesgos.md` | Controles que faltan por subsistema. |
| `12_mapa_criticidad_refactor.md` | Que tocar y que no tocar sin pruebas. |

## Riesgos principales antes de simplificar

- Contrato `eeg_block_uV` manual y muy critico.
- Constantes duplicadas entre firmware, backend y tools.
- Activar MIDI/LED puede cargar Bridge si no se mide.
- `BENCH_NOTIFY_ENABLED` mezcla streaming y benchmark.
- Falta `BENCH_REPORT_ENABLED`.
- Falta modo raw/unfiltered para diagnostico.
- CH1-only activo por defecto puede confundirse con 4 canales EEG reales.
- Panic MIDI existe en Python pero no esta expuesto en UI.
- Firmware no se compilo en esta auditoria por ausencia de toolchain verificada.

## Orden recomendado de refactor futuro

1. Congelar tests de contrato `streaming.h` ↔ `receiver.py`.
2. Crear tests Python de DSP, quality, sonificacion, MIDI y LED.
3. Separar flags de streaming/benchmark en firmware.
4. Documentar/mostrar ADS mode y BIAS/RLD en snapshot/UI.
5. Exponer panic MIDI y clear LED antes de pruebas fisicas.
6. Centralizar configuraciones Python y mapa de constantes.
7. Reducir duplicacion offline/live de DSP solo despues de tener golden outputs.
8. Simplificar docs marcando definitivos vs historicos.
