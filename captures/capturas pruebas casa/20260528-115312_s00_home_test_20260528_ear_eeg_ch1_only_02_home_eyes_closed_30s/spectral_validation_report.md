# Spectral validation report

- Capture: 20260528-115312_s00_home_test_20260528_ear_eeg_ch1_only_02_home_eyes_closed_30s
- Condition: s00_home_test_20260528_ear_eeg_ch1_only_02_home_eyes_closed_30s
- Channel: ch1
- Window: 4.0 s
- Hop: 0.256 s
- Windows: 97
- Median quality score: 0.8430226308086535
- Low-quality/artifact fraction: 0.3402061855670103

## Band Decisions

| Band | Median rel | P95 rel | Decision | Risk |
| --- | ---: | ---: | --- | --- |
| delta | 0.298456636502778 | 0.4661483050243617 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| theta | 0.0945032702198802 | 0.1820292957321544 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| alpha | 0.03852682674169459 | 0.06283403532943097 | NECESITA MAS CAPTURAS | no validada solo por presencia; requiere open/closed robusto |
| beta | 0.0902574265968819 | 0.3499604174138664 | USAR SOLO COMO APOYO | puede aumentar con mandibula/frente/EMG |
| gamma | 0.4537267585642571 | 0.596721701137849 | NO USAR EN TIEMPO REAL | muy sensible a EMG y ruido en EEG superficial |

## Sonification Controls

| Control | Median | P05 | P95 |
| --- | ---: | ---: | ---: |
| alpha_drive | 0.31345773794588666 | 0.22154506206526128 | 0.4923172639602553 |
| beta_gamma_drive | 0.6012993838109568 | 0.5053215752030416 | 0.655447925989972 |
| rms_beta_activity | 0.23355611509523774 | 0.006792881009315089 | 0.30493552941682545 |
| band_driven_density | 0.21312574769499848 | 0.006645916150337763 | 0.2679820607326126 |
| spectral_register | 0.6178871014123476 | 0.5046330552272752 | 0.6789402281409045 |
| alpha_stability | 0.3124497312078043 | 0.24099169507904553 | 0.49291934473881355 |
| rms_band_velocity | 0.47553702307372747 | 0.30489447486609617 | 0.5450430960017747 |
| band_note_probability | 0.32050059815599874 | 0.15531673292027023 | 0.36438564858609007 |

## Interpretation

- Use relative bands and ratios before absolute powers for sonification until session normalization is validated.
- Treat beta/gamma as artifact-sensitive unless jaw/forehead controls remain clean.
- Treat delta/theta as artifact-sensitive when blink, drift, or cable movement is present.
- Alpha requires open/closed comparison before being considered validated.
