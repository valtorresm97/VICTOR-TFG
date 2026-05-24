# Spectral validation report

- Capture: 20260524-115948_diag_atenuacion_mixed_states_ear_eeg
- Condition: diag_atenuacion_mixed_states_ear_eeg
- Channel: ch1
- Window: 4.0 s
- Hop: 0.256 s
- Windows: 705
- Median quality score: 0.9161084333181548
- Low-quality/artifact fraction: 0.13333333333333333

## Band Decisions

| Band | Median rel | P95 rel | Decision | Risk |
| --- | ---: | ---: | --- | --- |
| delta | 0.36588259946050733 | 0.5503431017865235 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| theta | 0.1045412300446285 | 0.18052487703522768 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| alpha | 0.041288796333341385 | 0.07811016361190203 | NECESITA MAS CAPTURAS | no validada solo por presencia; requiere open/closed robusto |
| beta | 0.06203008424556241 | 0.19207374397467022 | USAR SOLO COMO APOYO | puede aumentar con mandibula/frente/EMG |
| gamma | 0.3840701170455315 | 0.5774852361235886 | NO USAR EN TIEMPO REAL | muy sensible a EMG y ruido en EEG superficial |

## Sonification Controls

| Control | Median | P05 | P95 |
| --- | ---: | ---: | ---: |
| activity | 0.3735737496515487 | 0.12757451330025185 | 0.52945535234729 |
| calmness | 0.018766488435102754 | 0.008525086577582846 | 0.3548644612577022 |
| tension | 0.554927791933098 | 0.4481983958245333 | 0.6749281664980507 |
| rhythmic_density | 0.41121044200129736 | 0.13983042346646893 | 0.5948566977447408 |
| register | 0.31495192992984133 | 0.2649989832735662 | 0.43745969307809474 |
| harmonic_stability | 0.20668183517577277 | 0.124042535901731 | 0.3952714705204291 |
| velocity_factor | 0.5615016247560842 | 0.38930215931017637 | 0.6706187466431031 |
| note_probability | 0.47896835360103795 | 0.2618643387731752 | 0.6258853581957928 |

## Interpretation

- Use relative bands and ratios before absolute powers for sonification until session normalization is validated.
- Treat beta/gamma as artifact-sensitive unless jaw/forehead controls remain clean.
- Treat delta/theta as artifact-sensitive when blink, drift, or cable movement is present.
- Alpha requires open/closed comparison before being considered validated.
