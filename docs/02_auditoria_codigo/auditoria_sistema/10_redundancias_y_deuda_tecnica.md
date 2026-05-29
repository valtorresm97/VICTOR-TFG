# 10. Redundancias y deuda tecnica - final-v4

## 1. Objetivo

Este documento recoge redundancias ya resueltas, compatibilidades que todavia existen y deuda tecnica real que conviene tener en cuenta antes de crear una version simplificada/UML.

La mayoria de redundancias fuertes detectadas durante fases anteriores ya se eliminaron o se centralizaron. Por tanto, el foco actual no es "limpiar por limpiar", sino distinguir:

```text
lo resuelto
lo que queda como compatibilidad historica
lo que sigue siendo deuda real
lo que no debe tocarse sin pruebas
```

La auditoria funcion por funcion mas exhaustiva esta en:

```text
docs/02_auditoria_codigo/funcion_por_funcion/10_mapa_funciones_criticas.md
docs/02_auditoria_codigo/funcion_por_funcion/11_hallazgos_para_simplificacion_futura.md
```

Estado actual de referencia:

```text
Rama integrada: firmware-final-v4
Rama documental: refactor/essential-eeg-midi-plan
```

## 2. Lectura general

La arquitectura final-v4 ya esta bastante consolidada:

- el contrato EEG por bloques esta centralizado en Python mediante `eeg_contract.py`;
- el DSP multitaper vive en `DSPCore`;
- el quality gate vive en `spectral_quality.py`;
- la sonificacion publica nombres final-v4;
- el MIDI fisico usa `midi_bytes` y `Serial1`/D1 con TX invertido;
- la WebUI ya tiene panic y controles root/main/scale;
- las capturas finales guardan EEG y musica;
- los benchmarks reales estan separados de las capturas.

La deuda actual es mas de explicabilidad, separacion de responsabilidades, tests de contrato y limpieza de rutas legacy que de duplicacion funcional grave.

## 3. Redundancias resueltas o muy reducidas

