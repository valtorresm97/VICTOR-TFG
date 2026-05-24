# Spectral validation report

- Capture: 20260523-200925_ear_eeg_ch1_only_eyes_open_60s
- Condition: ear_eeg_ch1_only_eyes_open_60s
- Channel: ch1
- Window: 4.0 s
- Hop: 0.256 s
- Windows: 210
- Median quality score: 1.0
- Low-quality/artifact fraction: 0.0

## Band Decisions

| Band | Median rel | P95 rel | Decision | Risk |
| --- | ---: | ---: | --- | --- |
| delta | 0.3909983758863337 | 0.8876472088635017 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| theta | 0.10761992140833913 | 0.1535284121313884 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| alpha | 0.0639895741892422 | 0.11031911934334329 | NECESITA MAS CAPTURAS | no validada solo por presencia; requiere open/closed robusto |
| beta | 0.15439268328886968 | 0.22428381674914682 | USAR SOLO COMO APOYO | puede aumentar con mandibula/frente/EMG |
| gamma | 0.25990967046222796 | 0.33900290446929304 | NO USAR EN TIEMPO REAL | muy sensible a EMG y ruido en EEG superficial |

## Sonification Controls

| Control | Median | P05 | P95 |
| --- | ---: | ---: | ---: |
| activity | 0.3671687993884981 | 0.2678487907741381 | 0.4602174579665071 |
| calmness | 0.017984292253942852 | 0.0062970495384088295 | 0.039775782206129234 |
| tension | 0.6082331627887765 | 0.5408405166419572 | 0.670622309310677 |
| rhythmic_density | 0.4498361693408117 | 0.39565003890457834 | 0.5023249252310419 |
| register | 0.3312868403245122 | 0.26403533518239797 | 0.4084471008433473 |
| harmonic_stability | 0.1493896821416354 | 0.1253204898113977 | 0.1815361425919394 |
| velocity_factor | 0.5570181595719488 | 0.4874941535418967 | 0.6221522205765551 |
| note_probability | 0.5098689354726493 | 0.4665200311236628 | 0.5518599401848335 |

## Interpretation

- Use relative bands and ratios before absolute powers for sonification until session normalization is validated.
- Treat beta/gamma as artifact-sensitive unless jaw/forehead controls remain clean.
- Treat delta/theta as artifact-sensitive when blink, drift, or cable movement is present.
- Alpha requires open/closed comparison before being considered validated.
