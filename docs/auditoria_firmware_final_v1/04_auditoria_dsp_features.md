# 04. Auditoria DSP y features

## Pipeline DSP live

```text
receiver.py
  ↓ bloques uV
EEGSignalProcessor.add_block_uV()
  ↓ convierte uV a V
ring buffer multicanal 10 s
  ↓ ventana CH1 4 s
DSPCore.compute_features(psd_method="multitaper")
  ↓
bandpower_abs, bandpower_rel, peaks, rms
  ↓
compute_quality_diagnostics()
  ↓
compute_spectral_quality()
  ↓
SonificationFeatureAdapter.update()
```

La senal llega ya filtrada desde el MCU: HP 0.5 Hz, notch 50 Hz, LP 40 Hz. Python no aplica filtros EEG principales adicionales; `DSPCore.preprocess()` hace detrend lineal y correccion robusta de outliers antes de PSD.

## Parametros

| Parametro | Valor | Archivo |
| --- | --- | --- |
| Frecuencia | 250 Hz | `backend_service.py`, `eeg_signal_processor.py` |
| Ventana features | 4.0 s | `backend_service.py` |
| Hop features | 64 muestras | `backend_service.py` |
| Buffer live | 10 s | `backend_service.py` |
| Metodo PSD live | multitaper | `backend_service.py` |
| Multitaper NW | 2.5 | `dsp_core.py` |
| Tapers | `2*NW-1 = 4` | `dsp_core.py` |
| Bandas | delta 0.5-4, theta 4-8, alpha 8-13, beta 13-30, gamma 30-50 | `dsp_core.py` |

## Features espectrales

| Feature | Origen | Archivo | Formula/idea | Uso | Riesgo | Estado |
| --- | --- | --- | --- | --- | --- | --- |
| `rms` | Senal preprocesada | `dsp_core.py` | `sqrt(mean(x^2))` en V | Actividad/diagnostico | Sensible a artefactos | Activa |
| `bandpower_abs` | PSD | `dsp_core.py` | Integral por banda reescalada a potencia temporal | Validacion/offline y snapshot | No calibracion fisica absoluta definitiva | Activa |
| `bandpower_rel` | PSD | `dsp_core.py` | Banda / suma bandas | Sonificacion y UI | Cambia si filtros limitan gamma | Activa |
| `peak_freq` | PSD | `dsp_core.py` | Frecuencia de maximo global | Snapshot/registro | Puede saltar con ruido | Activa |
| `peak_alpha` | PSD | `dsp_core.py` | Maximo 8-13 Hz | Registro potencial | Necesita mas validacion | Activa |
| `peak_beta` | PSD | `dsp_core.py` | Maximo 13-30 Hz | Snapshot | EMG puede contaminar | Activa |
| `line_50_ratio` | PSD diagnostico | `eeg_signal_processor.py` | Potencia 49-51 / 1-50 Hz | Quality warnings | Notch puede ocultar parte | Activa |
| `spectral_quality.score` | Features + diagnostico + RX | `spectral_quality.py` | 1 - suma penalizaciones | Gate de sonificacion | Umbrales empiricos | Activa |
| `quality_gate` | Score | `spectral_quality.py` | clean 1.0, caution 0.75, artifact 0.35, bad 0 | Atenuacion musical | Puede ser conservador | Activa |
| `activity` | fast_power + RMS norm | `sonification_features.py` | `0.55*fast + 0.45*rms_norm` | Densidad/velocity | Artefactos suben RMS | Activa con gate |
| `calmness` | alpha/beta | `sonification_features.py` | `alpha*(1-beta/(alpha+beta))` | Estabilidad/calma | Alpha validada mejor en ear EEG | Activa |
| `tension` | beta/gamma | `sonification_features.py` | `0.8*beta_ratio + 0.2*gamma` | Armonia/sincopa | EMG/gamma no robusta | Activa con gate |
| `rhythmic_density` | activity+tension | `sonification_features.py` | `0.65*activity + 0.35*tension` | Cadencia ritmica | Movimiento genera notas | Activa con gate |
| `register` | peak alpha/freq | `sonification_features.py` | Frecuencia normalizada 0.5-30 Hz | Pitch register | Peak global salta | Activa |
| `harmonic_stability` | calmness/tension | `sonification_features.py` | `0.65*calm + 0.35*(1-tension)` | Acordes | Indirecto | Activa |
| `velocity_factor` | activity | `sonification_features.py` | `0.30 + 0.70*activity` | Velocity MIDI | Artefactos | Activa con gate |
| `note_probability` | density | `sonification_features.py` | `0.15 + 0.80*density` | Slots ritmicos | Cascadas por artefacto | Activa con gate |

## Quality gate

Estados:

| Estado | Score | Gate | Comportamiento |
| --- | --- | --- | --- |
| `clean` | `>=0.85` | `1.0` | Sonificacion plena. |
| `usable_with_caution` | `>=0.70` | `0.75` | Atenuacion ligera. |
| `artifact_suspected` | `>=0.50` | `0.35` | Atenuacion fuerte. |
| `bad` | `<0.50` | `0.0` | No valido para sonificacion. |

Penalizaciones actuales incluyen: ventana no lista, bandpowers no finitos, status ADS invalido, perdidas/drops/malformed, saturacion, flatline, RMS alto/bajo, pico-pico alto, ratio 50 Hz alto, saltos abruptos, gamma relativa alta y slow power con RMS alto.

## Controles de sonificacion

| Control | Archivo | Normalizacion | Suavizado | Histeresis | Riesgo |
| --- | --- | --- | --- | --- | --- |
| `activity` | `sonification_features.py` | [0,1] | EMA 0.18 | No | Artefactos de movimiento. |
| `calmness` | `sonification_features.py` | [0,1] | EMA 0.18 | No | Depende de alpha. |
| `tension` | `sonification_features.py` | [0,1] | EMA 0.18 | No | Beta/gamma EMG. |
| `rhythmic_density` | `sonification_features.py` | [0,1] | EMA 0.18 | Cadencia posterior | Puede generar exceso de notas. |
| `register` | `sonification_features.py` | [0,1] | EMA 0.18 | No | Peak inestable. |
| `harmonic_stability` | `sonification_features.py` | [0,1] | EMA 0.18 | Acorde posterior | Cambios lentos deseables. |
| `velocity_factor` | `sonification_features.py` | [0.3,1] | EMA 0.18 | No | Dinamica por artefacto. |
| `note_probability` | `sonification_features.py` | [0.15,0.95] | EMA 0.18 | Slots por probabilidad | Saturacion musical. |

## Ventanas malas y protecciones

- `score < 0.50` marca `valid=False`, lo que impide generar nuevo compas.
- El baseline RMS no se actualiza si `quality_score < 0.70`.
- El gate atenua actividad, tension, densidad, velocity, probabilidad y estabilidad.
- El receiver aporta errores RX por delta para que errores antiguos no silencien la musica permanentemente.
