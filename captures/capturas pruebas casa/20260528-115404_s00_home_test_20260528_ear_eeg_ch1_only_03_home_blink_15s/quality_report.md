# EEG capture quality report

- Diagnosis: dudosa
- Duration observed: 14.02 s
- Effective sample rate: 250.00 Hz
- Samples received: 3504
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

- rms_uV: 2626.61
- mean_uV: 10.9521
- ptp_uV: 114989
- line_50_ratio_1_50: 0.00139016
- peak_freq_hz: 24.5434

## CH1 windowed stability

- window_sec: 2.0
- window_count: 13
- median_rms_uV: 171.735
- p95_rms_uV: 6797.79
- best_window_rms_uV: 91.7119
- best_window_start_sec: 2
- median_ptp_uV: 2459
- p95_ptp_uV: 114989
- artifact_window_fraction: 0.384615

## Multichannel summary

| Channel | RMS uV | Median win RMS uV | Artifact win % | Mean uV | PTP uV | Peak Hz | 50 Hz ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ch1 | 2626.61 | 171.735 | 38.4615 | 10.9521 | 114989 | 24.5434 | 0.00139016 |
| ch2 | 2489.05 | 0.363318 | 30.7692 | 0.010274 | 113109 | 14.2694 | 0.00127591 |
| ch3 | 1763.69 | 0 | 30.7692 | 0.00856164 | 85307 | 17.6227 | 0.000463375 |
| ch4 | 1874.65 | 0 | 15.3846 | -0.00827626 | 84857 | 9.13242 | 0.000881437 |
