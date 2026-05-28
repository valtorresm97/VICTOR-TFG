# Spectral validation report

- Capture: 20260528-144607_s01_20260528_ear_eeg_ch1_only_00_precheck_10s
- Condition: s01_20260528_ear_eeg_ch1_only_00_precheck_10s
- Channel: ch1
- Window: 4.0 s
- Hop: 0.256 s
- Windows: 22
- Median quality score: 1.0
- Low-quality/artifact fraction: 0.0

## Band Decisions

| Band | Median rel | P95 rel | Decision | Risk |
| --- | ---: | ---: | --- | --- |
| delta | 0.23520147051141688 | 0.4066590412520032 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| theta | 0.08924233273045751 | 0.11576948239509942 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| alpha | 0.1464588111951132 | 0.16478314401339406 | NECESITA MAS CAPTURAS | no validada solo por presencia; requiere open/closed robusto |
| beta | 0.22850463350870123 | 0.2509698717098356 | USAR SOLO COMO APOYO | puede aumentar con mandibula/frente/EMG |
| gamma | 0.3231389605588576 | 0.39287020912006226 | NO USAR EN TIEMPO REAL | muy sensible a EMG y ruido en EEG superficial |

## Sonification Controls

| Control | Median | P05 | P95 |
| --- | ---: | ---: | ---: |
| alpha_drive | 0.4188714567067033 | 0.28704963106173065 | 0.4808754622354276 |
| beta_gamma_drive | 0.5096424914560458 | 0.4223236554581552 | 0.6216579601349167 |
| rms_beta_activity | 0.26154578138238266 | 0.24601626559885342 | 0.2793342690961337 |
| band_driven_density | 0.2798251873086931 | 0.22027812033297334 | 0.31310637994470475 |
| spectral_register | 0.5253429175193862 | 0.47349524213712646 | 0.5977388585315286 |
| alpha_stability | 0.3943244486503161 | 0.2920376507575272 | 0.42265693707310126 |
| rms_band_velocity | 0.4904095041067361 | 0.4863224508144103 | 0.5129913534538338 |
| band_note_probability | 0.3738601498469545 | 0.32622249626637867 | 0.40048510395576375 |

## Interpretation

- Use relative bands and ratios before absolute powers for sonification until session normalization is validated.
- Treat beta/gamma as artifact-sensitive unless jaw/forehead controls remain clean.
- Treat delta/theta as artifact-sensitive when blink, drift, or cable movement is present.
- Alpha requires open/closed comparison before being considered validated.
