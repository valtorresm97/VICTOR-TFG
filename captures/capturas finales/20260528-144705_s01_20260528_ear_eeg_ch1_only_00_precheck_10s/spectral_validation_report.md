# Spectral validation report

- Capture: 20260528-144705_s01_20260528_ear_eeg_ch1_only_00_precheck_10s
- Condition: s01_20260528_ear_eeg_ch1_only_00_precheck_10s
- Channel: ch1
- Window: 4.0 s
- Hop: 0.256 s
- Windows: 23
- Median quality score: 1.0
- Low-quality/artifact fraction: 0.0

## Band Decisions

| Band | Median rel | P95 rel | Decision | Risk |
| --- | ---: | ---: | --- | --- |
| delta | 0.4164995474098144 | 0.5101187104372683 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| theta | 0.06221809118018085 | 0.09985608741278121 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| alpha | 0.049593421766225325 | 0.07298860339749731 | NECESITA MAS CAPTURAS | no validada solo por presencia; requiere open/closed robusto |
| beta | 0.12057403816051095 | 0.149240680461013 | USAR SOLO COMO APOYO | puede aumentar con mandibula/frente/EMG |
| gamma | 0.35582053568728444 | 0.409441338094425 | NO USAR EN TIEMPO REAL | muy sensible a EMG y ruido en EEG superficial |

## Sonification Controls

| Control | Median | P05 | P95 |
| --- | ---: | ---: | ---: |
| alpha_drive | 0.30407670344716264 | 0.28202839457662354 | 0.3309722200327539 |
| beta_gamma_drive | 0.6120161244770684 | 0.5772696906828888 | 0.6273959054462671 |
| rms_beta_activity | 0.2853646404137532 | 0.26872292178591095 | 0.32230361984646616 |
| band_driven_density | 0.2643869515432391 | 0.2434005362010203 | 0.28498163629010576 |
| spectral_register | 0.6038168829511268 | 0.5787969504559723 | 0.6189918671715148 |
| alpha_stability | 0.2904341284744632 | 0.26871089445276736 | 0.3111060199386401 |
| rms_band_velocity | 0.5204778776710494 | 0.5122992713226879 | 0.5527918713751785 |
| band_note_probability | 0.3615095612345913 | 0.3447204289608163 | 0.37798530903208466 |

## Interpretation

- Use relative bands and ratios before absolute powers for sonification until session normalization is validated.
- Treat beta/gamma as artifact-sensitive unless jaw/forehead controls remain clean.
- Treat delta/theta as artifact-sensitive when blink, drift, or cable movement is present.
- Alpha requires open/closed comparison before being considered validated.
