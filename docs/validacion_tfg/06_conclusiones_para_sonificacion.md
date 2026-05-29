# 06. Conclusiones para sonificacion - final-v4

## 1. Objetivo

Este documento resume que decisiones de sonificacion se justifican a partir de la validacion de adquisicion, calidad de senal, DSP multitaper y bandas EEG.

A diferencia de la version inicial generada automaticamente, final-v4 ya no tiene la sonificacion como fase pendiente: existe una ruta integrada con controles reportables, quality gate, WebUI, notas registradas y MIDI fisico validado.

## 2. Principio de diseno

La sonificacion no debe depender de potencias absolutas crudas ni de una unica banda aislada. La estrategia defendible es:

```text
features relativas + suavizado + normalizacion + quality gate
  -> controles musicales acotados
  -> notas MIDI / piano roll / MIDI OUT fisico
```

Esto permite que el sistema responda a la dinamica de la senal sin convertir artefactos de mandibula, frente, cableado o contacto en actividad musical excesiva.

## 3. Decisiones validadas

| Decision | Justificacion | Estado final-v4 |
| --- | --- | --- |
| Usar bandpowers relativos | Reducen dependencia de escala absoluta y contacto. | Vigente |
| Usar ventana DSP de 4 s | Permite estimacion espectral mas estable. | Vigente |
| Usar hop de 64 muestras | Actualizacion cada 256 ms con margen temporal amplio. | Vigente |
| Usar multitaper | Reduce variabilidad/leakage frente a periodograma simple. | Vigente |
| Usar quality gate | Evita que ventanas artefactadas dominen la musica. | Esencial |
| Suavizar controles | Evita saltos bruscos por transitorios. | Vigente |
| Mantener nombres EEG-reportables | Facilita defender el TFG. | Vigente |
| Registrar musica durante capturas | Permite trazabilidad EEG -> controles -> notas. | Vigente |
| Conservar panic MIDI | Evita notas colgadas. | Esencial |

## 4. Controles reportables final-v4

Los controles que deben usarse en la memoria son:

| Control | Lectura tecnica | Uso musical |
| --- | --- | --- |
| `alpha_drive` | Peso relativo de alpha/reposo espectral. | Estabilidad/reposo relativo. |
| `beta_gamma_drive` | Activacion beta/gamma con cautela por EMG. | Tension armonica/sincopa. |
| `rms_beta_activity` | RMS normalizado + bandas rapidas. | Actividad global. |
| `band_driven_density` | Actividad espectral convertida en densidad. | Densidad ritmica. |
| `spectral_register` | Pico/frecuencia dominante normalizada. | Registro melodico. |
| `alpha_stability` | Alpha frente a actividad rapida. | Estabilidad armonica. |
| `rms_band_velocity` | Amplitud y bandas. | Velocity MIDI. |
| `band_note_probability` | Probabilidad musical derivada de bandas. | Probabilidad de nota. |

Los nombres antiguos (`activity`, `calmness`, `tension`, `rhythmic_density`, etc.) deben tratarse como aliases legacy o historicos, no como nombres principales de redaccion.

## 5. Relacion con quality gate

La validacion de calidad demuestra que una captura puede tener adquisicion tecnicamente correcta y, aun asi, contener ventanas con artefactos. Por tanto, la sonificacion debe distinguir:

```text
ventana usable -> generar/adaptar musica
ventana dudosa -> atenuar controles
ventana artefactada -> bloquear o reducir eventos nuevos
```

En final-v4 esta logica se aplica mediante:

```text
compute_quality_diagnostics()
  -> compute_spectral_quality()
  -> SonificationFeatureAdapter.update()
```

El quality gate no elimina la necesidad de buen montaje, pero reduce el riesgo de que artefactos se traduzcan directamente en notas.

## 6. Relacion con capturas finales

La sesion `s01_20260528` conserva, por captura:

```text
music_snapshots.jsonl
music_notes.csv
music_capture_summary.json
windowed_sonification_features.csv
```

Esto permite justificar que la sonificacion quedo registrada durante adquisiciones reales y puede analizarse offline junto con EEG, bandpowers y calidad.

La lectura correcta es:

```text
La sonificacion funciono y quedo persistida.
La interpretacion fisiologica de cada nota debe hacerse con cautela.
El valor principal para el TFG es demostrar integracion tecnica EEG -> features -> controles -> notas/MIDI.
```

## 7. Limitaciones

- Las bandas no deben interpretarse como diagnostico clinico.
- Beta/gamma pueden contener EMG.
- Delta puede contaminarse por drift o movimiento.
- El quality gate depende de umbrales empiricos.
- El piano roll muestra intencion musical, no confirmacion fisica del sintetizador externo.
- La validacion de latencia fisica EEG -> MIDI OUT queda como trabajo futuro.

## 8. Conclusion

La validacion respalda una sonificacion basada en features relativas, suavizadas y filtradas por calidad. En final-v4, la sonificacion ya esta integrada con el backend, la WebUI, el piano roll, el registro de notas y el MIDI fisico.

La formulacion defendible para el TFG es:

```text
La EEG no se convierte directamente en musica.
Primero se evalua calidad, despues se extraen rasgos espectrales y finalmente esos rasgos modulan parametros musicales acotados.
```

Esta estrategia permite una sonificacion expresiva, trazable y prudente frente a artefactos.
