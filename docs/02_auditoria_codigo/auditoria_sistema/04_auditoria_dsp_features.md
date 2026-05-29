# 04. Auditoria DSP y features - final-v4

## 1. Objetivo

Este documento explica el bloque DSP y de extraccion de features en lenguaje narrativo para la redaccion del TFG. La auditoria funcion por funcion mas exhaustiva esta en:

```text
docs/02_auditoria_codigo/funcion_por_funcion/04_dsp_eeg_funcion_por_funcion.md
```

Aqui se describe como la senal recibida desde firmware se convierte en features espectrales, como se evalua la calidad de la ventana y como esos resultados alimentan la sonificacion.

Estado actual de referencia:

```text
Rama integrada: firmware-final-v4
Rama documental: refactor/essential-eeg-midi-plan
```

## 2. Pipeline DSP live

El pipeline live final-v4 es:

```text
receiver.py
  â†“ bloques en microvoltios
EEGSignalProcessor.add_block_uV()
  â†“ convierte uV a V
ring buffer multicanal 10 s
  â†“ ventana CH1 4 s
EEGSignalProcessor.compute_live_features()
  â†“
DSPCore.compute_features(psd_method="multitaper")
  â†“
bandpower_abs, bandpower_rel, peaks, rms
  â†“
compute_quality_diagnostics()
  â†“
compute_spectral_quality()
  â†“
SonificationFeatureAdapter.update()
```

La senal llega ya filtrada desde el MCU:

```text
HP/DC blocker 0.5 Hz
notch 50 Hz
LP 40 Hz
```

Python no aplica filtros EEG principales adicionales en el loop live. `DSPCore.preprocess()` realiza detrend lineal y correccion robusta de outliers antes de calcular PSD.

## 3. Canal principal y montaje final

Las capturas finales se realizaron con:

```text
ADS_DIAGNOSTIC_MODE=5
ADS_MODE=bias_ch1_only_loff_off
montage=ear_eeg_ch1_only
```

Por tanto:

- CH1 es el canal EEG principal para features, quality gate y sonificacion.
- CH2-CH4 se conservan en el payload y CSV por contrato, pero no deben interpretarse como EEG activo en la sesion final.
- Los reportes, figuras y validaciones deben indicar esta limitacion.

## 4. Parametros principales

| Parametro | Valor final-v4 | Archivo | Comentario |
| --- | ---: | --- | --- |
| Frecuencia | 250 Hz | `eeg_contract.py`, backend | Debe coincidir con firmware. |
| Canales | 4 | `eeg_contract.py` | Contrato ADS1299-4, aunque final se interpreta CH1. |
| Ventana features | 4.0 s | `backend_service.py` | 1000 muestras. |
| Hop features | 64 muestras | `backend_service.py` | 256 ms. |
| Buffer live | 10 s | `backend_service.py` | Historial de seguridad. |
| Metodo PSD live | multitaper | `backend_service.py`, `dsp_core.py` | Metodo principal final-v4. |
| Multitaper NW | 2.5 | `dsp_core.py` | Suavizado/resolucion. |
| Tapers | `2*NW-1 = 4` | `dsp_core.py` | Promedio DPSS. |
| Bandas | delta 0.5-4, theta 4-8, alpha 8-13, beta 13-30, gamma 30-50 | `dsp_core.py` | Base de features y sonificacion. |
| Quality clean | `score >= 0.85` | `spectral_quality.py` | Sonificacion plena. |
| Quality bad | `score < 0.50` | `spectral_quality.py` | Bloquea nueva sonificacion. |

El presupuesto temporal de features es:

```text
64 / 250 = 0.256 s = 256 ms
```

Los benchmarks final-v4 muestran que `compute_live_features()` queda muy por debajo de ese margen.

## 5. Unidades

La cadena de unidades es critica:

| Etapa | Unidad | Comentario |
| --- | --- | --- |
| Firmware | microvoltios enteros | Payload `eeg_block_uV`. |
| Receiver | microvoltios | No convierte, valida y encola. |
| `add_block_uV()` | uV -> V | Multiplica por `1e-6`. |
| Ring buffer | voltios | `float32`, shape multicanal. |
| `DSPCore` | voltios | PSD, RMS, bandpowers. |
| Diagnostics/quality | microvoltios | RMS/PTP/percentiles se expresan para interpretacion. |
| Sonificacion | 0..1 | Controles normalizados y suavizados. |

Regla:

