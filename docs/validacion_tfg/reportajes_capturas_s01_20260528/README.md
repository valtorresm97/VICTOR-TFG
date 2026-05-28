# Reportajes por captura - sesion final `s01_20260528`

Esta carpeta contiene una version narrativa de las capturas finales de la sesion `s01_20260528`.

La documentacion automatica generada con matplotlib se conserva en:

```text
/docs/validacion_tfg/capturas_finales_s01_20260528_matplotlib/
```

Los reportajes de esta carpeta son una capa interpretativa adicional para el TFG. Su objetivo es ordenar las graficas y explicar que se observa en cada estado.

## Indice

| Documento | Condicion | Nivel de detalle | Uso recomendado |
| --- | --- | --- | --- |
| `00_prechecks.md` | Dos prechecks de 10 s | Breve | Verificacion tecnica previa. |
| `01_eyes_open_rest_60s.md` | Ojos abiertos | Completo | Mostrar captura real con artefacto transitorio. |
| `02_eyes_closed_rest_60s.md` | Ojos cerrados | Completo | Comparacion cualitativa con ojos abiertos, con cautela por 50 Hz. |
| `03_quiet_rest_60s.md` | Reposo quieto | Completo | Evidencia de pipeline sostenido en reposo. |
| `04_blink_artifact_30s.md` | Parpadeo | Completo | Artefacto fisiologico controlado. |
| `06_eyes_open_repeat_30s.md` | Repeticion ojos abiertos | Completo | Lectura base de la mejor candidata de la sesion. |
| `06_eyes_open_repeat_30s_reajustada.md` | Repeticion ojos abiertos reajustada | Completo final | Figura principal recomendada: conserva artefacto y anade vistas robustas, quality score y espectrograma. |

## Figura principal recomendada

Para la memoria del TFG, la figura mas defendible de la sesion es la de la captura `06_eyes_open_repeat_30s` en version reajustada:

```text
../figures/capturas_finales_s01_20260528_enhanced/06_eyes_open_repeat_30s/06_figura_combinada_reajustada_300uv.png
```

Debe usarse junto a la figura completa con transitorio para dejar claro que el artefacto existe y no se oculta.

## Criterio comun de interpretacion

Todas las capturas se interpretan bajo el mismo criterio:

```text
El sistema funciona tecnicamente y registra EEG + musica.
La calidad fisiologica no es limpia en toda la sesion.
Los artefactos deben documentarse, no ocultarse.
```

Por tanto, los reportajes no deben leerse como prueba clinica, sino como evidencia experimental y tecnica de integracion EEG-MIDI.
