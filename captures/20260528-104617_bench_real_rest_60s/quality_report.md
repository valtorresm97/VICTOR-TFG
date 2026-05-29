# EEG capture quality report

- Diagnosis: valida_preliminar_con_artefactos
- Duration observed: 57.09 s
- Effective sample rate: 250.00 Hz
- Samples received: 14272
- Sample gaps: 0
- Invalid status: 0

## Reasons

- stable windows look physiologically plausible, with some transient artifacts

## Recommendations

- Use the clean/still intervals for EEG validation and repeat with better cable fixation to reduce transient jumps.

## CH1 summary

- rms_uV: 289.062
- mean_uV: 31.116
- ptp_uV: 16851
- line_50_ratio_1_50: 0.0714407
- peak_freq_hz: 24.9965

## CH1 windowed stability

- window_sec: 2.0
- window_count: 56
- median_rms_uV: 97.9523
- p95_rms_uV: 480.714
- best_window_rms_uV: 43.881
- best_window_start_sec: 48
- median_ptp_uV: 1266.5
- p95_ptp_uV: 5479.75
- artifact_window_fraction: 0.160714

## Multichannel summary

| Channel | RMS uV | Median win RMS uV | Artifact win % | Mean uV | PTP uV | Peak Hz | 50 Hz ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ch1 | 289.062 | 97.9523 | 16.0714 | 31.116 | 16851 | 24.9965 | 0.0714407 |
| ch2 | 1078.88 | 0 | 10.7143 | 0.0081278 | 101798 | 9.07371 | 0.00116699 |
| ch3 | 1563.62 | 0 | 17.8571 | -0.0650224 | 124176 | 15.625 | 0.00082626 |
| ch4 | 1220.75 | 0 | 16.0714 | -0.0570348 | 97215 | 15.625 | 0.00098082 |
