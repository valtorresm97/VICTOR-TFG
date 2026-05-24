# Mixed-state DSP validation by segment

| Segment | Windows | Quality | Low-quality % | RMS uV | alpha_rel | beta_rel | gamma_rel | slow | fast | activity | calmness | tension | note_prob |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| eyes_open_1 | 110 | 1 | 0 | 49 | 0.05859 | 0.116 | 0.3345 | 0.4747 | 0.4579 | 0.4236 | 0.02217 | 0.6003 | 0.5525 |
| eyes_closed_1 | 117 | 1 | 0 | 53.14 | 0.07007 | 0.09666 | 0.2986 | 0.5379 | 0.401 | 0.3671 | 0.02654 | 0.5377 | 0.4851 |
| jaw | 78 | 0.4 | 60.26 | 2332 | 0.03493 | 0.1346 | 0.1434 | 0.6693 | 0.291 | 0.4962 | 0.01546 | 0.6448 | 0.5814 |
| recovery_1 | 117 | 0.8223 | 11.11 | 58.6 | 0.04592 | 0.0654 | 0.2879 | 0.6093 | 0.3463 | 0.2487 | 0.01721 | 0.5471 | 0.4369 |
| blink_forehead | 78 | 0.75 | 0 | 47.57 | 0.05279 | 0.075 | 0.3292 | 0.5351 | 0.4075 | 0.3383 | 0.02419 | 0.5339 | 0.4754 |
| recovery_2 | 118 | 0.75 | 0 | 48.21 | 0.0545 | 0.1 | 0.3333 | 0.5055 | 0.4319 | 0.3888 | 0.01875 | 0.5728 | 0.5162 |
| eyes_closed_2 | 77 | 1 | 20.78 | 44.72 | 0.07111 | 0.08626 | 0.2707 | 0.5532 | 0.3589 | 0.4081 | 0.03386 | 0.502 | 0.5041 |

## Automatic observations

- closed_1/open_1: alpha_rel ratio=1.196, rms ratio=1.085, quality 1 vs 1.
- closed_2/open_1: alpha_rel ratio=1.214, rms ratio=0.9128, quality 1 vs 1.
- jaw/recovery_1: alpha_rel ratio=0.7606, rms ratio=39.8, quality 0.4 vs 0.8223.
- blink/recovery_2: alpha_rel ratio=0.9687, rms ratio=0.9868, quality 0.75 vs 0.75.
