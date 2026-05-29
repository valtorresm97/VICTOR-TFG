# 11. Controles faltantes y riesgos - final-v4

## 1. Objetivo

Este documento recoge controles que faltaban en fases anteriores, controles ya resueltos en final-v4 y riesgos que siguen abiertos antes de una futura simplificacion/UML.

No todos los controles faltantes deben implementarse. Algunos se dejan fuera de forma deliberada porque aumentarian complejidad, romperian comparabilidad de capturas o expondrÃ­an configuracion peligrosa al usuario.

La auditoria funcion por funcion mas exhaustiva esta en:

```text
docs/01_arquitectura_sistema/09_mapa_contratos_entre_modulos.md
docs/01_arquitectura_sistema/10_mapa_funciones_criticas.md
docs/02_auditoria_codigo/funcion_por_funcion/11_hallazgos_para_simplificacion_futura.md
```

Estado actual de referencia:

```text
Rama integrada: firmware-final-v4
Rama documental: refactor/essential-eeg-midi-plan
```

## 2. Principio de control en final-v4

El sistema final-v4 no busca exponer todos los controles posibles. El criterio correcto es:

```text
exponer controles musicales seguros;
mostrar estado tecnico suficiente;
conservar panic MIDI;
no exponer firmware/ADS/filtros desde WebUI;
conservar tools offline para validacion;
no mezclar diagnostico con flujo principal EEG->MIDI.
```

Por eso, algunos controles que podrian parecer utiles no deben ir a la WebUI esencial:

- cambio de `ADS_DIAGNOSTIC_MODE`;
- cambio de filtros MCU;
- cambio de `MIDI_UART_ENABLED`;
- cambio de `LED_MATRIX_ENABLED`;
- cambio de frecuencia de muestreo;
- cambio de constantes de payload.

Esos cambios pertenecen a firmware/configuracion controlada, no a operacion live.

## 3. Controles ya resueltos en final-v4

| Control | Subsistema | Estado final-v4 | Riesgo restante | Accion futura |
| --- | --- | --- | --- | --- |
| `BENCH_REPORT_ENABLED` separado | Firmware | Resuelto: reports Monitor separados de streaming EEG. | Alias legacy `BENCH_NOTIFY_ENABLED` puede confundir. | Mantener alias solo como compatibilidad. |
| Panic MIDI en backend/WebUI | MIDI/UI | Resuelto: `POST /midi/panic` y boton WebUI llaman `send_panic()`. | No hay panic autonomo si Python/App Lab cae. | Mantener siempre; valorar panic firmware si se justifica. |
| Controles musicales basicos | WebUI/Musica | Resuelto: root note, main note y scale key disponibles. | Endpoints separados pueden aplicar cambios parciales. | Preferir `/music/config` atomico en simplificacion. |
| MIDI fisico live | Python/Firmware | Resuelto: `MidiByteTransport` -> `midi_bytes` -> `Serial1/D1` TX invertido. | Cambios de UART/polaridad requieren validacion fisica. | No tocar sin placa. |
| Quality gate | DSP/Sonificacion | Resuelto: `compute_quality_diagnostics()` + `compute_spectral_quality()`. | Umbrales empiricos. | Mantener y testear escenarios clean/artifact/bad. |
| Nombres reportables de sonificacion | DSP/MIDI/docs | Resuelto: nombres final-v4 en snapshot/reports/figuras. | Aliases legacy siguen internamente. | Migrar/ocultar gradualmente. |
| Capturas con musica | Tools/Capture | Resuelto: `music_snapshots.jsonl`, `music_notes.csv`, summary. | Depende de `final_capture_session.py`. | Mantener como trazabilidad TFG. |
| Benchmarks MCU sin contaminar Bridge | Firmware/tools | Resuelto: Monitor `[BENCH] EEG_MIDI` + parser offline. | Parser depende del formato textual. | Conservar logs finales y parser. |
| Etiquetado CH1-only basico | Snapshot/UI/docs | Resuelto parcialmente: UI/snapshot muestran `ADS_DIAGNOSTIC_MODE` y canales activos/apagados. | Falta panel BIAS/RLD mas pedagogico. | Mejorar documentacion/UI si se simplifica. |

## 4. Controles parcialmente resueltos

