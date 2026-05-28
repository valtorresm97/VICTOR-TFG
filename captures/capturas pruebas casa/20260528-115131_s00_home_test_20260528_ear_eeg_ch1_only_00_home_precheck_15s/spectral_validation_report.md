# Spectral validation report

- Capture: 20260528-115131_s00_home_test_20260528_ear_eeg_ch1_only_00_home_precheck_15s
- Condition: s00_home_test_20260528_ear_eeg_ch1_only_00_home_precheck_15s
- Channel: ch1
- Window: 4.0 s
- Hop: 0.256 s
- Windows: 41
- Median quality score: 1.0
- Low-quality/artifact fraction: 0.0

## Band Decisions

| Band | Median rel | P95 rel | Decision | Risk |
| --- | ---: | ---: | --- | --- |
| delta | 0.5064358261024035 | 0.6272074999428089 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| theta | 0.13059719480490847 | 0.160334900093865 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| alpha | 0.04764919439909086 | 0.06426852092135747 | NECESITA MAS CAPTURAS | no validada solo por presencia; requiere open/closed robusto |
| beta | 0.07673437005713953 | 0.1289092069071753 | USAR SOLO COMO APOYO | puede aumentar con mandibula/frente/EMG |
| gamma | 0.23766861731933017 | 0.3543248857474365 | NO USAR EN TIEMPO REAL | muy sensible a EMG y ruido en EEG superficial |

## Sonification Controls

| Control | Median | P05 | P95 |
| --- | ---: | ---: | ---: |
| alpha_drive | 0.3926781326886666 | 0.2983203184575649 | 0.45503958642452136 |
| beta_gamma_drive | 0.5159577937171257 | 0.46323686148125054 | 0.5790777736573387 |
| rms_beta_activity | 0.2761412266701323 | 0.2556480852603508 | 0.3096444978477467 |
| band_driven_density | 0.21943988386645946 | 0.20786989396285244 | 0.2471555066292318 |
| spectral_register | 0.5274016233800782 | 0.4946724141638496 | 0.5710147459894859 |
| alpha_stability | 0.3306574123251551 | 0.2417624502552003 | 0.36928127953149137 |
| rms_band_velocity | 0.5306594885578015 | 0.5026456882306202 | 0.575869424979133 |
| band_note_probability | 0.3255519070931676 | 0.3162959151702819 | 0.34772440530338544 |

## Interpretation

- Use relative bands and ratios before absolute powers for sonification until session normalization is validated.
- Treat beta/gamma as artifact-sensitive unless jaw/forehead controls remain clean.
- Treat delta/theta as artifact-sensitive when blink, drift, or cable movement is present.
- Alpha requires open/closed comparison before being considered validated.
