# EEG capture quality report

- Diagnosis: dudosa
- Duration observed: 57.12 s
- Effective sample rate: 250.00 Hz
- Samples received: 14280
- Sample gaps: 0
- Invalid status: 0

## Reasons

- abrupt jumps or motion artifacts

## Recommendations

- Full-capture peak-to-peak is high, but most 2 s windows are stable; inspect transient movement/artifact periods instead of rejecting the whole capture.
- Repeat capture with still posture and verify electrode stability.

## CH1 summary

- rms_uV: 2199.4
- mean_uV: -2.37367
- ptp_uV: 107661
- line_50_ratio_1_50: 0.00043512
- peak_freq_hz: 31.25

## CH1 windowed stability

- window_sec: 2.0
- window_count: 56
- median_rms_uV: 38.0824
- p95_rms_uV: 5901.71
- best_window_rms_uV: 20.5134
- best_window_start_sec: 55
- median_ptp_uV: 479
- p95_ptp_uV: 78564
- artifact_window_fraction: 0.125

## Multichannel summary

| Channel | RMS uV | Median win RMS uV | Artifact win % | Mean uV | PTP uV | Peak Hz | 50 Hz ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ch1 | 2199.4 | 38.0824 | 12.5 | -2.37367 | 107661 | 31.25 | 0.00043512 |
| ch2 | 1951.51 | 0 | 12.5 | 0.00238095 | 126783 | 23.3543 | 0.00125963 |
| ch3 | 24.8979 | 0 | 0 | 0.0030112 | 2226 | 15.2311 | 0.0010813 |
| ch4 | 693.565 | 0 | 10.7143 | -0.0070028 | 42428 | 5.84734 | 0.00099371 |
