# EEG capture quality report

- Diagnosis: dudosa
- Duration observed: 57.47 s
- Effective sample rate: 250.00 Hz
- Samples received: 14368
- Sample gaps: 0
- Invalid status: 0

## Reasons

- high 50 Hz power ratio
- abrupt jumps or motion artifacts

## Recommendations

- Check electrode contact, cable routing, grounding, and notch effectiveness.
- Repeat capture with still posture and verify electrode stability.

## CH1 summary

- rms_uV: 58.3981
- mean_uV: -0.981974
- ptp_uV: 1004
- line_50_ratio_1_50: 0.363277
- peak_freq_hz: 48.7194

## CH1 windowed stability

- window_sec: 2.0
- window_count: 56
- median_rms_uV: 55.1146
- p95_rms_uV: 72.7784
- best_window_rms_uV: 30.5469
- best_window_start_sec: 31
- median_ptp_uV: 789
- p95_ptp_uV: 919.5
- artifact_window_fraction: 0

## Multichannel summary

| Channel | RMS uV | Median win RMS uV | Artifact win % | Mean uV | PTP uV | Peak Hz | 50 Hz ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ch1 | 58.3981 | 55.1146 | 0 | -0.981974 | 1004 | 48.7194 | 0.363277 |
| ch2 | 462.875 | 0 | 3.57143 | -0.00208797 | 42428 | 8.36929 | 0.000931014 |
| ch3 | 383.514 | 0 | 3.57143 | 0.00368875 | 35150 | 8.0561 | 0.000930948 |
| ch4 | 462.932 | 0 | 3.57143 | 0 | 42428 | 7.4993 | 0.000946535 |
