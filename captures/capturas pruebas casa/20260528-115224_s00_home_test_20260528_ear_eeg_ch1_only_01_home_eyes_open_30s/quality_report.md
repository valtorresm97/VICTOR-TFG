# EEG capture quality report

- Diagnosis: dudosa
- Duration observed: 28.83 s
- Effective sample rate: 250.00 Hz
- Samples received: 7208
- Sample gaps: 0
- Invalid status: 0

## Reasons

- CH1 peak-to-peak amplitude is far above typical resting scalp EEG

## Recommendations

- Look for motion, electrode polarization, missing reference/common-mode control, or scaling error.

## CH1 summary

- rms_uV: 421.622
- mean_uV: 9.80757
- ptp_uV: 26362
- line_50_ratio_1_50: 0.0158486
- peak_freq_hz: 4.16204

## CH1 windowed stability

- window_sec: 2.0
- window_count: 27
- median_rms_uV: 101.898
- p95_rms_uV: 1139.39
- best_window_rms_uV: 36.4037
- best_window_start_sec: 2
- median_ptp_uV: 1556
- p95_ptp_uV: 18983.5
- artifact_window_fraction: 0.0740741

## Multichannel summary

| Channel | RMS uV | Median win RMS uV | Artifact win % | Mean uV | PTP uV | Peak Hz | 50 Hz ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ch1 | 421.622 | 101.898 | 7.40741 | 9.80757 | 26362 | 4.16204 | 0.0158486 |
| ch2 | 735.21 | 0 | 11.1111 | 0.00332963 | 47732 | 8.67092 | 0.000907052 |
| ch3 | 7.66427 | 0 | 0 | 0.00402331 | 498 | 6.3818 | 0.0009045 |
| ch4 | 1.66745 | 0 | 0 | 0.00346837 | 108 | 2.91343 | 0.000871734 |