| Control | Subsistema | Estado actual | Riesgo si queda asi | Prioridad | Recomendacion |
| --- | --- | --- | --- | --- | --- |
| Estado ADS mode visible | Firmware/Python/UI | `ADS_DIAGNOSTIC_MODE` y canales se muestran. | Puede no explicar BIAS/RLD fisico. | Media | En TFG explicar modo 5; en UI esencial mostrar texto CH1-only claro. |
| Estado BIAS/RLD visible | Firmware/Python/UI | Documentado en docs, no panel UI dedicado. | Usuario puede olvidar montaje analogico exacto. | Media/Alta | No exponer control; solo mostrar descripcion fija del modo activo. |
| Confirmacion de handler MIDI | Python/Firmware | Transporte cuenta sent/failed y handler devuelve bool. | Fallos parciales pueden ser confusos. | Media | Mantener counters en UI; test mock + placa. |
| Tests endpoints musicales WebUI | WebUI/MIDI | Rutas existen y funcionan conceptualmente. | Rename/payload puede desincronizar UI/backend. | Media/Alta | Crear smoke tests HTTP o procedimiento manual. |
| Control de cola Bridge EEG vs MIDI/LED | Bridge | Benchmarks miden EEG/MIDI en condiciones actuales; LED off. | Activar LED o subir densidad puede alterar latencia. | Alta si se cambia carga | No activar LED en benchmarks finales; repetir medicion si sube trafico. |
| Limitador global notas/segundo | Sonificacion/MIDI | Hay slots/compas, `max_events` y gate, pero no rate limiter global explicito. | Si se cambian parametros puede saturar. | Media | Mantener parametros; crear test si se aumenta densidad. |
| Musica con quality mala | Sonificacion/MIDI | Gate evita nuevos compases; eventos ya programados pueden sonar brevemente. | Artefacto puede persistir hasta vaciar scheduler. | Media | Mantener panic; valorar cortar eventos pendientes solo con pruebas musicales. |
| Logs persistentes de errores | Backend | Errores en logger/snapshot; capturas guardan metadata. | Diagnostico post-prueba limitado. | Baja/Media | No prioritario; usar logs App Lab y reports. |
| Saturacion UI con umbral visible | UI/DSP | Se calcula `saturation_fraction`; UI muestra diagnostico parcial. | Usuario no sabe umbral exacto. | Baja | Mejorar texto/tooltip si se simplifica UI. |

## 5. Controles/riesgos aun abiertos

| Control faltante/riesgo | Subsistema | Motivo | Riesgo si falta | Prioridad | Decision final-v4 |
| --- | --- | --- | --- | --- | --- |
| Contador explicito de DRDY overruns/frame drops | Firmware | `pending > 1` incrementa lag generico, no recupera todos los frames perdidos. | Perdidas DRDY no cuantificadas con precision. | Alta si se toca firmware | No tocar ahora; documentar como mejora firmware futura. |
| Modo raw/unfiltered diagnostico | Firmware/Python | Separar adquisicion real de filtros MCU. | Filtros pueden ocultar problemas ADS/electrodos. | Media/Alta | No necesario para TFG final; valorar solo en rama diagnostica. |
| Watchdog de adquisicion | Firmware/Python | Detectar ausencia prolongada de DRDY/bloques. | UI puede quedar esperando sin causa clara. | Media | Puede implementarse como alerta snapshot, sin tocar ADS. |
| Panic firmware autonomo | Firmware MIDI | Cortar notas aunque Python falle. | Si App Lab cae, notas pueden quedar activas. | Media | Pendiente; no bloquear final-v4. |
| Test automatico de contrato firmware/Python | Streaming | Payload `eeg_block_uV` es manual y grande. | Refactor rompe parseo. | Alta | Crear tests antes de tocar payload. |
| Tests unitarios DSP/sonificacion | DSP/MIDI | Hay pocas pruebas automatizadas. | Refactor cambia comportamiento sin detectar. | Alta | Prioritario antes de simplificar. |
| Compilacion firmware automatizada | Firmware | No verificada desde este entorno documental. | Cambios futuros pueden romper build. | Alta | En placa/App Lab antes de tocar firmware. |
| Control de latencia end-to-end | Bridge/MIDI/externo | Benchmarks miden partes, no latencia fisica completa EEG->MIDI OUT. | Dificil optimizar experiencia live. | Media | Futura validacion avanzada, no esencial para simplificacion inicial. |
| Schema minimo de snapshot | Backend/WebUI | UI depende de muchas claves. | Refactor rompe render silenciosamente. | Alta | Crear antes de tocar WebUI/backend. |
| WebUI comprensible para el autor | UI/docs | Fue generada mayoritariamente por Codex. | Dificil defender/cambiar sin bugs. | Alta | Simplificar con especial cuidado y pruebas visuales. |

