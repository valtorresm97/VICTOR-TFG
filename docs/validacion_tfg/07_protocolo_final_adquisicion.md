# 07. Protocolo final de adquisicion - final-v4

## 1. Estado del documento

Este documento sustituye al protocolo generado automaticamente por `python/tools/build_validation_docs.py` durante la fase `diagnosis/sonificacion-atenuacion-artefactos`.

La version anterior era util como historico de la captura intermedia:

```text
20260524-122200_final_atenuacion_artefactos_mixed_states
```

pero ya no debe considerarse el protocolo final principal. En final-v4, la adquisicion final reportable esta asociada a:

```text
s01_20260528
captures/capturas finales/
docs/validacion_tfg/10_resultados_captura_final_laboratorio.md
docs/validacion_tfg/reportaje_sesion_final_s01_20260528.md
```

## 2. Objetivo del protocolo

El objetivo del protocolo final es obtener capturas reales EEG-MIDI trazables, repetibles y documentables para el TFG:

```text
ADS1299 -> firmware -> Bridge -> Python -> DSP -> quality gate -> sonificacion -> notas MIDI registradas
```

El protocolo valida integracion tecnica, no EEG clinica. Por tanto, las capturas se aceptan si demuestran continuidad, metadata completa, analisis espectral y registro musical; la interpretacion fisiologica se hace con cautela.

## 3. Rama y configuracion de referencia

| Campo | Valor final-v4 |
| --- | --- |
| Rama integrada | `firmware-final-v4` |
| Rama documental actual | `refactor/essential-eeg-midi-plan` |
| Montaje | `ear_eeg_ch1_only` |
| Modo ADS | `bias_ch1_only_loff_off` |
| Macro ADS | `ADS_DIAGNOSTIC_MODE=5` |
| Canal EEG principal | CH1 |
| CH2-CH4 | Conservados por contrato, no EEG activo en capturas finales |
| Frecuencia | 250 Hz |
| Ventana DSP | 4 s |
| Hop DSP | 64 muestras |
| MIDI fisico | `Serial1`/D1 con TX invertido |
| LED matrix | Desactivada por defecto |

## 4. Preparacion previa

Antes de grabar:

1. Confirmar que la rama/codigo cargado corresponde al estado final-v4.
2. Verificar que App Lab arranca sin errores.
3. Confirmar que el backend publica snapshots recientes.
4. Comprobar que CH1 muestra valores plausibles en reposo.
5. Fijar cables para reducir movimiento.
6. Evitar contacto deficiente en electrodos.
7. Evitar movimiento mandibular salvo en la condicion especifica.
8. Evitar tocar cables, placa o electrodos durante la captura.
9. Verificar que el panic MIDI esta disponible.
10. Registrar sujeto, fecha, montaje, modo ADS y observaciones.

## 5. Orden recomendado de pruebas

Para una sesion multiestado o multisujeto, el orden recomendado es:

| Orden | Condicion | Duracion orientativa | Objetivo |
| --- | --- | ---: | --- |
| 00 | `precheck_10s` | 10 s | Verificar guardado, metadata, EEG y musica. |
| 01 | `eyes_open_rest_60s` | 60 s | Reposo con ojos abiertos. |
| 02 | `eyes_closed_rest_60s` | 60 s | Reposo con ojos cerrados. |
| 03 | `quiet_rest_60s` | 60 s | Reposo quieto sostenido. |
| 04 | `blink_artifact_30s` | 30 s | Artefacto ocular controlado. |
| 05 | `jaw_artifact_30s` | 30 s | Artefacto mandibular/EMG si procede. |
| 06 | `eyes_open_repeat_30s` | 30 s | Repeticion breve para comprobar estabilidad. |

Nota: en la sesion final `s01_20260528` no se conserva una carpeta real `05_jaw_artifact_30s`. Por tanto, el analisis oficial se centra en las condiciones que existen realmente en `captures/capturas finales/`.

## 6. Comandos de captura

La captura final debe hacerse con las herramientas de sesion/captura actuales. La herramienta `capture_eeg_quality.py` no calcula el quality gate por si sola: escribe una solicitud al backend vivo para que este capture los datos reales.

Ejemplo de captura individual:

```bash
python3 python/tools/capture_eeg_quality.py \
  --condition eyes_open_rest_60s \
  --duration 60 \
  --timeout-extra 180
```

Para una sesion final organizada, usar el flujo documentado por:

```text
python/tools/final_capture_session.py
docs/04_protocolos_captura/protocolo_capturas_multiusuario.md
docs/04_protocolos_captura/templates/plantilla_sesion_sujeto.md
```

## 7. Artefactos que debe contener cada captura

Una captura final defendible debe conservar:

```text
eeg_timeseries.csv
metadata.json
quality_report.json
quality_report.md
spectral_validation_report.json
spectral_validation_report.md
windowed_bandpowers.csv
windowed_sonification_features.csv
music_snapshots.jsonl
music_notes.csv
music_capture_summary.json
```

Estos artefactos permiten reconstruir:

```text
senal EEG -> calidad -> bandpowers/features -> controles de sonificacion -> notas generadas
```

## 8. Analisis offline posterior

Una vez tomada una captura:

```bash
python3 python/tools/analyze_eeg_capture.py "$DIR"
python3 python/tools/validate_spectral_features.py "$DIR" --channel 0 --window-sec 4 --hop-samples 64
cat "$DIR/quality_report.md"
cat "$DIR/spectral_validation_report.md"
```

Para la sesion final, los reportajes/figuras se generan con los scripts especificos:

```text
python/tools/build_final_capture_docs_matplotlib.py
python/tools/build_capture06_enhanced_figures.py
```

Para regenerar solo figuras de validacion historica `00` a `05`:

```bash
python3 python/tools/build_validation_docs_final_v4_style.py --captures captures --output docs/validacion_tfg
```

Ese wrapper preserva los Markdown revisados y solo regenera figuras.

## 9. Criterios de aceptacion

Aceptar una captura si:

- la frecuencia efectiva es cercana a 250 Hz;
- no hay sample gaps;
- no hay invalid status ADS persistente;
- existe `metadata.json` coherente;
- se guardo `eeg_timeseries.csv`;
- se generaron reports de calidad/espectro;
- existen ventanas limpias o utilizables;
- la fraccion de artefactos es compatible con el objetivo de la prueba;
- se registraron snapshots musicales y/o notas cuando la sonificacion estaba activa.

Repetir o descartar si:

- hay saturacion persistente;
- RMS en mV domina la mayor parte de ventanas;
- 50 Hz domina de forma incompatible con analisis;
- la senal queda plana;
- faltan CSV/metadata;
- no se guardan artefactos musicales esperados;
- se detecta mal contacto o movimiento no controlado.

## 10. Relacion con mixed_states

La captura `final_atenuacion_artefactos_mixed_states` sigue siendo valida como captura intermedia para estudiar quality gate, estados y artefactos:

```text
ojos abiertos -> ojos cerrados -> mandibula -> recuperacion -> parpadeo/frente -> recuperacion -> ojos cerrados
```

No debe presentarse como la sesion final principal. Su papel actual es justificar decisiones de calidad, DSP y artefactos en los documentos `03` y `04`.

## 11. Conclusion

El protocolo final-v4 queda centrado en capturas reales trazables, con metadata, EEG, calidad, espectro, controles de sonificacion y notas persistidas. La captura `mixed_states` queda como antecedente tecnico importante, mientras que `s01_20260528` es la sesion final reportable para resultados del TFG.



