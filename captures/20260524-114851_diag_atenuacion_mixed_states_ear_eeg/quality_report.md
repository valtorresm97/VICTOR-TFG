# EEG capture quality report

- Diagnosis: dudosa
- Duration observed: 183.68 s
- Effective sample rate: 250.00 Hz
- Samples received: 45920
- Sample gaps: 0
- Invalid status: 0

## Reasons

- abrupt jumps or motion artifacts

## Recommendations

- Full-capture peak-to-peak is high, but most 2 s windows are stable; inspect transient movement/artifact periods instead of rejecting the whole capture.
- Repeat capture with still posture and verify electrode stability.

## CH1 summary

- rms_uV: 596.749
- mean_uV: 30.922
- ptp_uV: 66813
- line_50_ratio_1_50: 0.0107935
- peak_freq_hz: 10.1699

## CH1 windowed stability

- window_sec: 2.0
- window_count: 182
- median_rms_uV: 71.895
- p95_rms_uV: 1047.78
- best_window_rms_uV: 37.1542
- best_window_start_sec: 91
- median_ptp_uV: 1042
- p95_ptp_uV: 17675.7
- artifact_window_fraction: 0.0934066

## Multichannel summary

| Channel | RMS uV | Median win RMS uV | Artifact win % | Mean uV | PTP uV | Peak Hz | 50 Hz ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ch1 | 596.749 | 71.895 | 9.34066 | 30.922 | 66813 | 10.1699 | 0.0107935 |
| ch2 | 1065.21 | 0 | 5.49451 | -2.64338 | 156504 | 20.6065 | 0.00112461 |
| ch3 | 476.1 | 0 | 4.94505 | 0.73088 | 75459 | 12.2496 | 0.000759973 |
| ch4 | 476.524 | 0 | 6.59341 | 0.00043554 | 62300 | 9.90309 | 0.00090244 |
