# 04. DSP y procesamiento EEG funcion por funcion

## Responsabilidad global

El firmware ya entrega senal filtrada en microvoltios. Python convierte a voltios, mantiene un ring buffer y calcula features espectrales. `DSPCore` es la fuente unica de PSD multitaper live/offline tras la eliminacion de redundancias.

## Parametros activos

| Parametro | Valor | Archivo | Uso |
| --- | --- | --- | --- |
| `FS_HZ` | 250 Hz | `eeg_contract.py` | Buffer, ventanas, PSD. |
| Ventana features | 4.0 s | `backend_service.py` | 1000 muestras. |
| Hop features | 64 muestras | `backend_service.py` | Cadencia live. |
| PSD live | multitaper | `backend_service.py`, `DSPCore` | Features dashboard/sonificacion. |
| Bandas | delta 0.5-4, theta 4-8, alpha 8-13, beta 13-30, gamma 30-50 | `DSPCore` | Bandpowers. |

## Funciones DSP

| Archivo | Funcion | Entrada | Salida | Formula/algoritmo | Estado | Riesgo cientifico/tecnico | Test recomendado |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `dsp_core.py` | `DSPCore.__init__()` | fs, ventana, bandas, multitaper, outliers | Objeto | Configura window_samples, bandas, DPSS params | Cache DPSS y ultimos flags | Cambiar `mt_nw` altera PSD y validaciones | Test seno conocido. |
| `dsp_core.py` | `get_freq_bin_size()` | n_samples opcional | Hz/bin | `fs/N` | Ninguno | Bajo | N=1000 -> 0.25 Hz. |
| `dsp_core.py` | `_make_window()` | n | array | `signal.get_window` | Ninguno | Tipo ventana cambia leakage | Test longitud. |
| `dsp_core.py` | `_detect_clipping()` | array | bool | Cuenta muestras en min/max | `last_clipping_detected` indirecto | Heuristico puede false positive en senal plana | Test clipping artificial. |
| `dsp_core.py` | `preprocess()` | x,detrend,outliers | array | float, detrend lineal, MAD zscore, interpolacion | `last_clipping_detected`, `last_outlier_ratio` | Interpolacion altera transitorios | Test outlier aislado. |
| `dsp_core.py` | `compute_psd()` | x, method, nperseg, overlap | freqs, pxx | periodogram/Welch/multitaper | Puede actualizar preprocess flags | Metodo no soportado lanza error | Comparar metodos. |
| `dsp_core.py` | `_get_mt_cache()` | n_win | freqs,tapers | `windows.dpss`, `rfftfreq` | `_mt_cache` | Cache por longitud; si fs cambia requiere objeto nuevo | Test cache hit. |
| `dsp_core.py` | `_compute_psd_multitaper()` | x | freqs, pxx | DPSS tapers, rFFT, promedio PSD | Usa cache | Normalizacion cientifica sensible | Seno 10 Hz y ruido. |
| `dsp_core.py` | `compute_bandpower()` | freqs, pxx, relative | dict | Integracion trapezoidal por bandas | Ninguno | Bordes inclusivos pueden contar bins comunes | Test PSD plana. |
| `dsp_core.py` | `compute_features()` | x, flags | dict | Preprocess una vez, RMS, PSD, band_abs escalada a potencia temporal, band_rel, picos | Flags preprocess | Escalado band_abs aproxima potencia de tiempo | Test feature shape. |
| `dsp_core.py` | `compute_spectrogram()` | x, method, window/step | times,freqs,Sxx | Ventanas deslizantes, PSD por segmento, log opcional | Preprocess flags | Coste CPU alto offline/UI | Test dimensiones. |
| `dsp_core.py` | `compute_spectral_stability()` | x,fmin,fmax | float 0..1/nan | Entropia espectral normalizada invertida | Ninguno | Interpretacion depende de banda | Test ruido vs seno. |
| `eeg_signal_processor.py` | `EEGSignalProcessor.__init__()` | fs,num_channels,buffer,psd params | objeto | Crea ring buffer `(ch, samples)` | buffer/write_pos/valid | Buffer pequeno pierde historia; grande consume RAM | Smoke. |
| `eeg_signal_processor.py` | `_write_block_volts()` | array V `(n,ch)` | n escritos | Escritura circular con wrap | buffer/write_pos/valid/total | Shape incorrecta descarta bloque | Test wrap. |
| `eeg_signal_processor.py` | `_get_recent_count()` | window_sec | n | Min(valid, window*fs) | Ninguno | Bajo | Test. |
| `eeg_signal_processor.py` | `_extract_recent_channel()` | ch,n | array | Copia contigua desde ring | Ninguno | Indice canal no validado aqui | Test wrap. |
| `eeg_signal_processor.py` | `_extract_recent_matrix()` | n | matrix | Copia multicanal desde ring | Ninguno | Bajo | Test wrap. |
| `eeg_signal_processor.py` | `add_sample()` | voltages V | n | Valida shape y escribe | buffer | Ruta legacy; entrada en V no uV | Test 4 canales. |
| `eeg_signal_processor.py` | `add_block_uV()` | iterable uV | n | Convierte uV a V y escribe | buffer | Critico: unidad uV->V | Test 1000 uV -> 0.001 V. |
| `eeg_signal_processor.py` | `_get_channel_array()` | ch, window | array | Wrapper recientes | Ninguno | Bajo | Test. |
| `eeg_signal_processor.py` | `get_recent_multichannel_window()` | window | matrix | Ventana reciente todos canales | Ninguno | Bajo | Test. |
| `eeg_signal_processor.py` | `available_samples/seconds` | ch opcional | int/float | Lee `valid_samples` | Ninguno | ch ignorado por diseno | Bajo | Test. |
| `eeg_signal_processor.py` | `min_available_samples/seconds` | Ninguna | int/float | Lee `valid_samples` | Ninguno | Bajo | Test. |
| `eeg_signal_processor.py` | `is_window_ready()` | window | bool | `valid_samples >= needed` | Ninguno | Critico para DSP cadence | Test. |
| `eeg_signal_processor.py` | `get_buffer_status()` | window | dict | Estado ring | Ninguno | Cambiar claves rompe diagnostico | Snapshot test. |
| `eeg_signal_processor.py` | `get_signal_window()` | ch, window | array V | Lee senal sin filtrar en Python | Ninguno | Critico para DSP | Test unidad. |
| `eeg_signal_processor.py` | `get_power_spectrum()` | ch,window,method | freqs,pxx | DSPCore PSD | DSP flags | Bajo/medio | Seno. |
| `eeg_signal_processor.py` | `get_band_power()` | ch,window,method | dict | PSD + bandpower abs | Ninguno | Bajo | Test. |
| `eeg_signal_processor.py` | `get_rms_amplitude()` | ch,window | float V | RMS temporal | Ninguno | Unidad V | Test. |
| `eeg_signal_processor.py` | `compute_features()` | ch,window,method | dict rico | Incluye spectrum/peaks/band_rel | DSP flags | Coste mayor | Offline test. |
| `eeg_signal_processor.py` | `compute_live_features()` | ch,window,method | dict compacto | Sin freqs/psd, con picos | DSP flags | Ruta live principal | Test shape. |
| `eeg_signal_processor.py` | `compute_online_features()` | ch,window | dict minimo | Multitaper sin picos/spectrum | DSP flags | No usada centralmente | Test. |
| `eeg_signal_processor.py` | `compute_quality_diagnostics()` | ch, window, waveform | dict | RMS/ptp/percentiles/saturacion/jumps/50Hz/waveform | DSP flags por PSD | Heuristicas dependen de uV y LSB | Test captura sintetica. |
| `eeg_signal_processor.py` | `get_spectrogram()` | ch,window,step,method | times,freqs,Sxx | DSP spectrogram | DSP flags | Coste alto | Offline. |
| `spectral_quality.py` | `SpectralQuality.to_dict()` | self | dict | `asdict` | Ninguno | Bajo | Test. |
| `spectral_quality.py` | `_safe_float()` | any | float | finite guard | Ninguno | Bajo | Test NaN. |
| `spectral_quality.py` | `_clamp01()` | float | 0..1 | Clamp | Ninguno | Bajo | Test. |
| `spectral_quality.py` | `_penalty_ramp()` | value,start,stop,max | penalty | Rampa lineal | Ninguno | Umbrales empiricos | Test bordes. |
| `spectral_quality.py` | `compute_spectral_quality()` | features, diagnostics, rx_metrics, window_ready | `SpectralQuality` | Suma penalizaciones y asigna estado/gate | Ninguno | Critico para congelar o permitir sonificacion | Test escenarios clean/bad. |

## Quality gate

Estados:

- `clean`: score >= 0.85, gate 1.0.
- `usable_with_caution`: score >= 0.70, gate 0.75.
- `artifact_suspected`: score >= 0.50, gate 0.35.
- `bad`: score < 0.50, gate 0.0 y `freeze_recommended=True`.

Entradas sensibles: errores RX recientes, RMS uV, ptp uV, `line_50_ratio`, saturation, flatline, abrupt jumps, gamma relativa y slow power con RMS alto.

## Riesgos para refactor

- No duplicar multitaper fuera de `DSPCore`.
- No cambiar unidades: `EEGSignalProcessor` almacena V, UI diagnostico convierte a uV.
- No mover quality gate dentro de DSPCore; es una capa de decision, no calculo espectral.
- Cualquier cambio en bandas/ventana/hop invalida comparabilidad con reports previos.
