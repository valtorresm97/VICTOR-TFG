# 04. DSP y procesamiento EEG funcion por funcion - final-v4

Rama auditada originalmente: `eliminacion-redudancias`.

Actualizacion final-v3: contrastada contra `codex/direct-band-sonification` y `firmware-final-v3`.

Re-auditoria final-v4: revisada contra codigo real en `firmware-final-v4` desde la rama documental `refactor/essential-eeg-midi-plan`.

Objetivo de esta re-auditoria: documentar el procesamiento EEG Python real, la relacion entre firmware filtrado, ring buffer, `DSPCore`, `spectral_quality`, benchmarks y herramientas offline, sin modificar runtime.

## 1. Responsabilidad global

En final-v4, el firmware ya entrega senal filtrada en microvoltios. Python no aplica filtros EEG principales adicionales en el loop live. La cadena DSP Python hace:

```text
eeg_block_uV desde receiver
  -> EEGSignalProcessor.add_block_uV()
  -> conversion uV a V
  -> ring buffer multicanal
  -> ventana reciente CH1
  -> DSPCore.compute_features(psd_method="multitaper")
  -> bandpowers / peaks / RMS
  -> compute_quality_diagnostics()
  -> compute_spectral_quality()
  -> SonificationFeatureAdapter
```

Separacion importante:

- `DSPCore` calcula espectro, PSD, bandpowers, RMS, picos y espectrograma.
- `EEGSignalProcessor` gestiona buffer multicanal y llama a `DSPCore`.
- `spectral_quality.py` decide si una ventana es usable musicalmente.
- `sonification_features.py` transforma features EEG en controles musicales.
- Las tools offline reutilizan `DSPCore` y `compute_spectral_quality()` para mantener comparabilidad con el backend live.

Criterio para simplificacion futura:

- `compute_live_features()` es la ruta live principal.
- `compute_online_features()` queda fuera del UML principal y no debe usarse como ruta de la version esencial salvo que se justifique expresamente.
- `compute_quality_diagnostics()` y `compute_spectral_quality()` si deben conservarse, pero representados como un bloque compacto de `SignalQuality` o `QualityGate` para no sobrecargar los diagramas.

## 2. Parametros activos final-v4

| Parametro | Valor | Archivo | Uso | Riesgo si cambia |
| --- | ---: | --- | --- | --- |
| `FS_HZ` | 250 Hz | `eeg_contract.py` | Buffer, ventanas, PSD y eje temporal | Requiere repetir benchmarks/capturas. |
| `NUM_CH` | 4 | `eeg_contract.py` | Ring buffer multicanal | Contrato firmware/Python. |
| `FEATURE_WINDOW_SEC` | 4.0 s | `backend_service.py` | Ventana live de features | Cambia resolucion espectral y latencia. |
| `FEATURE_HOP_SAMPLES` | 64 | `backend_service.py` | Cadencia live | Presupuesto actual = 256 ms. |
| Buffer backend | 10.0 s | `backend_service.py` | Historial reciente | Mayor RAM si sube; menos margen si baja. |
| PSD live | multitaper | `backend_service.py`, `DSPCore` | Features dashboard/sonificacion | Cambia resultados si se usa Welch/periodogram. |
| `DSPCore.window_sec` | 4.0 s | `EEGSignalProcessor` | Ventana PSD principal | Debe coincidir con features. |
| Ventana | Hann por defecto | `EEGSignalProcessor`, `DSPCore` | Welch/periodogram | Menor relevancia en multitaper. |
| Bandas | delta 0.5-4, theta 4-8, alpha 8-13, beta 13-30, gamma 30-50 | `DSPCore` | Bandpowers y sonificacion | Cambia TFG y reportes. |
| Multitaper `mt_nw` | 2.5 | `DSPCore` | DPSS | Cambia suavizado/resolucion. |
| Tapers | `2*NW-1 = 4` por defecto | `DSPCore` | Promedio PSD | Cambia coste y PSD. |
| Outlier zscore | 5.0 | `DSPCore` | Preprocesado robusto | Puede suavizar transitorios reales/artefactos. |
| Quality gate clean | >= 0.85 | `spectral_quality.py` | Sonificacion plena | Umbral empirico. |
| Quality gate bad | < 0.50 | `spectral_quality.py` | Bloquea nueva sonificacion | Umbral empirico. |

## 3. Unidades y flujo de datos

