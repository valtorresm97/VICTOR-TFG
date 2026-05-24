# 11. Controles faltantes y riesgos

| Control faltante | Subsistema | Motivo | Riesgo si falta | Prioridad |
| --- | --- | --- | --- | --- |
| `BENCH_REPORT_ENABLED` separado | Firmware | `BENCH_NOTIFY_ENABLED` no debe controlar prints. | No se puede apagar Monitor bench sin tocar codigo. | Alta |
| Contador explicito de DRDY overruns/frame drops | Firmware | `pending > 1` solo incrementa lag generico. | Perdidas no cuantificadas claramente. | Alta |
| Modo raw/unfiltered diagnostico | Firmware/Python | Separar adquisicion real de filtros MCU. | Filtros pueden ocultar problemas ADS/electrodos. | Alta |
| Watchdog de adquisicion | Firmware/Python | Detectar ausencia prolongada de DRDY/bloques. | UI puede quedar esperando sin causa clara. | Media |
| Estado ADS mode visible en snapshot/UI | Firmware/Python/UI | Saber si modo 5, test, shorted, normal. | Capturas mal interpretadas. | Alta |
| Estado BIAS/RLD visible en UI | Firmware/Python/UI | Modo 5 depende de conexion fisica. | Usuario no sabe configuracion analogica activa. | Alta |
| Boton/endpoint MIDI panic | MIDI/UI | Panic existe en Python pero no expuesto. | Notas colgadas en prueba fisica. | Alta |
| Panic firmware autonomo | Firmware MIDI | Cortar notas aunque Python falle. | Si Bridge/app se cae, notas pueden quedar activas. | Media |
| Confirmacion de handler MIDI | Python/Firmware | `midi_bytes` puede devolver false. | Activacion parcial genera fallos confusos. | Media |
| Control de cola Bridge EEG vs MIDI/LED | Bridge | Tres flujos comparten canal. | Latencia/drops al activar MIDI/LED. | Alta |
| Fallback LED claro | LED/UI | Transporte guarda `last_error`, UI no lo muestra. | Fallos LED invisibles. | Media |
| Boton clear LED | LED/UI | Limpiar matriz fisica. | Frame residual si app para. | Baja/Media |
| Limitador global de notas/segundo | Sonificacion/MIDI | Generacion depende de compas/slots. | Saturacion MIDI si parametros cambian. | Media |
| Congelar musica con quality mala y cortar notas pendientes | Sonificacion/MIDI | Gate evita nuevos compases, pero eventos ya programados siguen. | Artefacto puede seguir sonando brevemente. | Media |
| Logs persistentes de errores | Backend | Errores solo logger/snapshot. | Diagnostico post-prueba dificil. | Baja |
| Control de saturacion UI con umbral visible | UI/DSP | Se calcula `saturation_fraction`. | Usuario no sabe que umbral aplica. | Baja |
| Tests de contrato firmware/Python | Streaming | Payload manual grande. | Refactor rompe parseo. | Alta |
| Tests unitarios DSP/sonificacion | DSP/MIDI | Hay pocas pruebas automatizadas. | Refactor de formulas cambia comportamiento. | Alta |
| Compilacion firmware automatizada | Firmware | No verificada en este entorno. | Cambios futuros pueden romper build. | Alta |
| Configuracion centralizada | Todo | Flags dispersos en macros/env/constantes. | Refactor riesgoso. | Media |
| Etiquetado CH1-only en UI | UI | Modo 5 apaga CH2-CH4. | Usuario interpreta canales no usados. | Media |
| Control de latencia end-to-end | Bridge/MIDI/LED | No se mide EEG->nota->MIDI/LED. | Dificil optimizar live. | Media |
