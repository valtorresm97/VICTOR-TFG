# 08. Tools CLI funcion por funcion

## Resumen

Las tools son offline o auxiliares de App Lab. No forman parte del loop real-time salvo `capture_eeg_quality.py`, que escribe una solicitud que el backend vivo consume.

| Tool | Funcion | Entrada CLI | Archivos que lee | Archivos que escribe | Algoritmo | Estado | Riesgo | Ejemplo de uso |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `capture_eeg_quality.py` | Solicitar captura real | `--condition`, `--duration`, `--notes`, `--no-wait` | `state/capture_status.json` | `state/capture_request.json` | Escribe request atomico y espera estado | Activa | Requiere App Lab corriendo | `python3 python/tools/capture_eeg_quality.py --condition test --duration 30` |
| `analyze_eeg_capture.py` | Analizar una captura | `capture_dir` | `metadata.json`, `eeg_timeseries.csv` | `quality_report.json/md`, `spectral_summary.csv` | Metricas tiempo, PSD multitaper via DSPCore, diagnostico | Activa | Offline; puede tardar | `python3 python/tools/analyze_eeg_capture.py captures/...` |
| `compare_eeg_captures.py` | Comparar open/closed | open_dir closed_dir | Reports/capturas | Markdown/JSON comparacion | Ratios alpha y resumen | Activa | Depende de reports previos | `python3 python/tools/compare_eeg_captures.py open closed` |
| `validate_spectral_features.py` | Validar features ventana a ventana | path root/capture, `--channel`, `--window-sec`, `--hop-samples` | CSV captura, metadata | `windowed_bandpowers.csv`, `windowed_sonification_features.csv`, `psd_multitaper.csv`, reports | DSPCore multitaper + SpectralQuality + SonificationFeatureAdapter | Activa | Coste alto; genera artefactos | `python3 python/tools/validate_spectral_features.py captures` |
| `build_validation_docs.py` | Generar documentacion TFG | captures_dir/output_dir | Capturas, reports, git branches | `docs/validacion_tfg/**`, figures, tables | Agrega capturas, plots, tablas y docs | Activa/offline | Muy grande; puede requerir matplotlib/scipy | `python3 python/tools/build_validation_docs.py captures docs/validacion_tfg` |
| `set_ads_diagnostic_mode.py` | Cambiar modo ADS | mode int | `sketch/sketch.ino` | `sketch/sketch.ino` | Sustituye macro `ADS_DIAGNOSTIC_MODE` | Activa con cuidado | Modifica firmware critico | `python3 python/tools/set_ads_diagnostic_mode.py 5` |
| `test_led_matrix_visualizer.py` | Test manual LED | Ninguna | Modulo LED | Ninguno | Assertions sobre frame LED | Activa | No usa pytest, se ejecuta directo | `python3 python/tools/test_led_matrix_visualizer.py` |

## Funciones por tool

