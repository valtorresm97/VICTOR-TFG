# EEG capture quality report

- Diagnosis: valida_preliminar_con_artefactos
- Duration observed: 181.86 s
- Effective sample rate: 250.00 Hz
- Samples received: 45464
- Sample gaps: 0
- Invalid status: 0

## Reasons

- stable windows look physiologically plausible, with some transient artifacts

## Recommendations

- Use the clean/still intervals for EEG validation and repeat with better cable fixation to reduce transient jumps.

## CH1 summary

- rms_uV: 757.654
- mean_uV: 0.838532
- ptp_uV: 83247
- line_50_ratio_1_50: 0.00180709
- peak_freq_hz: 7.01104

## CH1 windowed stability

- window_sec: 2.0
- window_count: 180
- median_rms_uV: 50.8354
- p95_rms_uV: 384.771
- best_window_rms_uV: 8.43042
- best_window_start_sec: 134
- median_ptp_uV: 768
- p95_ptp_uV: 6337
- artifact_window_fraction: 0.1

## Multichannel summary

| Channel | RMS uV | Median win RMS uV | Artifact win % | Mean uV | PTP uV | Peak Hz | 50 Hz ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ch1 | 757.654 | 50.8354 | 10 | 0.838532 | 83247 | 7.01104 | 0.00180709 |
| ch2 | 1241.16 | 0 | 14.4444 | -0.000219954 | 142835 | 15.3968 | 0.000906176 |
| ch3 | 1171.63 | 0 | 8.33333 | -0.00138571 | 168556 | 9.91994 | 0.000782608 |
| ch4 | 898.95 | 0 | 8.88889 | 0.00195759 | 105834 | 6.92306 | 0.000917655 |
