# Spectral validation report

- Capture: 20260523-201321_ear_eeg_ch1_only_jaw_movement_30s
- Condition: ear_eeg_ch1_only_jaw_movement_30s
- Channel: ch1
- Window: 4.0 s
- Hop: 0.256 s
- Windows: 98
- Median quality score: 0.49008808996447184
- Low-quality/artifact fraction: 0.6836734693877551

## Band Decisions

| Band | Median rel | P95 rel | Decision | Risk |
| --- | ---: | ---: | --- | --- |
| delta | 0.9449678009692054 | 0.9632917930018338 | USAR SOLO COMO APOYO | condicion de artefacto puede inflar baja frecuencia |
| theta | 0.02644133152862855 | 0.044672255978826604 | USAR SOLO COMO APOYO | condicion de artefacto puede inflar baja frecuencia |
| alpha | 0.006646986973613935 | 0.01600608242299297 | NECESITA MAS CAPTURAS | no validada solo por presencia; requiere open/closed robusto |
| beta | 0.012296701299115198 | 0.0485461972208271 | NO USAR EN TIEMPO REAL | condicion de artefacto muestra contaminacion probable |
| gamma | 0.00955511757923462 | 0.13574440961623568 | NO USAR EN TIEMPO REAL | condicion de artefacto muestra contaminacion probable |

## Sonification Controls

| Control | Median | P05 | P95 |
| --- | ---: | ---: | ---: |
| activity | 0.22202310721068796 | 0.12451147868211854 | 0.31269549173987327 |
| calmness | 0.002378562579398201 | 0.001421360704926955 | 0.003876326229138316 |
| tension | 0.567113634134962 | 0.4040533239351665 | 0.6436339162860034 |
| rhythmic_density | 0.3230306475735653 | 0.28041294454564 | 0.4103938961937726 |
| register | 0.2724219651002766 | 0.2542372881355932 | 0.3084041989357555 |
| harmonic_stability | 0.1526645021007276 | 0.1262438546832403 | 0.21123894097047372 |
| velocity_factor | 0.45541617504748166 | 0.38715803507748303 | 0.5188868442179113 |
| note_probability | 0.40842451805885227 | 0.374330355636512 | 0.47831511695501805 |

## Interpretation

- Use relative bands and ratios before absolute powers for sonification until session normalization is validated.
- Treat beta/gamma as artifact-sensitive unless jaw/forehead controls remain clean.
- Treat delta/theta as artifact-sensitive when blink, drift, or cable movement is present.
- Alpha requires open/closed comparison before being considered validated.