| Redundancia/deuda original | Archivos afectados | Estado final-v4 | Riesgo restante | Recomendacion futura |
| --- | --- | --- | --- | --- |
| Constantes EEG repetidas (`FS_HZ`, `NUM_CH`, `BLOCK_SAMPLES`, `LSB_V`, status mask) | `sketch.ino`, `receiver.py`, `capture_manager.py`, tools offline | Resuelto en Python: receiver, capture, backend y tools usan `python/eeg_contract.py`. Firmware sigue siendo fuente fisica del payload real. | Si firmware cambia y Python no, se rompe contrato. | Mantener sincronÃ­a con `streaming.h`, ADS1299 y `eeg_contract.py`. |
| Formato `eeg_block_uV` duplicado manualmente en Python | `streaming.h`, `receiver.py`, `capture_manager.py` | Resuelto en Python: evento, longitud, stride, parseo e iteracion por muestra viven en `eeg_contract.py`. | Firmware sigue construyendo payload manualmente. | Si cambia el payload, actualizar firmware y parser en el mismo commit. |
| DSP multitaper duplicado en live/offline | `dsp_core.py`, tools de analisis | Resuelto: analyzers y validadores reutilizan `DSPCore`. | Si una tool calcula PSD por su cuenta, puede divergir. | Mantener `DSPCore` como unica implementacion DPSS/FFT. |
| Quality score duplicado parcialmente | `spectral_quality.py`, `validate_spectral_features.py`, docs | Resuelto: validacion offline usa `compute_spectral_quality()` como fuente. | Umbrales siguen siendo empiricos. | Mantener umbrales en `spectral_quality.py` y docs de diseno. |
| Escritura JSON atomica duplicada | `app_state.py`, `capture_manager.py`, `capture_eeg_quality.py` | Resuelto: `app_state.atomic_write_json()` centraliza escritura atomica y conversion segura. | Algunas tools offline pueden escribir JSON directo. | No reintroducir helpers locales. |
| Configuracion por env dispersa en Python | `backend_service.py`, `led_matrix_visualizer.py`, tools | Bastante resuelto con `runtime_config.py`. | Firmware mantiene macros compile-time separadas, como debe ser. | Documentar env Python y macros firmware juntos, pero no mezclarlos. |
| `BENCH_NOTIFY_ENABLED` mezclaba streaming y benchmark | `sketch.ino` | Resuelto conceptualmente: streaming usa `EEG_STREAMING_NOTIFY_ENABLED`; reportes usan `BENCH_REPORT_ENABLED`. | Alias legacy puede confundir. | Mantener alias solo para perfiles antiguos; no usarlo en docs principales. |
| `dashboard.py` esperado por docs iniciales | Prompt/docs antiguas frente a `web_server.py` + assets | Resuelto: la UI real es WebUI HTML/CSS/JS. | Alguna documentacion vieja puede seguir diciendo Streamlit/dashboard. | Mantener README y configuracion final-v4 como fuente principal. |
| Adafruit NeoPixel declarado pero no usado | `sketch/sketch.yaml` | Resuelto: se retiro si no habia uso real. | Reintroduccion accidental. | Reintroducir solo con implementacion real. |
| `std::vector` en handler firmware LED | `sketch.ino` | Resuelto: `led_matrix_row` usa chunks fijos y framebuffer estatico. | LED sigue siendo Bridge-heavy si se activa. | Mantener LED desactivada salvo prueba especifica. |
| `USE_SYNTHETIC` parcialmente comentado | `sketch.ino` | Resuelto: modo sintetico y ADS real separados por macro. | No es evidencia TFG final. | Mantener default `0`. |
| CH2-CH4 transmitidos aunque modo 5 los apaga | Firmware/Python/UI | Resuelto como decision de contrato: payload sigue 4ch, UI/snapshot documentan modo 5. | Interpretacion incorrecta si se olvida CH1-only. | Mantener texto CH1 principal en docs/reportes. |
| Reports/documentos solapados | `docs/resultados_*`, `docs/validacion_tfg/*` | Parcialmente resuelto con README e indices. | Todavia puede haber documentos historicos con lenguaje antiguo. | Mantener docs definitivos claramente indexados. |
| `packed_points` LED alternativo | `led_matrix_visualizer.py` | Resuelto: transporte LED usa `rows`. | Ninguno importante. | Mantener `rows` como contrato. |
| Capturas guardaban filas en memoria | `capture_manager.py` | Resuelto: escritura incremental CSV. | Errores de disco. | Mantener status `error` si falla escritura. |
| Ruta runtime `state/` dispersa | `app_state.py`, `capture_manager.py`, tools | Resuelto con `runtime_config.runtime_state_dir()`. | Default sigue siendo `state/`. | Usar env solo para varias apps/checkouts. |

## 4. Compatibilidades/historico que aun conviene ocultar en UML

Estas rutas no son necesariamente errores. Muchas existen para compatibilidad o diagnostico. La recomendacion es ocultarlas del UML principal y eliminarlas solo si hay busqueda de referencias, tests y prueba en placa cuando aplique.

