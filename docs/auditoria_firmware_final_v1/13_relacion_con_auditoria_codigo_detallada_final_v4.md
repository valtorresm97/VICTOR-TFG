# 13. Relacion entre auditoria_firmware_final_v1 y auditoria_codigo_detallada - final-v4

## 1. Decision documental

La carpeta `docs/auditoria_firmware_final_v1/` no debe tratarse como duplicado simple de `docs/auditoria_codigo_detallada/`.

Aunque nacio como auditoria de `firmware-final-v1`, contiene descripciones narrativas y transversales de los sistemas que pueden ser muy utiles para redactar la memoria del TFG. La carpeta `auditoria_codigo_detallada/`, en cambio, es mas tabular, mas exhaustiva por funcion y mas orientada a no romper contratos durante refactor.

Decision final-v4:

```text
Conservar docs/auditoria_firmware_final_v1/
Reajustarla a firmware-final-v4
Usarla como capa narrativa/transversal para redaccion TFG
Usar docs/auditoria_codigo_detallada/ como capa tecnica funcion por funcion
```

## 2. Diferencia entre ambas carpetas

| Carpeta | Estilo | Aporta principalmente | Mejor uso |
| --- | --- | --- | --- |
| `docs/auditoria_codigo_detallada/` | Tablas, funcion por funcion, contratos, criticidad, pruebas | Seguridad tecnica para tocar codigo, contratos intocables, ruta esencial UML, candidatos a simplificacion | Refactor, UML tecnico, pruebas, evitar romper runtime |
| `docs/auditoria_firmware_final_v1/` | Texto mas global y narrativo por subsistema | Explicacion de arquitectura, papel de cada bloque, vision de sistema, contexto de decisiones | Redaccion TFG, explicacion de bloques, introduccion tecnica por modulos |

Por tanto, ambas deben convivir:

```text
auditoria_codigo_detallada = precision tecnica y checklist de refactor
auditoria_firmware_final_v1 = explicacion narrativa y material redactable para memoria
```

## 3. Regla de prevalencia

Si ambas carpetas dicen cosas distintas, prevalece este orden:

```text
1. Codigo real de firmware-final-v4
2. docs/configuracion_final_v4.md
3. docs/auditoria_codigo_detallada/09_mapa_contratos_entre_modulos.md
4. docs/auditoria_codigo_detallada/10_mapa_funciones_criticas.md
5. docs/auditoria_firmware_final_v1/ una vez reajustada
6. documentos historicos antiguos
```

La carpeta `auditoria_firmware_final_v1/` debe actualizarse para no contradecir final-v4, pero no tiene que repetir tabla por tabla toda la auditoria detallada.

## 4. Informacion valiosa especifica de auditoria_firmware_final_v1

La informacion mas valiosa de esta carpeta es:

- explicaciones globales de arquitectura;
- descripciones por bloque mas redactables que una tabla;
- transiciones entre firmware, Python, WebUI y tools;
- riesgos escritos en lenguaje mas narrativo;
- contexto historico de por que aparecen LED, MIDI, capturas y tools;
- mapas globales de configuracion, deuda tecnica y controles faltantes;
- material util para convertir despues en apartados de memoria.

Esta informacion es distinta de la auditoria funcion por funcion y conviene conservarla.

## 5. Mapeo documento a documento

