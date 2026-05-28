# Spectral validation report

- Capture: 20260528-145809_s01_20260528_ear_eeg_ch1_only_06_eyes_open_repeat_30s
- Condition: s01_20260528_ear_eeg_ch1_only_06_eyes_open_repeat_30s
- Channel: ch1
- Window: 4.0 s
- Hop: 0.256 s
- Windows: 95
- Median quality score: 1.0
- Low-quality/artifact fraction: 0.010526315789473684

## Band Decisions

| Band | Median rel | P95 rel | Decision | Risk |
| --- | ---: | ---: | --- | --- |
| delta | 0.3975236596864759 | 0.7452756331458344 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| theta | 0.11252023347618036 | 0.16618415137942416 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| alpha | 0.04975787180178986 | 0.1085870732024939 | NECESITA MAS CAPTURAS | no validada solo por presencia; requiere open/closed robusto |
| beta | 0.13163551699565523 | 0.5993335240977222 | USAR SOLO COMO APOYO | puede aumentar con mandibula/frente/EMG |
| gamma | 0.23362461529524767 | 0.38062464590878153 | NO USAR EN TIEMPO REAL | muy sensible a EMG y ruido en EEG superficial |

## Sonification Controls

| Control | Median | P05 | P95 |
| --- | ---: | ---: | ---: |
| alpha_drive | 0.29673933318357676 | 0.07389874178910909 | 0.41551676285202893 |
| beta_gamma_drive | 0.5847594361727758 | 0.4903842269745639 | 0.7580336220577085 |
| rms_beta_activity | 0.3089870009094503 | 0.18236264416452527 | 0.6757484138937248 |
| band_driven_density | 0.25447605429461395 | 0.19947125817390993 | 0.5902218205627762 |
| spectral_register | 0.5686173321251002 | 0.511413903600926 | 0.6903363252705614 |
| alpha_stability | 0.24904299984166767 | 0.0737794106679527 | 0.3751666430897181 |
| rms_band_velocity | 0.5492562064823661 | 0.428782390389025 | 0.8551334538151883 |
| band_note_probability | 0.3535808434356912 | 0.30957700653912795 | 0.6221774564502207 |

## Interpretation

- Use relative bands and ratios before absolute powers for sonification until session normalization is validated.
- Treat beta/gamma as artifact-sensitive unless jaw/forehead controls remain clean.
- Treat delta/theta as artifact-sensitive when blink, drift, or cable movement is present.
- Alpha requires open/closed comparison before being considered validated.
