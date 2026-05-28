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
| `06_eyes_open_repeat_30s.md` | Repeticion ojos abiertos | Completo | Mejor candidata para figura principal combinada. |

## Criterio comun de interpretacion

Todas las capturas se interpretan bajo el mismo criterio:

```text
El sistema funciona tecnicamente y registra EEG + musica.
La calidad fisiologica no es limpia en toda la sesion.
Los artefactos deben documentarse, no ocultarse.
```

Por tanto, los reportajes no deben leerse como prueba clinica, sino como evidencia experimental y tecnica de integracion EEG-MIDI.