```text
No mezclar uV y V.
add_block_uV() recibe microvoltios.
add_sample() recibe voltios y no es la ruta principal de bloques final-v4.
```

## 6. Features espectrales

| Feature | Origen | Archivo | Formula/idea | Uso | Riesgo | Estado |
| --- | --- | --- | --- | --- | --- | --- |
| `rms` | Senal preprocesada | `dsp_core.py` | `sqrt(mean(x^2))` en V | Actividad/diagnostico | Sensible a artefactos | Activa |
| `bandpower_abs` | PSD | `dsp_core.py` | Integral por banda reescalada a potencia temporal | Validacion/offline y snapshot | No es calibracion clinica absoluta | Activa |
| `bandpower_rel` | PSD | `dsp_core.py` | Banda / suma bandas | Sonificacion y UI | Cambia si filtros limitan gamma | Activa |
| `peak_freq` | PSD | `dsp_core.py` | Frecuencia de maximo global | Snapshot/registro | Puede saltar con ruido | Activa |
| `peak_alpha` | PSD | `dsp_core.py` | Maximo 8-13 Hz | Seguimiento alfa | Necesita interpretacion cautelosa | Activa |
| `peak_beta` | PSD | `dsp_core.py` | Maximo 13-30 Hz | Actividad rapida | EMG puede contaminar | Activa |
| `alpha_beta_ratio` | Bandpowers | `dsp_core.py`/features | Relacion alpha/beta | Resumen espectral | No debe sobreinterpretarse | Activa |
| `line_50_ratio` | PSD diagnostico | `eeg_signal_processor.py` | Potencia 49-51 / 1-50 Hz | Quality warnings | Notch puede ocultar parte | Activa |
| `spectral_quality.score` | Features + diagnostico + RX | `spectral_quality.py` | 1 - suma penalizaciones | Gate de sonificacion | Umbrales empiricos | Activa |
| `gate_factor` | Score | `spectral_quality.py` | clean 1.0, caution 0.75, artifact 0.35, bad 0 | Atenuacion musical | Puede ser conservador | Activa |

## 7. Quality gate

El quality gate se conserva como bloque esencial en final-v4:

```text
compute_quality_diagnostics()
  -> compute_spectral_quality()
```

En UML y TFG puede representarse como:

```text
SignalQuality / QualityGate
```

Estados:

| Estado | Score | Gate | Comportamiento |
| --- | ---: | ---: | --- |
| `clean` | `>=0.85` | `1.0` | Sonificacion plena. |
| `usable_with_caution` | `>=0.70` | `0.75` | Atenuacion ligera. |
| `artifact_suspected` | `>=0.50` | `0.35` | Atenuacion fuerte. |
| `bad` | `<0.50` | `0.0` | No valido para sonificacion. |

Penalizaciones actuales incluyen:

- ventana no lista;
- bandpowers no finitos;
- status ADS invalido;
- perdidas/drops/malformed recientes;
- saturacion;
- flatline;
- RMS alto/bajo;
- pico-pico alto;
- ratio 50 Hz alto;
- saltos abruptos;
- gamma relativa alta;
- slow power con RMS alto.

Protecciones:

- `score < 0.50` marca `valid=False`, impidiendo generar nuevo compas.
- El baseline RMS no se actualiza si `quality_score < 0.70`.
- El gate atenua actividad, tension, densidad, velocity, probabilidad y estabilidad.
- El receiver aporta errores RX por delta para que errores antiguos no silencien la musica permanentemente.

## 8. Controles de sonificacion final-v4

En final-v4 deben usarse nombres reportables vinculados a EEG/features:

| Control final-v4 | Alias legacy interno | Origen conceptual | Uso musical | Riesgo |
| --- | --- | --- | --- | --- |
| `alpha_drive` | `calmness` | Alfa relativa y relacion alpha/beta | Estabilidad/reposo relativo | Alpha en montaje auricular requiere cautela. |
| `beta_gamma_drive` | `tension` | Beta/gamma relativa | Tension armonica/sincopa | EMG puede elevar beta/gamma. |
| `rms_beta_activity` | `activity` | RMS normalizado + potencia rapida | Actividad global, velocity y densidad | Artefactos suben RMS. |
| `band_driven_density` | `rhythmic_density` | Actividad + tension | Densidad ritmica | Movimiento puede generar exceso de notas. |
| `spectral_register` | `register` | Pico/frecuencia dominante normalizada | Registro melodico | Peak global puede saltar. |
| `alpha_stability` | `harmonic_stability` | Alpha drive frente a tension | Estabilidad armonica | Indirecto, no clinico. |
| `rms_band_velocity` | `velocity_factor` | Actividad RMS/bandas | Velocity MIDI | Artefactos pueden aumentar dinamica. |
| `band_note_probability` | `note_probability` | Densidad y bandas | Probabilidad de notas | Cascadas si no hay gate. |

