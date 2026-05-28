# Benchmark report

- Branch: `docs/final-v3-audit-update`
- Commit: `51d5ebc97ab660b50b311c0f1b65dd04847f4f72`
- Python: `3.13.5 (main, Jun 25 2025, 18:55:22) [GCC 14.2.0]`
- Platform: `Linux-7.0.0-g122c2c22d838-aarch64-with-glibc2.41`

| benchmark_id | function | scenario | median ms | p95 ms | max ms | notes |
| --- | --- | --- | ---: | ---: | ---: | --- |
| real_capture.parse_eeg_block_values.first_block | parse_eeg_block_values | real_capture_first_block | 0.0489 | 0.0502 | 0.1404 | captura_real=20260528-104617_bench_real_rest_60s; blocks=1784; frames=14272; duration_sec=57.09 |
| real_capture.receiver_replay_all_blocks | EEGReceiver.eeg_block_uV | replay_all_real_capture_blocks | 162.6736 | 252.6365 | 318.8870 | captura_real=20260528-104617_bench_real_rest_60s; blocks=1784; frames=14272; duration_sec=57.09; tiempo por replay completo, no por bloque |
| real_capture.buffer_replay_all_blocks | EEGSignalProcessor.add_block_uV | replay_real_capture_into_ring_buffer | 74.6253 | 75.5110 | 75.9692 | captura_real=20260528-104617_bench_real_rest_60s; blocks=1784; frames=14272; duration_sec=57.09; tiempo por replay completo |
| real_capture.compute_live_features.final_window | EEGSignalProcessor.compute_live_features | real_capture_final_4s_window_ch1 | 5.4151 | 10.4633 | 23.1306 | captura_real=20260528-104617_bench_real_rest_60s; blocks=1784; frames=14272; duration_sec=57.09; benchmark principal DSP live en ventana real |
| real_capture.compute_quality_diagnostics.final_window | EEGSignalProcessor.compute_quality_diagnostics | real_capture_final_4s_diagnostics_ch1 | 5.9687 | 7.3465 | 8.2549 | captura_real=20260528-104617_bench_real_rest_60s; blocks=1784; frames=14272; duration_sec=57.09; incluye PSD para ratio 50 Hz |
| real_capture.dsp_core_compute_features.final_window | DSPCore.compute_features | real_capture_final_4s_window_direct_dsp | 5.2113 | 6.3767 | 7.3927 | captura_real=20260528-104617_bench_real_rest_60s; blocks=1784; frames=14272; duration_sec=57.09; mide DSPCore aislado sobre datos reales |
| real_capture.live_feature_sweep_replay | replay_blocks_with_feature_hop | real_capture_replay_compute_features_every_64_samples | 2630.2501 | 2642.7249 | 2644.4776 | captura_real=20260528-104617_bench_real_rest_60s; blocks=1784; frames=14272; duration_sec=57.09; feature_calls=208; simula hop real de 64 muestras |
| real_capture.numpy_materialize_uv_matrix | blocks_to_uv_matrix/asarray | real_capture_materialize_uv_matrix | 0.0015 | 0.0016 | 0.0031 | captura_real=20260528-104617_bench_real_rest_60s; blocks=1784; frames=14272; duration_sec=57.09; coste auxiliar no pertenece al loop real |