| Etapa | Unidad | Comentario |
| --- | --- | --- |
| Firmware despues de filtros | microvoltios enteros | Payload `eeg_block_uV`. |
| `receiver.py` | microvoltios enteros | No convierte unidades, solo valida y encola. |
| `EEGSignalProcessor.add_block_uV()` | microvoltios -> voltios | Multiplica por `1e-6`. |
| Ring buffer Python | voltios `float32` | Shape `(num_channels, buffer_size)`. |
| `DSPCore` | voltios `float` | RMS y PSD en unidades SI relativas a V. |
| Diagnostico UI/calidad | microvoltios | Convierte ventana V a uV para RMS/PTP/percentiles. |
| Sonificacion | normalizado 0..1 | Derivado de features y quality gate. |

Regla critica: no mezclar uV y V. `add_sample()` espera voltios; `add_block_uV()` espera microvoltios.

## 4. Funciones DSP re-auditadas

| Archivo | Funcion | Entrada | Salida | Formula/algoritmo | Estado | Riesgo cientifico/tecnico | Test recomendado |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `dsp_core.py` | `DSPCore.__init__()` | fs, ventana, bandas, multitaper, outliers | Objeto | Configura `window_samples`, bandas, DPSS params | `_mt_cache`, flags debug | Cambiar `mt_nw`/bandas invalida comparabilidad | Test seno conocido y captura real. |
| `dsp_core.py` | `get_freq_bin_size()` | n_samples opcional | Hz/bin | `fs/N` | Ninguno | Bajo | N=1000 -> 0.25 Hz. |
| `dsp_core.py` | `_make_window()` | n | array | `signal.get_window` | Ninguno | Tipo ventana cambia leakage | Test longitud/tipo. |
| `dsp_core.py` | `_detect_clipping()` | array | bool | Fraccion de muestras en min/max | `last_clipping_detected` via preprocess | Heuristico; false positives en senal cuantizada/plana | Test clipping artificial. |
| `dsp_core.py` | `preprocess()` | x, detrend, outliers | array | float, detrend lineal, MAD zscore, interpolacion/winsor | `last_clipping_detected`, `last_outlier_ratio` | Puede alterar transitorios; no usar para ocultar artefactos | Test outlier aislado y mandibula. |
| `dsp_core.py` | `compute_psd()` | x, method, nperseg, overlap | freqs, pxx | periodogram/Welch/multitaper | Puede actualizar preprocess flags | Metodo no soportado lanza error | Comparar metodos y coste. |
| `dsp_core.py` | `_get_mt_cache()` | n_win | freqs,tapers | `windows.dpss`, `rfftfreq` | `_mt_cache` | Cache por longitud; si fs cambia requiere objeto nuevo | Test cache hit. |
| `dsp_core.py` | `_compute_psd_multitaper()` | x | freqs, pxx | DPSS tapers, rFFT, promedio PSD | Usa cache | Normalizacion sensible; no cambiar sin justificar | Seno 10 Hz, ruido blanco, captura real. |
| `dsp_core.py` | `compute_bandpower()` | freqs, pxx, relative | dict | Integracion trapezoidal por bandas | Ninguno | Bordes inclusivos pueden compartir bins de frontera | Test PSD plana. |
| `dsp_core.py` | `compute_features()` | x, flags | dict | Preprocess una vez, RMS, PSD, band_abs escalada a potencia temporal, band_rel, picos | Flags preprocess | Escalado band_abs aproxima potencia temporal; cambiarlo afecta reportes | Test feature shape y suma relativa. |
| `dsp_core.py` | `compute_spectrogram()` | x, method, window/step | times,freqs,Sxx | Ventanas deslizantes, PSD por segmento, log opcional | Preprocess flags | Coste CPU alto; preferir offline/figuras | Test dimensiones. |
| `dsp_core.py` | `compute_spectral_stability()` | x,fmin,fmax | float 0..1/nan | Entropia espectral normalizada invertida | Ninguno | Interpretacion depende de banda y ruido | Test ruido vs seno. |
| `eeg_signal_processor.py` | `EEGSignalProcessor.__init__()` | fs,num_channels,buffer,psd params | objeto | Crea ring buffer `(ch, samples)` y `DSPCore` | buffer/write_pos/valid | Buffer pequeno pierde historia; grande consume RAM | Smoke. |
| `eeg_signal_processor.py` | `_write_block_volts()` | array V `(n,ch)` | n escritos | Escritura circular con wrap | buffer/write_pos/valid/total | Shape incorrecta descarta bloque | Test wrap. |
| `eeg_signal_processor.py` | `_get_recent_count()` | window_sec | n | Min(valid, window*fs) | Ninguno | Bajo | Test. |
| `eeg_signal_processor.py` | `_extract_recent_channel()` | ch,n | array | Copia contigua desde ring | Ninguno | No valida canal; llamadores deben controlar | Test wrap. |
| `eeg_signal_processor.py` | `_extract_recent_matrix()` | n | matrix | Copia multicanal desde ring | Ninguno | Bajo | Test wrap. |
| `eeg_signal_processor.py` | `add_sample()` | voltages V | n | Valida shape y escribe | buffer | Ruta legacy/sencilla; entrada en V no uV | Test 4 canales. |
| `eeg_signal_processor.py` | `add_block_uV()` | iterable uV | n | Convierte uV a V y escribe | buffer | Critico: unidad uV->V | Test 1000 uV -> 0.001 V. |
| `eeg_signal_processor.py` | `get_recent_multichannel_window()` | window | matrix | Ventana reciente todos canales | Ninguno | En modo 5 CH2-CH4 no son EEG activo | Test. |
| `eeg_signal_processor.py` | `available_samples/seconds` | ch opcional | int/float | Lee `valid_samples` | Ninguno | `channel_idx` ignorado por diseno | Test. |
| `eeg_signal_processor.py` | `is_window_ready()` | window | bool | `valid_samples >= needed` | Ninguno | Critico para cadencia DSP | Test. |
| `eeg_signal_processor.py` | `get_buffer_status()` | window | dict | Estado ring | Ninguno | Cambiar claves rompe snapshot | Snapshot test. |
| `eeg_signal_processor.py` | `get_signal_window()` | ch, window | array V | Lee senal sin filtrado Python | Ninguno | Canal 0/CH1 es principal final-v4 | Test unidad. |
| `eeg_signal_processor.py` | `get_power_spectrum()` | ch,window,method | freqs,pxx | DSPCore PSD | DSP flags | Bajo/medio | Seno. |
| `eeg_signal_processor.py` | `get_band_power()` | ch,window,method | dict | PSD + bandpower abs | Ninguno | Bajo | Test. |
| `eeg_signal_processor.py` | `get_rms_amplitude()` | ch,window | float V | RMS temporal | Ninguno | Unidad V | Test. |
| `eeg_signal_processor.py` | `compute_features()` | ch,window,method | dict rico | Incluye spectrum/peaks/band_rel | DSP flags | Coste mayor; usar offline si no se necesita espectro | Offline test. |
| `eeg_signal_processor.py` | `compute_live_features()` | ch,window,method | dict compacto | Sin freqs/psd, con picos | DSP flags | Ruta live principal benchmarkeada | Test shape + benchmark. |
| `eeg_signal_processor.py` | `compute_online_features()` | ch,window | dict minimo | Multitaper sin picos/spectrum | DSP flags | Ruta secundaria. No usar ni representar en la version esencial/UML principal | No priorizar salvo compatibilidad. |
| `eeg_signal_processor.py` | `compute_quality_diagnostics()` | ch, window, waveform | dict | RMS/ptp/percentiles/saturacion/jumps/50Hz/waveform | DSP PSD interna | Heuristicas dependen de uV, LSB y filtros MCU | Test captura sintetica/real. |
| `eeg_signal_processor.py` | `get_spectrogram()` | ch,window,step,method | times,freqs,Sxx | DSP spectrogram | DSP flags | Coste alto; uso offline/figuras | Offline. |
| `spectral_quality.py` | `SpectralQuality.to_dict()` | self | dict | `asdict` | Ninguno | Bajo | Test. |
| `spectral_quality.py` | `_safe_float()` | any | float | finite guard | Ninguno | Bajo | Test NaN. |
| `spectral_quality.py` | `_clamp01()` | float | 0..1 | Clamp | Ninguno | Bajo | Test. |
| `spectral_quality.py` | `_penalty_ramp()` | value,start,stop,max | penalty | Rampa lineal | Ninguno | Umbrales empiricos | Test bordes. |
| `spectral_quality.py` | `compute_spectral_quality()` | features, diagnostics, rx_metrics, window_ready | `SpectralQuality` | Suma penalizaciones y asigna state/gate | Ninguno | Critico para congelar o permitir sonificacion | Test escenarios clean/bad/artifact. |

