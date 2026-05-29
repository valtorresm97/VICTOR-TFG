# Benchmark report

- Branch: `docs/final-v3-audit-update`
- Commit: `163dce71c3ebd01831747c78ecbf748ffd4226f0`
- Python: `3.13.5 (main, Jun 25 2025, 18:55:22) [GCC 14.2.0]`
- Platform: `Linux-7.0.0-g122c2c22d838-aarch64-with-glibc2.41`

| benchmark_id | function | scenario | median ms | p95 ms | max ms | notes |
| --- | --- | --- | ---: | ---: | ---: | --- |
| real_capture.parse_eeg_block_values.first_block | parse_eeg_block_values | real_capture_first_block | 0.0492 | 0.0516 | 0.1084 | captura_real=20260528-111723_bench_real_rest_60s_mcu; blocks=1796; frames=14368; duration_sec=57.47 |
| real_capture.receiver_replay_all_blocks | EEGReceiver.eeg_block_uV | replay_all_real_capture_blocks | 169.4442 | 245.3876 | 329.4355 | captura_real=20260528-111723_bench_real_rest_60s_mcu; blocks=1796; frames=14368; duration_sec=57.47; tiempo por replay completo, no por bloque |
| real_capture.buffer_replay_all_blocks | EEGSignalProcessor.add_block_uV | replay_real_capture_into_ring_buffer | 76.1546 | 76.3177 | 76.3869 | captura_real=20260528-111723_bench_real_rest_60s_mcu; blocks=1796; frames=14368; duration_sec=57.47; tiempo por replay completo |
| real_capture.compute_live_features.final_window | EEGSignalProcessor.compute_live_features | real_capture_final_4s_window_ch1 | 5.2158 | 6.4103 | 6.9831 | captura_real=20260528-111723_bench_real_rest_60s_mcu; blocks=1796; frames=14368; duration_sec=57.47; benchmark principal DSP live en ventana real |
| real_capture.compute_quality_diagnostics.final_window | EEGSignalProcessor.compute_quality_diagnostics | real_capture_final_4s_diagnostics_ch1 | 6.0806 | 8.1642 | 9.4764 | captura_real=20260528-111723_bench_real_rest_60s_mcu; blocks=1796; frames=14368; duration_sec=57.47; incluye PSD para ratio 50 Hz |
| real_capture.dsp_core_compute_features.final_window | DSPCore.compute_features | real_capture_final_4s_window_direct_dsp | 5.1967 | 6.2634 | 6.5716 | captura_real=20260528-111723_bench_real_rest_60s_mcu; blocks=1796; frames=14368; duration_sec=57.47; mide DSPCore aislado sobre datos reales |
| real_capture.live_feature_sweep_replay | replay_blocks_with_feature_hop | real_capture_replay_compute_features_every_64_samples | 2624.4660 | 2635.7004 | 2640.8206 | captura_real=20260528-111723_bench_real_rest_60s_mcu; blocks=1796; frames=14368; duration_sec=57.47; feature_calls=209; simula hop real de 64 muestras |
| real_capture.numpy_materialize_uv_matrix | blocks_to_uv_matrix/asarray | real_capture_materialize_uv_matrix | 0.0015 | 0.0019 | 0.0030 | captura_real=20260528-111723_bench_real_rest_60s_mcu; blocks=1796; frames=14368; duration_sec=57.47; coste auxiliar no pertenece al loop real |
