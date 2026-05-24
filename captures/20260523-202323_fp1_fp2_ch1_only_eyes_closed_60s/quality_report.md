# EEG capture quality report

- Diagnosis: valida_preliminar_con_artefactos
- Duration observed: 57.15 s
- Effective sample rate: 250.00 Hz
- Samples received: 14288
- Sample gaps: 0
- Invalid status: 0

## Reasons

- stable windows look physiologically plausible, with some transient artifacts

## Recommendations

- Use the clean/still intervals for EEG validation and repeat with better cable fixation to reduce transient jumps.

## CH1 summary

- rms_uV: 859.721
- mean_uV: 0.587556
- ptp_uV: 45684
- line_50_ratio_1_50: 0.000895125
- peak_freq_hz: 13.3679

## CH1 windowed stability

- window_sec: 2.0
- window_count: 56
- median_rms_uV: 37.3516
- p95_rms_uV: 2657.62
- best_window_rms_uV: 14.8112
- best_window_start_sec: 4
- median_ptp_uV: 552.5
- p95_ptp_uV: 45532
- artifact_window_fraction: 0.0892857

## Multichannel summary

| Channel | RMS uV | Median win RMS uV | Artifact win % | Mean uV | PTP uV | Peak Hz | 50 Hz ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ch1 | 859.721 | 37.3516 | 8.92857 | 0.587556 | 45684 | 13.3679 | 0.000895125 |
| ch2 | 1406.28 | 0 | 14.2857 | 0.000279955 | 112948 | 6.31649 | 0.000833824 |
| ch3 | 1406.68 | 0 | 12.5 | 0.00587906 | 106939 | 18.3021 | 0.00104631 |
| ch4 | 1605.25 | 0 | 12.5 | 0.00370941 | 134267 | 11.0407 | 0.000910631 |