Los nombres legacy se conservan solo por compatibilidad interna y no deben protagonizar la redaccion del TFG ni el UML principal.

## 9. Suavizado y estabilidad temporal

`SonificationFeatureAdapter` aplica:

- baseline RMS adaptativo;
- quality gate;
- EMA sobre controles;
- limites 0..1;
- congelacion/atenuacion de ventanas malas.

Esto evita que la musica responda bruscamente a cambios puntuales o artefactos. Aun asi, la salida no debe interpretarse como diagnostico clinico, sino como una transformacion musical de rasgos espectrales y de amplitud.

## 10. Runtime frente a validacion offline

Runtime live:

```text
BackendService.step()
  -> compute_live_features()
  -> compute_quality_diagnostics()
  -> compute_spectral_quality()
  -> SonificationFeatureAdapter.update()
```

Validacion offline:

```text
validate_spectral_features.py
analyze_eeg_capture.py
build_final_capture_docs_matplotlib.py
build_capture06_enhanced_figures.py
```

La validacion offline recalcula bandpowers, quality gate y controles para generar CSV, informes y figuras. No sustituye el runtime, pero permite documentar y comprobar lo ocurrido en capturas reales.

## 11. Rutas que no entran en UML principal

Quedan fuera del flujo principal:

```text
EEGSignalProcessor.compute_online_features()
get_spectrogram() live
herramientas offline
generadores de figuras
```

`compute_online_features()` se considera ruta secundaria/no principal. La ruta live validada y benchmarkeada es:

```text
compute_live_features()
```

## 12. Riesgos DSP principales

- Cambiar bandas invalida comparabilidad con reportes y controles musicales.
- Cambiar ventana de 4 s altera resolucion y latencia.
- Cambiar hop de 64 muestras altera presupuesto de 256 ms.
- Cambiar multitaper por Welch/periodogram cambia features y figuras.
- Cambiar unidades uV/V rompe RMS, quality score y sonificacion.
- Eliminar quality gate permite que ventanas malas vuelvan a mover la musica.
- Interpretar CH2-CH4 como EEG activo en modo 5 seria incorrecto.
- Gamma y beta pueden contener EMG; deben interpretarse con cautela.
- La sesion final valida integracion tecnica, no EEG clinico limpio.

## 13. Pruebas minimas si se toca DSP

1. `python3 -m py_compile python/dsp_core.py python/eeg_signal_processor.py python/spectral_quality.py python/sonification_features.py`.
2. Test uV->V: 1000 uV -> 0.001 V.
3. Test ring buffer con wrap.
4. Test seno 10 Hz con pico en alpha.
5. Test bandpowers relativos con suma razonable.
6. Test `compute_spectral_quality()` con escenarios clean/artifact/bad.
7. Recalcular una captura real con `validate_spectral_features.py`.
8. Regenerar figuras si cambian outputs.
9. Repetir benchmark Python/Linux si cambia coste o timing.
10. Comprobar que WebUI sigue recibiendo `features`, `spectral_quality` y `sonification`.

## 14. Relacion con futura version esencial/UML

En UML principal deben aparecer:

```text
EEGSignalProcessor.add_block_uV
ring buffer
compute_live_features
DSPCore.compute_features(multitaper)
SignalQuality / QualityGate
SonificationFeatureAdapter.update
```

Deben quedar fuera u ocultos:

```text
compute_online_features
spectrogramas offline
tools de validacion
generadores de figuras
```

## 15. Conclusion

El bloque DSP final-v4 convierte una ventana reciente de CH1 en features espectrales y de amplitud. Despues, el quality gate decide si esa ventana es fiable para sonificacion y el adaptador transforma esos rasgos en controles musicales normalizados.

La lectura correcta para el TFG es:

```text
no se pretende diagnosticar clinicamente EEG;
se usan rasgos espectrales y de amplitud para controlar una sonificacion MIDI en tiempo real;
el quality gate protege frente a artefactos y ventanas malas;
la validacion offline documenta lo ocurrido en capturas reales.
```