## 5. Quality gate final-v4

Estados actuales:

| Estado | Score | Gate | Uso |
| --- | ---: | ---: | --- |
| `clean` | `>= 0.85` | 1.0 | Usar features normalmente. |
| `usable_with_caution` | `>= 0.70` | 0.75 | Atenuacion leve. |
| `artifact_suspected` | `>= 0.50` | 0.35 | Atenuacion fuerte. |
| `bad` | `< 0.50` | 0.0 | No generar nueva sonificacion. |

Entradas sensibles:

- errores RX recientes: invalid status, lost frames/blocks, queue drops, malformed blocks;
- RMS uV;
- pico-pico uV;
- saturacion ADC estimada;
- flatline;
- saltos abruptos;
- ratio 50 Hz;
- gamma relativa alta;
- delta+theta alta con RMS elevado.

Regla de arquitectura:

```text
spectral_quality no cambia PSD, bandas ni filtros.
Solo decide si una ventana es fiable para mover la sonificacion.
```

Por eso no debe integrarse dentro de `DSPCore` en una simplificacion futura. Debe permanecer como capa de decision posterior al calculo espectral.

Decision para la version esencial:

```text
compute_quality_diagnostics()
  -> compute_spectral_quality()
```

se conserva como bloque esencial de calidad de senal. En diagramas puede aparecer compactado como:

