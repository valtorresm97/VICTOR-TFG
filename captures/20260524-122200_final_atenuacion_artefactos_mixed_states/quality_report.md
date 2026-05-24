# EEG capture quality report

- Diagnosis: valida_preliminar_con_artefactos
- Duration observed: 183.49 s
- Effective sample rate: 250.00 Hz
- Samples received: 45872
- Sample gaps: 0
- Invalid status: 0

## Reasons

- stable windows look physiologically plausible, with some transient artifacts

## Recommendations

- Use the clean/still intervals for EEG validation and repeat with better cable fixation to reduce transient jumps.

## CH1 summary

- rms_uV: 848.708
- mean_uV: 13.5315
- ptp_uV: 98868
- line_50_ratio_1_50: 0.00349621
- peak_freq_hz: 7.74438

## CH1 windowed stability

- window_sec: 2.0
- window_count: 182
- median_rms_uV: 83.3033
- p95_rms_uV: 264.207
- best_window_rms_uV: 44.9027
- best_window_start_sec: 6
- median_ptp_uV: 1200
- p95_ptp_uV: 1763.45
- artifact_window_fraction: 0.0604396

## Multichannel summary

| Channel | RMS uV | Median win RMS uV | Artifact win % | Mean uV | PTP uV | Peak Hz | 50 Hz ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ch1 | 848.708 | 83.3033 | 6.04396 | 13.5315 | 98868 | 7.74438 | 0.00349621 |
| ch2 | 1150.89 | 0 | 7.69231 | -0.171717 | 138115 | 10.7963 | 0.000669994 |
| ch3 | 1066.76 | 0 | 8.79121 | 0.0481993 | 129501 | 12.7583 | 0.00119694 |
| ch4 | 884.101 | 0 | 7.69231 | 1.5652 | 125554 | 14.922 | 0.000882919 |
