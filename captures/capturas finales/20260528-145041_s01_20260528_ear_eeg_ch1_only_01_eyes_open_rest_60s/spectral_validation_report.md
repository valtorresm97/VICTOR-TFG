# Spectral validation report

- Capture: 20260528-145041_s01_20260528_ear_eeg_ch1_only_01_eyes_open_rest_60s
- Condition: s01_20260528_ear_eeg_ch1_only_01_eyes_open_rest_60s
- Channel: ch1
- Window: 4.0 s
- Hop: 0.256 s
- Windows: 208
- Median quality score: 1.0
- Low-quality/artifact fraction: 0.25

## Band Decisions

| Band | Median rel | P95 rel | Decision | Risk |
| --- | ---: | ---: | --- | --- |
| delta | 0.42687804343726843 | 0.8761015036954586 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| theta | 0.1443949561693462 | 0.25959726472475836 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| alpha | 0.06644744524010951 | 0.12286334046861642 | NECESITA MAS CAPTURAS | no validada solo por presencia; requiere open/closed robusto |
| beta | 0.12053955051349452 | 0.2420117539627921 | USAR SOLO COMO APOYO | puede aumentar con mandibula/frente/EMG |
| gamma | 0.20159247408847925 | 0.32752792475288767 | NO USAR EN TIEMPO REAL | muy sensible a EMG y ruido en EEG superficial |

## Sonification Controls

| Control | Median | P05 | P95 |
| --- | ---: | ---: | ---: |
| alpha_drive | 0.3605828990764498 | 0.2720702961984225 | 0.49998192184748924 |
| beta_gamma_drive | 0.5365192959101428 | 0.4386454704756212 | 0.5995847216850899 |
| rms_beta_activity | 0.2578987865482719 | 0.0004376049710037852 | 0.30691707236296056 |
| band_driven_density | 0.22316960893223323 | 0.0004038054288084935 | 0.28923749707815455 |
| spectral_register | 0.5373121594181487 | 0.4750455647753759 | 0.5779706257410535 |
| alpha_stability | 0.37101607843297657 | 0.3000625992651146 | 0.4999513265978647 |
| rms_band_velocity | 0.5036137863835537 | 0.300345555927376 | 0.5528935892712684 |
| band_note_probability | 0.32853568714578657 | 0.1503230443430468 | 0.3813899976625237 |

## Interpretation

- Use relative bands and ratios before absolute powers for sonification until session normalization is validated.
- Treat beta/gamma as artifact-sensitive unless jaw/forehead controls remain clean.
- Treat delta/theta as artifact-sensitive when blink, drift, or cable movement is present.
- Alpha requires open/closed comparison before being considered validated.