| Elemento | Estado actual | Por que no va al UML principal | Accion futura |
| --- | --- | --- | --- |
| `receiver.eeg_frame_uV()` | Ruta legacy de muestras individuales. En la busqueda actual aparece como definicion/ruta aislada, no como flujo principal. | Final-v4 usa `eeg_block_uV`. | Eliminar solo tras confirmar que App Lab/Bridge no lo invoca. |
| `EEGSignalProcessor.compute_online_features()` | Ruta secundaria. En la busqueda actual aparece como definicion; la ruta live benchmarkeada es `compute_live_features()`. | Puede confundir al explicar DSP. | Ocultar del UML; eliminar solo tras buscar referencias en tools/tests. |
| `BarGenerator.generate_bars()` | Wrapper de compatibilidad. El backend live usa `generate_live_bar()`. | No representa la generacion live real. | Candidato a eliminar si no hay referencias externas. |
| `NoteGenerator.generate_notes_for_segment()` | Wrapper multi-bar. El backend live usa `generate_notes_for_bar()`. | No representa la ruta live real. | Candidato a eliminar si no hay referencias externas. |
| Aliases legacy de sonificacion | `activity`, `calmness`, `tension`, etc. | Final-v4 debe explicar nombres EEG-reportables. | Migrar internamente antes de borrar propiedades legacy. |
| `controlValue()` con fallback legacy en WebUI | Compatibilidad JS con nombres antiguos. | En final-v4 se deben mostrar nombres nuevos. | Quitar solo tras verificar snapshot final-v4 y navegador. |
| MIDI test loop/endpoints | Diagnostico MIDI. | No es sonificacion EEG. | Mantener oculto en UML; conservar test manual si es util. |
| LED matrix | Lateral/desactivada por defecto. | No participa en EEG->MIDI fisico. | Mantener lateral o excluir en version esencial. |
| Polling fallback WebUI | Robustez ante socket. | No es logica principal. | Simplificar solo si no se pierde fluidez. |

## 5. Deuda tecnica real aun vigente

| Deuda tecnica | Archivos afectados | Riesgo | Prioridad | Recomendacion futura |
| --- | --- | --- | --- | --- |
| `backend_service.py` concentra demasiadas responsabilidades | `backend_service.py` | Dificulta UML y cambios seguros; mezcla RX, DSP, quality, music, MIDI, WebUI, LED y capture. | Alta | Separar conceptualmente primero; despues valorar extraer snapshot/music engine/transports sin cambiar API. |
| Snapshot grande sin schema/test automatico | `backend_service.py`, `assets/app.js`, `web_server.py` | Cambios de nombres pueden congelar UI sin error fuerte. | Alta | Crear fixture/schema minimo de snapshot final-v4. |
| WebUI poco comprensible y muy acoplada al snapshot | `assets/app.js`, `assets/index.html` | Dificulta defensa del TFG y cambios seguros. | Alta | Reordenar JS por bloques, comentar contrato y probar fluidez. |
| Doble inicializacion SPI | `sketch.ino`, `ADS1299Plus.begin()` | Puede confundir refactor futuro; no se ha demostrado fallo. | Media/alta | Revisar solo con placa: ADS ID, RDATAC, status y benchmarks. |
| Payload Bridge `eeg_block_uV` construido manualmente en firmware | `streaming.h` | Cambios de `BLOCK_SAMPLES`/canales obligan a tocar muchas posiciones. | Alta si se cambia contrato | No tocar salvo necesidad; crear test de parser/longitud. |
| Quality gate heuristico | `spectral_quality.py` | Umbrales empiricos pueden ser conservadores o permisivos. | Media/alta | Mantener hasta tener mas capturas; crear tests clean/artifact/bad. |
| `compute_quality_diagnostics()` puede duplicar trabajo espectral | `eeg_signal_processor.py` | Coste extra, aunque benchmarks muestran margen. | Media | No optimizar prematuramente; solo reusar PSD si se rediseÃ±a con tests. |
| Comentarios historicos MIDI/D1/handler | `midi_live.py`, `midi_byte_transport.py`, docs | Confunden porque `midi_bytes` ya existe y esta validado. | Media | Limpiar en primera fase sin runtime changes. |
| Comentarios historicos ADS mode normal | `sketch.ino`, docs antiguos | Pueden hacer creer que modo 0 es final. | Media | Actualizar texto a `ADS_DIAGNOSTIC_MODE=5` como capturas finales. |
| Defaults y docs historicos `final-v3` | varios docs | Confusion documental. | Media | Sustituir por final-v4 donde sea estado actual; conservar final-v3 solo como historico. |
| Test automatico incompleto para MIDI/WebUI/music config | `midi_live.py`, `midi_byte_transport.py`, `web_server.py`, assets | Cambios de controles pueden romper UX. | Media/alta | Tests de bytes, panic, root/main/scale y smoke navegador. |
| Tools de generacion documental grandes | `build_validation_docs.py`, `build_final_capture_docs_matplotlib.py` | Pueden sobrescribir muchos archivos. | Media | Usarlas con git limpio; no refactorizar antes de cerrar TFG. |
| LED enabled puede anadir 8 Bridge.call por frame | LED modules + firmware | Puede alterar benchmarks si se activa. | Baja/media | Mantener disabled por defecto; benchmark especifico si se activa. |

