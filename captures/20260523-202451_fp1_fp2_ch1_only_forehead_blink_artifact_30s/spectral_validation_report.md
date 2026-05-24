# Spectral validation report

- Capture: 20260523-202451_fp1_fp2_ch1_only_forehead_blink_artifact_30s
- Condition: fp1_fp2_ch1_only_forehead_blink_artifact_30s
- Channel: ch1
- Window: 4.0 s
- Hop: 0.256 s
- Windows: 97
- Median quality score: 0.8641235983676107
- Low-quality/artifact fraction: 0.28865979381443296

## Band Decisions

| Band | Median rel | P95 rel | Decision | Risk |
| --- | ---: | ---: | --- | --- |
| delta | 0.8607236206992066 | 0.9077496763211408 | USAR SOLO COMO APOYO | condicion de artefacto puede inflar baja frecuencia |
| theta | 0.0655843091628964 | 0.14523557742802568 | USAR SOLO COMO APOYO | condicion de artefacto puede inflar baja frecuencia |
| alpha | 0.009172068175487604 | 0.033936559488183436 | NECESITA MAS CAPTURAS | no validada solo por presencia; requiere open/closed robusto |
| beta | 0.023732298652366864 | 0.07758739474923827 | NO USAR EN TIEMPO REAL | condicion de artefacto muestra contaminacion probable |
| gamma | 0.06393299600252939 | 0.1813894094652226 | NO USAR EN TIEMPO REAL | condicion de artefacto muestra contaminacion probable |

## Sonification Controls

| Control | Median | P05 | P95 |
| --- | ---: | ---: | ---: |
| activity | 0.24640400425165765 | 0.1757919087617424 | 0.36382976431513137 |
| calmness | 0.0027296483602063876 | 0.0010746375076808657 | 0.0141548255870439 |
| tension | 0.6070228536357625 | 0.439953797319909 | 0.7375911218762442 |
| rhythmic_density | 0.38304355849642757 | 0.27931193215448746 | 0.44549728161383 |
| register | 0.27744662283877974 | 0.2572396674808848 | 0.34140070402883216 |
| harmonic_stability | 0.13903042594208442 | 0.0928063230229896 | 0.20063535057835938 |
| velocity_factor | 0.4724828029761604 | 0.42305433613321974 | 0.554680835020592 |
| note_probability | 0.45643484679714214 | 0.37344954572359 | 0.506397825291064 |

## Interpretation

- Use relative bands and ratios before absolute powers for sonification until session normalization is validated.
- Treat beta/gamma as artifact-sensitive unless jaw/forehead controls remain clean.
- Treat delta/theta as artifact-sensitive when blink, drift, or cable movement is present.
- Alpha requires open/closed comparison before being considered validated.