```text
SignalQuality / QualityGate
```

Motivo: sin `compute_quality_diagnostics()`, el quality gate perderia medidas directas de amplitud y artefactos como RMS, pico-pico, saturacion, flatline, saltos y 50 Hz. Sin `compute_spectral_quality()`, el sistema volveria a convertir ventanas contaminadas en cambios musicales sin barrera explicita.

## 6. Relacion con benchmarks final-v4

El benchmark Python/Linux mide funciones criticas sobre captura real. La funcion mas importante para DSP live es:

```text
EEGSignalProcessor.compute_live_features(channel_idx=0, window_sec=4.0, psd_method="multitaper")
```

Resultado documentado en final-v4:

| Metrica | Resultado |
| --- | ---: |
| mediana `compute_live_features` | 5.2158 ms |
| p95 | 6.4103 ms |
| maximo | 6.9831 ms |
| presupuesto por hop | 256 ms |

Interpretacion:

```text
El DSP Python esta muy por debajo del presupuesto temporal de 256 ms.
No es el cuello de botella temporal principal.
```

Cualquier cambio en `DSPCore`, `compute_live_features`, bandas, ventana o multitaper exige repetir el benchmark sobre captura real.

## 7. Relacion con capturas finales

La sesion final `s01_20260528` se analiza principalmente con CH1:

```text
ADS_DIAGNOSTIC_MODE=5
montage=ear_eeg_ch1_only
ADS_MODE=bias_ch1_only_loff_off
```

Consecuencias:

- `channel_idx=0` es el canal principal para features, quality y sonificacion.
- CH2-CH4 existen por contrato y CSV, pero no deben interpretarse como EEG activo en la sesion final.
- Las figuras y reportajes usan bandpowers, quality gate y controles de sonificacion derivados de CH1.
- La sesion valida integracion tecnica y trazabilidad, no EEG clinico limpio.

## 8. Tools offline que reutilizan DSP

| Tool | Uso DSP | Estado final-v4 |
| --- | --- | --- |
| `python/tools/analyze_eeg_capture.py` | Analisis de captura, calidad, bandas, reportes | Offline; conserva trazabilidad de capturas. |
| `python/tools/validate_spectral_features.py` | Ventanas, bandpowers, quality gate y sonification features | Offline; compatible con nombres nuevos y alias legacy. |
| `python/tools/build_final_capture_docs_matplotlib.py` | Figuras/reportajes finales | Offline; no runtime. |
| `python/tools/build_capture06_enhanced_figures.py` | Espectrogramas/figuras enhanced captura 06 | Offline; no runtime. |
| `benchmarks/benchmark_real_capture.py` | Reconstruye bloques y mide DSP sobre captura real | Benchmark final; no runtime live. |

No borrar estas tools durante la version esencial: pueden quedar fuera del UML principal, pero son parte de la evidencia TFG.

## 9. Hallazgos para simplificacion futura