| Tool | Funcion | Entrada | Salida | Que hace | Riesgo |
| --- | --- | --- | --- | --- | --- |
| `capture_eeg_quality.py` | `_read_json` | path | dict | Lectura tolerante de status | Bajo |
| `capture_eeg_quality.py` | `parse_args` | argv | Namespace | Define CLI captura | Bajo |
| `capture_eeg_quality.py` | `main` | argv | exit code | Crea request id, escribe request, espera completed/stopped/error | Medio |
| `analyze_eeg_capture.py` | `_add_cached_site_packages` | Ninguna | Ninguna | Inserta site-packages App Lab si existe | Bajo |
| `analyze_eeg_capture.py` | `_load_metadata` | capture_dir | dict | Lee metadata | Bajo |
| `analyze_eeg_capture.py` | `_load_timeseries` | capture_dir | sample_idx,status,channels | Lee CSV EEG | Medio |
| `analyze_eeg_capture.py` | `_multitaper_psd` | x_uv,fs,nw | freqs,psd | Usa `DSPCore.compute_psd` | Medio |
| `analyze_eeg_capture.py` | `_bandpower/_peak_freq` | freqs,psd,banda | float/None | Integra y busca pico | Bajo |
| `analyze_eeg_capture.py` | `_windowed_metrics` | x,fs | dict | Resume ventanas 2 s | Medio |
| `analyze_eeg_capture.py` | `_channel_metrics` | x,sample_idx,fs | dict | Metricas amplitud, PSD, bandas, 50 Hz | Medio |
| `analyze_eeg_capture.py` | `_diagnose` | report | estado, razones, recomendaciones | Heuristica de validez | Medio/alto |
| `analyze_eeg_capture.py` | `_write_spectral_csv` | dir,report | archivo | Tabla bandas por canal | Bajo |
| `analyze_eeg_capture.py` | `_fmt_md_number` | value | string | Formato Markdown | Bajo |
| `analyze_eeg_capture.py` | `_write_markdown` | dir,report | archivo | Report humano | Bajo |
| `analyze_eeg_capture.py` | `analyze` | capture_dir | report | Pipeline completo offline | Medio |
| `analyze_eeg_capture.py` | `parse_args/main` | argv | exit code | CLI | Bajo |
| `compare_eeg_captures.py` | `_load_or_analyze` | capture_dir | report | Usa report existente o analiza | Medio |
| `compare_eeg_captures.py` | `_ratio` | num,den | float/None | Division segura | Bajo |
| `compare_eeg_captures.py` | `compare` | open,closed | dict | Compara bandas/ratios | Medio |
| `compare_eeg_captures.py` | `_write_markdown` | path,report | archivo | Report comparativo | Bajo |
| `compare_eeg_captures.py` | `parse_args/main` | argv | exit code | CLI | Bajo |
| `validate_spectral_features.py` | `_add_cached_site_packages` | Ninguna | Ninguna | Compatibilidad board shell | Bajo |
| `validate_spectral_features.py` | `_load_capture_csv/_load_metadata` | dir | arrays/dict | Lee captura | Medio |
| `validate_spectral_features.py` | `_finite` | any | float | Sanitiza | Bajo |
| `validate_spectral_features.py` | `_bandpower/_line_50_ratio/_spectral_entropy` | PSD | floats | Metricas espectrales | Medio |
| `validate_spectral_features.py` | `_summary` | valores | dict | Estadistica | Bajo |
| `validate_spectral_features.py` | `_classify_band` | banda,rows,condition | dict | Decision de uso por banda | Medio |
| `validate_spectral_features.py` | `_write_csv/_write_psd_csv` | path,rows/PSD | archivos | Outputs CSV | Bajo |
| `validate_spectral_features.py` | `validate_capture` | capture,params | report | Ventanas, DSPCore, quality, sonificacion | Medio/alto |
| `validate_spectral_features.py` | `_write_markdown` | path,report | archivo | Report espectral | Bajo |
| `validate_spectral_features.py` | `_discover_captures` | root | list dirs | Descubre capturas | Bajo |
| `validate_spectral_features.py` | `_write_aggregate` | root,reports | comparisons | Agregado multi-captura | Medio |
| `validate_spectral_features.py` | `parse_args/main` | argv | exit code | CLI | Bajo |
| `set_ads_diagnostic_mode.py` | `parse_args` | argv | Namespace | Lee modo | Bajo |
| `set_ads_diagnostic_mode.py` | `main` | mode | exit code | Reescribe `#define ADS_DIAGNOSTIC_MODE` | Alto |
| `test_led_matrix_visualizer.py` | `_notes` | Ninguna | list notas | Fixtures | Bajo |
| `test_led_matrix_visualizer.py` | `test_empty_frame_is_valid` | Ninguna | assertion | Valida rows 13x8 vacio | Bajo |
| `test_led_matrix_visualizer.py` | `test_pitch_center_and_clipping_ignore_out_of_range` | Ninguna | assertion | Clip ignore | Bajo |
| `test_led_matrix_visualizer.py` | `test_x_moves_left_to_right_with_time` | Ninguna | assertion | Mapeo temporal | Bajo |
| `test_led_matrix_visualizer.py` | `test_saturate_mode_keeps_extreme_notes_visible` | Ninguna | assertion | Clip saturate | Bajo |
| `test_led_matrix_visualizer.py` | `test_velocity_controls_intensity` | Ninguna | assertion | Intensidad por velocity | Bajo |
| `build_validation_docs.py` | `CaptureSummary` | dataclass | objeto | Resumen captura | Bajo |
| `build_validation_docs.py` | `_read_json`, `_fmt`, `_safe_float`, `_percent` | valores | valores seguros | Utilidades | Bajo |
| `build_validation_docs.py` | `_load_capture_summary/load_captures` | captures_dir | summaries | Descubre metadata/reports | Medio |
| `build_validation_docs.py` | `_write_csv/_markdown_table/_write_md_table/_write/_doc_header` | datos | archivos/texto | Escritura tablas/docs | Bajo |
| `build_validation_docs.py` | `apply_tfg_plot_style/_shade_timeline/_savefig` | matplotlib | figuras | Estilo plots | Bajo |
| `build_validation_docs.py` | `_read_timeseries/load_timeseries_csv/_read_psd/_read_windowed_bandpowers/load_*` | capture | arrays/list/dict | Carga datos para plots | Medio |
| `build_validation_docs.py` | `infer_or_load_state_timeline/_segment_signal/_compute_psd_for_segment` | capture/segment | timeline/PSD | Segmentos y PSD via DSPCore | Medio |
| `build_validation_docs.py` | `_git_lines/_git_text/_candidate_branches/discover_captures_all_branches/_read_git_json` | git args | texto/json | Inventario historico de ramas | Medio |
| `build_validation_docs.py` | `generate_figures` y `plot_*` | captures,figures_dir | paths | Figuras de validacion | Medio |
| `build_validation_docs.py` | `compute_state_stats`, `_median`, `_percentile`, `_state_diagnosis` | capture/rows | stats/texto | Estadistica por estado | Medio |
| `build_validation_docs.py` | `generate_tables` y helpers de conclusiones | captures | CSV/MD rows | Tablas TFG | Medio |
| `build_validation_docs.py` | `_doc_00`..`_doc_08` | summaries/figs/tables | Markdown | Docs TFG | Bajo/medio |
| `build_validation_docs.py` | `generate_docs/build/parse_args/main` | dirs | archivos/exit | Pipeline completo docs | Medio/alto por tamano |

## Riesgos

- `set_ads_diagnostic_mode.py` modifica firmware y debe usarse con commit claro.
- `build_validation_docs.py` es grande y mezcla lectura, calculo, plots y escritura: candidato a simplificar, pero offline.
- Tools offline no deben divergir de `DSPCore` ni reimplementar multitaper.
