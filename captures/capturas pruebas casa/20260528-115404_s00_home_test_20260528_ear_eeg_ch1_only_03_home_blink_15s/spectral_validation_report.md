# Spectral validation report

- Capture: 20260528-115404_s00_home_test_20260528_ear_eeg_ch1_only_03_home_blink_15s
- Condition: s00_home_test_20260528_ear_eeg_ch1_only_03_home_blink_15s
- Channel: ch1
- Window: 4.0 s
- Hop: 0.256 s
- Windows: 40
- Median quality score: 0.0
- Low-quality/artifact fraction: 0.625

## Band Decisions

| Band | Median rel | P95 rel | Decision | Risk |
| --- | ---: | ---: | --- | --- |
| delta | 0.35979256182274455 | 0.5162554911869244 | USAR SOLO COMO APOYO | condicion de artefacto puede inflar baja frecuencia |
| theta | 0.1148083922891956 | 0.2094592853670167 | USAR SOLO COMO APOYO | condicion de artefacto puede inflar baja frecuencia |
| alpha | 0.03497095501787367 | 0.1664461702464733 | NECESITA MAS CAPTURAS | no validada solo por presencia; requiere open/closed robusto |
| beta | 0.15935324736705964 | 0.3572034975121752 | NO USAR EN TIEMPO REAL | condicion de artefacto muestra contaminacion probable |
| gamma | 0.2907067613463432 | 0.4619473912664371 | NO USAR EN TIEMPO REAL | condicion de artefacto muestra contaminacion probable |

## Sonification Controls

| Control | Median | P05 | P95 |
| --- | ---: | ---: | ---: |
| alpha_drive | 0.46489551819265434 | 0.21003691307057404 | 0.509488052760279 |
| beta_gamma_drive | 0.5082717895808009 | 0.44987392631781437 | 0.6623393159021042 |
| rms_beta_activity | 0.07036242281504348 | 0.0007437827921367784 | 0.2735446111880063 |
| band_driven_density | 0.06331872046819863 | 0.000669325654521037 | 0.24878676829804122 |
| spectral_register | 0.5166663913622191 | 0.49411308688517114 | 0.6295653799196403 |
| alpha_stability | 0.441659778190057 | 0.17454863646686727 | 0.4991437215351838 |
| rms_band_velocity | 0.3566760403702569 | 0.30059910761834696 | 0.5189813664662432 |
| band_note_probability | 0.20065497637455892 | 0.15053546052361683 | 0.349029414638433 |

## Interpretation

- Use relative bands and ratios before absolute powers for sonification until session normalization is validated.
- Treat beta/gamma as artifact-sensitive unless jaw/forehead controls remain clean.
- Treat delta/theta as artifact-sensitive when blink, drift, or cable movement is present.
- Alpha requires open/closed comparison before being considered validated.