| Hallazgo | Impacto | Recomendacion futura |
| --- | --- | --- |
| `DSPCore` es la fuente unica de multitaper | Bien para evitar redundancias | Mantenerlo como clase unica de PSD/features. |
| `EEGSignalProcessor` mezcla buffer y acceso a features | Aceptable, pero puede separarse logicamente | UML: `RingBufferEEG` + `FeatureExtractor` sin mover codigo inicialmente. |
| `compute_features()` y `compute_live_features()` comparten logica | Bien, pero conviene documentar cual es live | Mantener `compute_live_features` como ruta benchmarkeada. |
| `compute_online_features()` es ruta secundaria/no principal | No aporta a la version esencial y puede confundir | Excluir del UML principal y no usar en la simplificacion salvo compatibilidad temporal. |
| `compute_quality_diagnostics()` es diagnostico, pero alimenta la seguridad de sonificacion | Si se elimina, el quality gate pierde amplitud/artefactos | Mantenerlo como parte compacta de `SignalQuality`, al menos con campos esenciales. |
| `compute_spectral_quality()` es la barrera contra artefactos | Sin ella la musica responde a ventanas malas | Mantener como `QualityGate` esencial, separado de `DSPCore`. |
| Preprocess interpola outliers | Puede ocultar transitorios si se abusa | No cambiar sin comparar capturas reales. |
| Bandpowers relativos dependen de la suma de bandas, no de toda potencia 0-Nyquist | Coherente con sonificacion pero debe explicarse | Mantener para comparabilidad. |
| Quality gate esta separado de DSP | Buena arquitectura | No fusionarlo dentro de `DSPCore`. |
| `scipy` es dependencia critica | App Lab/venv debe soportarla | No refactorizar sin validar entorno UNO Q. |

## 10. Riesgos principales

- Cambiar bandas invalida comparabilidad con reportes y controles musicales.
- Cambiar ventana de 4 s altera resolucion y latencia.
- Cambiar hop de 64 muestras altera presupuesto de 256 ms.
- Cambiar multitaper por Welch/periodogram cambia features y figuras.
- Cambiar unidades uV/V rompe RMS, quality score y sonificacion.
- Integrar quality gate dentro de `DSPCore` mezcla ciencia de seÃ±al con decision musical.
- Eliminar `compute_quality_diagnostics()` sin sustituto elimina indicadores de artefactos importantes.
- Eliminar `compute_spectral_quality()` elimina la barrera que evita sonificar ventanas malas.
- Interpretar CH2-CH4 como EEG activo en modo 5 seria incorrecto.
- Usar resultados sinteticos como evidencia final del TFG no es valido.

## 11. Pruebas minimas antes de aceptar cambios DSP

No aplicar cambios DSP en esta fase documental. Si en el futuro se modifica DSP:

1. `python3 -m py_compile python/dsp_core.py python/eeg_signal_processor.py python/spectral_quality.py python/sonification_features.py`.
2. Test de unidad uV->V: 1000 uV -> 0.001 V.
3. Test ring buffer con wrap.
4. Test PSD seno 10 Hz con pico en alpha.
5. Test bandpowers suma relativa â‰ˆ 1 cuando hay potencia.
6. Test `compute_spectral_quality()` para escenarios clean/bad/artifact.
7. Recalcular una captura real con `validate_spectral_features.py`.
8. Regenerar reportes/figuras si cambia el resultado.
9. Repetir benchmark Python/Linux sobre captura real.
10. Confirmar que la WebUI sigue recibiendo `features`, `spectral_quality` y `sonification`.

## 12. Recomendacion para version esencial UML

UML principal:

```text
EEGReceiver
  -> EEGSignalProcessor
       -> ring buffer multicanal
       -> get_signal_window(CH1)
       -> compute_live_features()
  -> DSPCore
       -> preprocess()
       -> compute_psd(multitaper)
       -> compute_bandpower()
       -> compute_features()
  -> SignalQuality / QualityGate
       -> compute_quality_diagnostics()
       -> compute_spectral_quality()
  -> SonificationFeatureAdapter
```

UML lateral/offline:

```text
analyze_eeg_capture.py
validate_spectral_features.py
build_final_capture_docs_matplotlib.py
build_capture06_enhanced_figures.py
benchmark_real_capture.py
```

Excluido del UML principal:

```text
compute_online_features()
```

No mover codigo todavia. Primero crear tests de contrato y diagramas logicos. El primer refactor seguro seria separar en documentacion las responsabilidades de buffer, extractor de features y quality gate, sin cambiar imports ni clases reales.