## 6. Redundancias que no deben eliminarse ahora

Algunas duplicaciones son intencionales o aceptables:

| Elemento | Por que se conserva |
| --- | --- |
| Constantes firmware y Python | Firmware y Python no comparten codigo; deben estar documentadas y sincronizadas. |
| `metadata.json` y reportes Markdown/JSON | Sirven a trazabilidad humana y parseo automatico. |
| Snapshot WebUI y snapshot disco | Uno sirve live/socket; otro fallback/tools. |
| CSV crudo y features offline | El CSV conserva senal; los features documentan interpretacion posterior. |
| Reportajes manuales y docs generados | Los manuales son narrativos; los generados son reproducibles. |
| WebUI socket y polling fallback | Duplican canal de actualizacion, pero aportan robustez. |
| MIDI test endpoints y ruta EEG->MIDI | Diagnostico separado del flujo real; no mezclar, pero no borrar sin alternativa. |

## 7. Prioridad para simplificacion futura

### Fase 1 - Limpieza segura sin runtime changes

- Limpiar comentarios historicos de MIDI, ADS y final-v3.
- Aclarar en docs que final-v4 usa modo 5 CH1-only.
- Ocultar rutas legacy en diagramas.
- No borrar funciones.

### Fase 2 - Tests de contrato

- `eeg_contract.py`: payload `eeg_block_uV`.
- `midi_live.py`: bytes, scheduler y panic.
- `midi_byte_transport.py`: mock Bridge.
- `spectral_quality.py`: clean/artifact/bad.
- Snapshot minimo WebUI.
- Root/main/scale HTTP.

### Fase 3 - UML conceptual

- Nucleo EEG->MIDI.
- WebUI como observador/control ligero.
- Capture/tools/benchmarks como laterales.
- LED como lateral/desactivado.

### Fase 4 - Refactor suave

- Extraer/ordenar snapshot si hay tests.
- Ordenar `assets/app.js` por secciones comprensibles.
- Usar `/music/config` atomico desde WebUI si se prueba.
- Reducir comentarios obsoletos.

### Fase 5 - Eliminacion real de legacy

Solo despues de tests y busqueda:

```text
eeg_frame_uV
compute_online_features
generate_bars
generate_notes_for_segment
legacy aliases de sonificacion
MIDI test loop si hay alternativa
LED si se decide excluir completamente
```

## 8. Reglas antes de eliminar codigo

1. Buscar referencias en todo el repo.
2. Confirmar que no hay uso desde App Lab/Bridge externo.
3. Ejecutar `py_compile`.
4. Ejecutar tests de contrato si existen.
5. Probar WebUI si toca snapshot/assets.
6. Probar placa si toca firmware, Bridge, MIDI, ADS o filtros.
7. Revisar `git diff --stat` antes de commit.
8. No mezclar eliminaciones con refactors grandes.

## 9. Conclusion

La mayor parte de redundancias funcionales importantes ya se resolvio. Lo que queda para la futura simplificacion no es una limpieza agresiva, sino:

```text
ocultar rutas legacy del UML
crear tests de contrato
limpiar comentarios historicos
separar responsabilidades demasiado anchas
hacer la WebUI comprensible
mantener herramientas y evidencias TFG como laterales
```

La prioridad no debe ser reducir lineas de codigo, sino dejar una version esencial que conserve el funcionamiento validado y sea explicable en la memoria.

