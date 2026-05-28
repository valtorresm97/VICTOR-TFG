# Spectral validation report

- Capture: 20260528-145635_s01_20260528_ear_eeg_ch1_only_04_blink_artifact_30s
- Condition: s01_20260528_ear_eeg_ch1_only_04_blink_artifact_30s
- Channel: ch1
- Window: 4.0 s
- Hop: 0.256 s
- Windows: 97
- Median quality score: 1.0
- Low-quality/artifact fraction: 0.020618556701030927

## Band Decisions

| Band | Median rel | P95 rel | Decision | Risk |
| --- | ---: | ---: | --- | --- |
| delta | 0.48179358639825487 | 0.6436526023401116 | USAR SOLO COMO APOYO | condicion de artefacto puede inflar baja frecuencia |
| theta | 0.03757562305254777 | 0.14835920053582607 | USAR SOLO COMO APOYO | condicion de artefacto puede inflar baja frecuencia |
| alpha | 0.04413637865969191 | 0.09814950964086518 | NECESITA MAS CAPTURAS | no validada solo por presencia; requiere open/closed robusto |
| beta | 0.08199388607800907 | 0.19906607489798786 | NO USAR EN TIEMPO REAL | condicion de artefacto muestra contaminacion probable |
| gamma | 0.33438716326438467 | 0.4939637132887142 | NO USAR EN TIEMPO REAL | condicion de artefacto muestra contaminacion probable |

## Sonification Controls

| Control | Median | P05 | P95 |
| --- | ---: | ---: | ---: |
| alpha_drive | 0.33117302193223275 | 0.24502750301169585 | 0.394963748332317 |
| beta_gamma_drive | 0.5667530823740855 | 0.4961090565843137 | 0.667488489707439 |
| rms_beta_activity | 0.25619030899934225 | 0.17467798161144563 | 0.3207442755480702 |
| band_driven_density | 0.2326527132443732 | 0.18848354588890043 | 0.2650575572248556 |
| spectral_register | 0.5751023355457807 | 0.5130316833023946 | 0.6538773277031756 |
| alpha_stability | 0.3009394321935287 | 0.20827429785836477 | 0.3669787884910324 |
| rms_band_velocity | 0.5069158814413627 | 0.4336755040490229 | 0.5735535662533742 |
| band_note_probability | 0.33612217059549854 | 0.3007868367111204 | 0.36204604577988453 |

## Interpretation

- Use relative bands and ratios before absolute powers for sonification until session normalization is validated.
- Treat beta/gamma as artifact-sensitive unless jaw/forehead controls remain clean.
- Treat delta/theta as artifact-sensitive when blink, drift, or cable movement is present.
- Alpha requires open/closed comparison before being considered validated.
