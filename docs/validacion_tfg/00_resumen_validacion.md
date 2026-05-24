# 00. Resumen general de validación

Generado automáticamente por `python/tools/build_validation_docs.py`.

La validación se realizó antes de diseñar la sonificación final para separar tres problemas: la adquisición física de la señal, la extracción espectral de características y la respuesta musical. Esta separación evita atribuir a la música errores que podrían venir del ADC, del firmware o del montaje de electrodos.

En la rama documentada se dispone de 12 capturas versionadas con informes asociados. Las pruebas internas y reales indican que la cadena ADS1299 -> SPI -> firmware -> Bridge -> Python funciona sin pérdidas temporales apreciables en las capturas principales. Las limitaciones restantes se asocian sobre todo a artefactos biológicos o mecánicos: mandíbula, frente, contacto de electrodos, movimiento de cables y ruido común.

La captura final `20260524-122200_final_atenuacion_artefactos_mixed_states` resume el estado alcanzado: fs=250.0 Hz, gaps=0, invalid_status=0, RMS mediano por ventanas=83.30 µV y quality score mediano=0.912.

| Bloque validado | Pruebas realizadas | Resultado | Estado final |
| --- | --- | --- | --- |
| ADS1299/SPI/RDATAC | ID 0x3C, status 0xC00000, shorted_inputs | sin gaps/invalid status en capturas versionadas | razonablemente validado |
| Bridge MCU-Python | capturas CSV con 250 Hz y bloques de 8 | streaming estable | validado en condiciones probadas |
| Montaje electrodos | Fp1-Fp2, ear-EEG, BIAS/RLD | ear-EEG y CH1-only más estables | montaje final definido |
| DSP multitaper | windowed PSD, bandpowers, quality score | features reproducibles offline | validado para diagnóstico |
| Sonificación | quality gate y controles espectrales | atenuación funciona; diseño musical pendiente | siguiente fase |

Queda fuera del alcance de estos documentos el diseño sonoro definitivo. La evidencia aquí recogida sirve como base para esa fase posterior.

Tabla de inventario: [`tables/table_01_capture_summary.csv`](tables/table_01_capture_summary.csv).

La evolución de ramas, commits y decisiones de esta conversación se documenta en [`08_historial_ramas_y_cambios.md`](08_historial_ramas_y_cambios.md).
