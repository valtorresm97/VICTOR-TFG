# 03. Auditoria Python backend

## Estructura principal

| Archivo | Responsabilidad | Estado |
| --- | --- | --- |
| `main.py` | Crea backend y WebUI, ejecuta `App.run(user_loop=loop)`. | Activo |
| `backend_service.py` | Orquestador de recepcion, buffer, DSP, quality, sonificacion, MIDI, LED y snapshots. | Activo |
| `receiver.py` | Handlers Bridge y cola de bloques EEG. | Activo |
| `eeg_signal_processor.py` | Ring buffer y acceso a DSP. | Activo |
| `dsp_core.py` | Analisis espectral puro de canal. | Activo |
| `spectral_quality.py` | Quality gate live. | Activo |
| `app_state.py` | Snapshot JSON atomico. | Activo |
| `capture_manager.py` | Capturas controladas por JSON desde CLI. | Activo |
| `web_server.py` | Web UI brick y rutas. | Activo |

No existe `python/dashboard.py` en esta rama; la UI esta implementada como WebUI HTML/CSS/JS en `assets/`.

## Entrada `eeg_block_uV`

`BackendService.__init__()` registra:

- `Bridge.provide("linux_started", self.rx.linux_started)`
- `Bridge.provide("eeg_block_uV", self.rx.eeg_block_uV)`

`receiver.eeg_block_uV()` recibe:

```text
block_idx, first_sample_idx, sample_count,
sample_count * (status, ch1_uV, ch2_uV, ch3_uV, ch4_uV)
```

Valida:

- `sample_count > 0` y `<= 8`,
- indices no negativos,
- longitud exacta del payload,
- continuidad de `block_idx`,
- continuidad de `sample_idx`,
- prefijo status `0xC00000`.

Luego encola un `BlockItem` en una `deque(maxlen=512)`. Si la cola se llena, descarta el bloque mas antiguo y contabiliza drops en bloques y frames.

## Drenado hacia DSP

`BackendService.step()` llama:

```python
self.rx.drain_blocks_to_processor(self.proc, max_blocks=16, block_sink=self.capture_manager.add_block)
```

Cada bloque se pasa a:

- `EEGSignalProcessor.add_block_uV(samples)`, que convierte uV a V y escribe ring buffer.
- `CaptureManager.add_block(...)`, si hay captura activa.

## Calculo de features

Constantes activas:

| Constante | Valor | Comentario |
| --- | --- | --- |
| `FS_HZ` | `250` | Debe coincidir con firmware. |
| `NUM_CH` | `4` | Contrato ADS1299-4. |
| `FEATURE_WINDOW_SEC` | `4.0` | 1000 muestras. |
| `FEATURE_HOP_SAMPLES` | `64` | ~256 ms. |
| `SNAPSHOT_PUBLISH_PERIOD_SEC` | `0.2` | UI fluida. |
| `DISK_PUBLISH_PERIOD_SEC` | `1.0` | Snapshot en disco. |

Cuando hay ventana lista, `compute_live_features(channel_idx=0, psd_method="multitaper")` calcula features ligeras. Luego:

1. `compute_quality_diagnostics()` mide RMS, ptp, 50 Hz, saturacion, waveform.
2. `_build_quality_rx_delta_metrics()` calcula deltas de errores RX desde ultima ventana.
3. `compute_spectral_quality()` produce `score/state/gate_factor`.
4. `SonificationFeatureAdapter.update()` genera controles musicales.

## Snapshot

`_build_snapshot()` publica claves principales:

- `config`
- `status`
- `rx`
- `features`
- `diagnostics`
- `spectral_quality`
- `capture`
- `sonification`
- `music`
- `midi`
- `led_matrix`
- `performance`
- `errors`

La Web UI depende directamente de esos nombres.

## Captura

`capture_manager.py` permite a `python/tools/capture_eeg_quality.py` solicitar una captura real escribiendo `state/capture_request.json`. El backend graba `captures/<timestamp>_<condition>/eeg_timeseries.csv` y `metadata.json`.

Campos CSV:

- `t_capture_sec`
- `timestamp_unix`
- `block_idx`
- `sample_idx`
- `sample_in_block`
- `status`
- `ch1_uV` ... `ch4_uV`

## MIDI y LED desde backend

MIDI:

- `MIDI_LIVE_ENABLED = EEG_MIDI_LIVE_ENABLED` con default `False`.
- Si esta desactivado, el scheduler sigue generando y el transporte cuenta `dropped_events_total`.
- `send_panic()` existe y se llama en `stop()`, pero no hay boton UI.

LED:

- `LedMatrixConfig.from_env()` lee `EEG_LED_MATRIX_*`, default desactivado.
- `_maybe_update_led_matrix()` solo corre si `self.led_matrix_transport.enabled`.
- Usa `recent_notes`, no un pipeline musical paralelo.

## Errores posibles

| Subsistema | Error | Mitigacion actual | Riesgo restante |
| --- | --- | --- | --- |
| Receiver | Bloque malformado | Contador y drop | UI solo muestra algunos totales. |
| Receiver | Status invalido | Contador y quality penalty | No detiene adquisicion. |
| Buffer | Shape incorrecta | Warning y drop | Sin alarma UI directa. |
| DSP | Excepcion en features | Log exception | Mantiene ultimas features. |
| MIDI | Bridge falla | `failed_events_total` | Sin panic UI manual. |
| LED | Bridge/frame falla | `failed_frames_total`, `last_error` | UI no muestra panel LED dedicado. |
| Captura | App no corre | CLI timeout | Usuario debe arrancar App Lab. |