| Documento en `auditoria_firmware_final_v1/` | Relacion con `auditoria_codigo_detallada/` | Valor para TFG | Accion final-v4 |
| --- | --- | --- | --- |
| `00_inventario_proyecto.md` | Se solapa con `00_inventario_actual.md`, pero su estilo es mas resumido y por familias | Medio: sirve como inventario narrativo de proyecto | Actualizar a final-v4, retirar capturas antiguas como listado principal y referenciar capturas finales/benchmarks. |
| `01_arquitectura_global.md` | Se complementa con mapas 09/10/11 detallados | Muy alto: explica flujo end-to-end en texto claro | Reajustar a nombres final-v4, separar LED como lateral, actualizar nombres de sonificacion y final-v4. |
| `02_auditoria_firmware_mcu.md` | Se solapa con `01_firmware_funcion_por_funcion.md` y `02_ads1299_spi_driver.md` | Alto: puede explicar firmware de forma narrativa para memoria | Conservar resumen narrativo, no repetir toda la tabla funcional. Actualizar modo ADS 5, MIDI TXINV, benchmarks Monitor. |
| `03_auditoria_python_backend.md` | Se solapa con `03_python_backend_funcion_por_funcion.md` | Alto: explica backend como orquestador | Actualizar con `SignalQuality / QualityGate`, MIDI activo, WebUI controls, capturas musicales. |
| `04_auditoria_dsp_features.md` | Se solapa con `04_dsp_eeg_funcion_por_funcion.md` | Muy alto: material directo para capitulo DSP/sonificacion | Mantener narrativa de multitaper/bandpowers/quality gate; excluir `compute_online_features` del flujo principal. |
| `05_auditoria_sonificacion_midi.md` | Se solapa con `05_sonificacion_midi_funcion_por_funcion.md` | Muy alto: explica mapping EEG->musica | Actualizar a nombres reportables final-v4 y ruta `midi_bytes` validada. |
| `06_auditoria_led_matrix_scroll.md` | Se solapa con `06_led_matrix_funcion_por_funcion.md` | Medio/bajo: util si se menciona LED como extra | Marcar claramente como lateral/desactivado por defecto, no evidencia central. |
| `07_auditoria_web_ui.md` | Se solapa con `07_web_server_assets_funcion_por_funcion.md` | Alto: WebUI necesita explicacion comprensible para TFG | Reescribir con cuidado: WebUI como monitorizacion/control musical ligero, conservar fluidez, panic, root/main/scale y piano roll. |
| `08_auditoria_tools_capturas_docs.md` | Se solapa con `08_tools_cli_funcion_por_funcion.md` | Alto para metodologia experimental | Separar tools offline de runtime; explicar captura, validacion, figuras y benchmarks de forma narrativa. |
| `09_mapa_configuraciones.md` | Complementa mapas de contratos/criticidad | Alto para reproducibilidad | Actualizar defaults final-v4: MIDI activo, LED desactivado, ADS mode 5, CH1-only. |
| `10_redundancias_y_deuda_tecnica.md` | Complementa `11_hallazgos_para_simplificacion_futura.md` | Alto para justificar simplificacion futura | Actualizar con hallazgos nuevos: doble SPI begin, wrappers legacy, comentarios historicos, WebUI delicada. |
| `11_controles_faltantes_y_riesgos.md` | Complementa riesgos de auditoria detallada | Medio/alto | Revisar porque algunos controles ya existen: root/main/scale, panic MIDI, quality gate, capturas musicales. |
| `12_mapa_criticidad_refactor.md` | Se solapa con `10_mapa_funciones_criticas.md` | Medio | Alinear o marcar como resumen transversal; no repetir toda la tabla. |

## 6. Que no debe hacerse

No conviene:

- borrar la carpeta por considerarla duplicada;
- moverla entera a historico sin revisar;
- convertirla en otra auditoria funcion por funcion;
- dejar referencias a final-v3 como estado actual;
- dejar nombres antiguos de sonificacion como principales;
- presentar LED matrix como parte del flujo EEG->MIDI principal;
- presentar capturas antiguas como evidencia final principal si ya existen `s01_20260528` y benchmarks reales final-v4.

## 7. Criterio de actualizacion por documento

Al actualizar cada documento de esta carpeta:

1. Mantener texto explicativo si ayuda a entender el sistema.
2. Cambiar final-v3/final-v1 por final-v4 cuando sea estado actual.
3. Mantener procedencia historica solo al inicio o como nota.
4. Sustituir nombres legacy de sonificacion por nombres final-v4.
5. Marcar LED, tools, benchmarks y capturas como laterales cuando proceda.
6. Referenciar `auditoria_codigo_detallada/` para tablas exhaustivas.
7. Evitar duplicar tablas largas si ya existen en la auditoria detallada.
8. Orientar el texto a redaccion del TFG.

## 8. Relacion con la futura version esencial UML

La futura version esencial debe alimentarse de ambas carpetas:

```text
Para decidir que entra y que no entra:
  docs/auditoria_codigo_detallada/09, 10, 11

Para escribir explicaciones del TFG:
  docs/auditoria_firmware_final_v1/01, 02, 03, 04, 05, 07, 08, 09
```

En especial, `01_arquitectura_global.md` puede ser una base muy buena para:

```text
docs/propuesta_version_esencial_uml.md
```

una vez corregido a final-v4.

## 9. Orden recomendado de revision

Orden optimo:

```text
1. 01_arquitectura_global.md
2. 09_mapa_configuraciones.md
3. 02_auditoria_firmware_mcu.md
4. 03_auditoria_python_backend.md
5. 04_auditoria_dsp_features.md
6. 05_auditoria_sonificacion_midi.md
7. 07_auditoria_web_ui.md
8. 08_auditoria_tools_capturas_docs.md
9. 10_redundancias_y_deuda_tecnica.md
10. 11_controles_faltantes_y_riesgos.md
11. 12_mapa_criticidad_refactor.md
12. 00_inventario_proyecto.md
13. 06_auditoria_led_matrix_scroll.md
```

Motivo: primero se actualiza la arquitectura y configuracion global; despues los bloques principales; finalmente inventario y LED como complemento.

## 10. Conclusion

La carpeta `docs/auditoria_firmware_final_v1/` debe conservarse porque aporta texto explicativo util para la memoria. La carpeta `docs/auditoria_codigo_detallada/` ya cubre la precision tecnica funcion por funcion. La estrategia correcta es:

```text
usar auditoria_codigo_detallada como fuente tecnica de seguridad
usar auditoria_firmware_final_v1 como fuente narrativa reajustada a final-v4
```

Esto permitira preparar una version esencial/UML mas clara y, al mismo tiempo, tener material redactable para el TFG sin perder la trazabilidad tecnica.