## 6. Controles que NO conviene anadir a la WebUI esencial

| Control | Motivo para no exponerlo |
| --- | --- |
| Cambiar `ADS_DIAGNOSTIC_MODE` | Requiere recompilar/subir firmware y cambia comparabilidad. |
| Habilitar/deshabilitar filtros MCU | Cambia el contenido espectral y exige nueva validacion. |
| Cambiar `FS_HZ`, `BLOCK_SAMPLES` o `NUM_CHANNELS` | Rompe contrato firmware/Python/tools. |
| Habilitar/deshabilitar `MIDI_UART_ENABLED` desde UI | Es macro firmware y puede dejar UI/backend incoherente. |
| Habilitar/deshabilitar `LED_MATRIX_ENABLED` desde UI | Firmware LED esta compile-time y LED es lateral. |
| Cambiar `LSB_V` o ganancia ADS desde UI | Afecta escala fisica uV y quality. |
| Activar test loop MIDI como control visible principal | Puede confundirse con sonificacion EEG real. |

La WebUI esencial debe limitarse a:

```text
observacion del sistema
panic MIDI
root/main/scale
piano roll
estado de calidad y MIDI
```

## 7. Riesgos por area

### Firmware / ADS

- `ADS_DIAGNOSTIC_MODE=5` debe mantenerse claro: CH1-only, CH2-CH4 no EEG activo.
- DRDY lag no equivale a contador perfecto de frames perdidos.
- Filtros MCU no deben cambiarse sin nuevas capturas.
- SPI/ADS/RDATAC no deben tocarse sin placa.

### Backend / DSP

- `compute_live_features()` es ruta benchmarkeada; no sustituir por `compute_online_features()`.
- Quality gate no debe eliminarse.
- Umbrales quality son empiricos y deben documentarse como tales.
- CH2-CH4 no deben analizarse como EEG activo en las capturas finales.

### Sonificacion / MIDI

- Cambiar nombres publicos de controles rompe reportes, WebUI y figuras.
- Eventos ya agendados pueden sonar aunque una ventana posterior sea mala.
- Panic es obligatorio.
- Aumentar densidad puede saturar transporte.

### WebUI

- Cambios de snapshot/IDs pueden congelar paneles.
- Socket/polling afectan fluidez percibida.
- La UI debe ser entendible para el autor del TFG.
- No exponer controles peligrosos.

### Capturas / tools

- Tools offline no son runtime.
- Capturas antiguas no deben presentarse como evidencia final principal.
- Regenerar figuras puede sobrescribir reportajes si no se revisa diff.
- `set_ads_diagnostic_mode.py` es util pero peligrosa.

## 8. Prioridad para version esencial/UML

### Debe entrar en el UML principal

```text
QualityGate
Panic MIDI
root/main/scale
snapshot minimo
piano roll como observador
midi_bytes
Serial1/D1 TXINV
```

### Debe quedar lateral

```text
CaptureManager
benchmarks
tools offline
LED matrix
MIDI test endpoints
raw/unfiltered diagnostic mode
logs persistentes avanzados
```

### Debe quedar como riesgo/futuro

```text
panic firmware autonomo
latencia end-to-end fisica
watchdog avanzado
contador DRDY overrun mas explicito
schema automatico de snapshot
```

## 9. Pruebas recomendadas antes de implementar controles nuevos

1. Si toca firmware: compilar y probar en placa.
2. Si toca ADS/DRDY: monitorizar ID, status, rates y drops.
3. Si toca WebUI: navegador, consola sin errores, fluidez y botones.
4. Si toca root/main/scale: probar endpoint y snapshot.
5. Si toca MIDI: nota diagnostica, panic y sonificacion real.
6. Si toca quality: escenarios clean/artifact/bad y captura real.
7. Si toca tools: ejecutar sobre copia y revisar diff.
8. Si toca payload: test `eeg_contract.py` y captura corta.

## 10. Conclusion

Final-v4 ya resolvio controles importantes que antes faltaban:

```text
panic WebUI
root/main/scale
MIDI fisico live
quality gate
capturas con musica
benchmarks MCU/Python reales
etiquetado basico CH1-only
```

Lo que queda abierto no impide defender el TFG, pero si orienta la futura version simplificada/UML:

```text
crear tests de contrato
hacer WebUI mas comprensible
mantener controles seguros
no exponer firmware/ADS desde UI
separar flujo principal y herramientas laterales
```





