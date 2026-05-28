# Spectral validation report

- Capture: 20260528-115224_s00_home_test_20260528_ear_eeg_ch1_only_01_home_eyes_open_30s
- Condition: s00_home_test_20260528_ear_eeg_ch1_only_01_home_eyes_open_30s
- Channel: ch1
- Window: 4.0 s
- Hop: 0.256 s
- Windows: 98
- Median quality score: 0.9385008076688002
- Low-quality/artifact fraction: 0.12244897959183673

## Band Decisions

| Band | Median rel | P95 rel | Decision | Risk |
| --- | ---: | ---: | --- | --- |
| delta | 0.39383562584648246 | 0.6416353252855753 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| theta | 0.11005603614236496 | 0.1679717957312255 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| alpha | 0.03941532380718164 | 0.08088769526816818 | NECESITA MAS CAPTURAS | no validada solo por presencia; requiere open/closed robusto |
| beta | 0.08758438683725267 | 0.15636785298862155 | USAR SOLO COMO APOYO | puede aumentar con mandibula/frente/EMG |
| gamma | 0.367166725619015 | 0.5039892452188602 | NO USAR EN TIEMPO REAL | muy sensible a EMG y ruido en EEG superficial |

## Sonification Controls

| Control | Median | P05 | P95 |
| --- | ---: | ---: | ---: |
| alpha_drive | 0.3076098107770763 | 0.2014974958561011 | 0.48648274732172403 |
| beta_gamma_drive | 0.6171246047985315 | 0.5016246772455362 | 0.6837402813468342 |
| rms_beta_activity | 0.24742206902953912 | 0.0445939005765801 | 0.30120933179074494 |
| band_driven_density | 0.23761897809057667 | 0.033880671066417914 | 0.2655008910307102 |
| spectral_register | 0.618685149347309 | 0.5060815242699369 | 0.6592346327266321 |
| alpha_stability | 0.30764173226072683 | 0.20200322201200457 | 0.47866319926048195 |
| rms_band_velocity | 0.4808690225223136 | 0.3375169120854536 | 0.5456872185508187 |
| band_note_probability | 0.34009518247246134 | 0.17710453685313435 | 0.3624007128245682 |

## Interpretation

- Use relative bands and ratios before absolute powers for sonification until session normalization is validated.
- Treat beta/gamma as artifact-sensitive unless jaw/forehead controls remain clean.
- Treat delta/theta as artifact-sensitive when blink, drift, or cable movement is present.
- Alpha requires open/closed comparison before being considered validated.
