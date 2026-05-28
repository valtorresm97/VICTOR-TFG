# EEG capture quality report

- Diagnosis: dudosa
- Duration observed: 28.58 s
- Effective sample rate: 250.00 Hz
- Samples received: 7144
- Sample gaps: 0
- Invalid status: 0

## Reasons

- CH1 RMS is far above typical resting scalp EEG amplitude
- CH1 peak-to-peak amplitude is far above typical resting scalp EEG
- abrupt jumps or motion artifacts

## Recommendations

- Treat this as transport-valid but physiologically suspicious; check gain/LSB, electrode placement, and BIAS/DRL strategy.
- Look for motion, electrode polarization, missing reference/common-mode control, or scaling error.
- Repeat capture with still posture and verify electrode stability.

## CH1 summary

- rms_uV: 967.03
- mean_uV: 13.995
- ptp_uV: 63088
- line_50_ratio_1_50: 0.00457259
- peak_freq_hz: 4.26932

## CH1 windowed stability

- window_sec: 2.0
- window_count: 27
- median_rms_uV: 143.361
- p95_rms_uV: 2739.29
- best_window_rms_uV: 75.0317
- best_window_start_sec: 3
- median_ptp_uV: 2060
- p95_ptp_uV: 52967.9
- artifact_window_fraction: 0.111111

## Multichannel summary

| Channel | RMS uV | Median win RMS uV | Artifact win % | Mean uV | PTP uV | Peak Hz | 50 Hz ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ch1 | 967.03 | 143.361 | 11.1111 | 13.995 | 63088 | 4.26932 | 0.00457259 |
| ch2 | 753.325 | 0 | 11.1111 | -0.00391937 | 42890 | 4.30431 | 0.000818113 |
| ch3 | 1338.18 | 0 | 7.40741 | -0.00461926 | 75575 | 8.92357 | 0.00116365 |
| ch4 | 1392.05 | 0 | 14.8148 | -0.00419933 | 83872 | 26.9107 | 0.000750588 |
