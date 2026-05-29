# Protocolo de capturas EEG-MIDI multiusuario

## 1. Objetivo

Definir un procedimiento repetible para capturar sesiones EEG-MIDI de varios sujetos despues de los benchmarks, usando un modelo fijo y sin generar plots durante la adquisicion.

El protocolo esta pensado para la placa Arduino UNO Q/Linux del proyecto, con ADS1299-4PAG, App Lab en ejecucion y capturas gestionadas por `python/tools/capture_eeg_quality.py` y `python/capture_manager.py`.

## 2. Alcance y reglas de esta fase

- No se modifican firmware, imports, contratos Bridge ni parametros DSP durante las sesiones.
- No se crean plots durante la captura.
- Las capturas se guardan en `captures/<timestamp>_<condition>/`.
- Cada captura debe contener, como minimo, `eeg_timeseries.csv` y `metadata.json`.
- El analisis offline permitido al terminar cada condicion es textual/CSV: `analyze_eeg_capture.py` y `validate_spectral_features.py`.
- El modelo musical debe permanecer fijo durante todos los sujetos de una misma tanda.
- Las condiciones deben repetirse con el mismo orden, duracion, montaje y consigna verbal.

## 3. Base tecnica verificada en el repositorio

### 3.1 Flujo real de captura

La CLI `capture_eeg_quality.py` no captura directamente desde Bridge. Escribe `state/capture_request.json`; la app App Lab viva, a traves de `CaptureManager`, consume esa solicitud y guarda los bloques EEG reales que ya llegan al backend.

Flujo operativo:

```text
Terminal Linux normal
  -> python/tools/capture_eeg_quality.py
  -> state/capture_request.json
  -> App Lab / python/main.py en ejecucion
  -> CaptureManager
  -> captures/<timestamp>_<condition>/eeg_timeseries.csv
  -> captures/<timestamp>_<condition>/metadata.json
```

Por tanto, antes de lanzar comandos de captura hay que comprobar que la app EEG_MIDI esta corriendo en App Lab sobre el mismo checkout.

### 3.2 Formato CSV generado

`CaptureManager` guarda una fila por muestra con estas columnas:

```text
t_capture_sec,timestamp_unix,block_idx,sample_idx,sample_in_block,status,ch1_uV,ch2_uV,ch3_uV,ch4_uV
```

Aunque el modelo final use CH1 como canal principal, se conservan las cuatro columnas para mantener el contrato `NUM_CH=4`.

### 3.3 Metadata automatica generada

`metadata.json` incluye automaticamente:

- `condition`.
- `duration_requested_sec`.
- `duration_observed_sec`.
- `created_at_utc`.
- `started_unix`.
- `fs_hz_expected`.
- `num_channels`.
- `block_samples_expected`.
- `bridge_event`.
- `value_units`.
- `firmware_pipeline`.
- Bloque `ads1299` con dispositivo esperado, status, LSB, PGA y canales.
- Bloque `rx_summary` con bloques, muestras, gaps, status invalidos y filas CSV.
- Bloque `git` con rama, commit y dirty state.
- `notes`.

La metadata adicional de sujeto/sesion debe escribirse en `--notes` y en la plantilla `docs/04_protocolos_captura/templates/plantilla_sesion_sujeto.md`.

## 4. Preparacion antes de todos los sujetos

### 4.1 Preparacion del repositorio en la placa

```bash
cd /home/arduino/ArduinoApps/eeg_midi
git status
git branch --show-current
git fetch origin
git switch docs/capture-protocol
git pull --ff-only origin docs/capture-protocol
```

Si todavia no se ha subido esta rama a la placa, usar:

```bash
cd /home/arduino/ArduinoApps/eeg_midi
git fetch origin
git switch -c docs/capture-protocol origin/docs/capture-protocol
```

Despues de cambiar de rama, abrir Arduino App Lab, compilar/subir si procede y ejecutar la app `EEG_MIDI`.

### 4.2 Preparacion de carpetas auxiliares

Las capturas se crean automaticamente en `captures/`. Para logs manuales de sesion se recomienda:

```bash
cd /home/arduino/ArduinoApps/eeg_midi
mkdir -p docs/04_protocolos_captura/sesiones_captura logs/capturas
```

No guardar plots en esta fase.

### 4.3 Identificacion anonima

Usar identificadores anonimos:

```bash
SUBJECT=s01
SESSION=$(date +"%Y%m%d")
MONTAGE=fp1_fp2_ch1_only
MODEL=final_v3_fixed_model
OPERATOR=victor
ADS_MODE=bias_ch1_only_loff_off
```

No usar nombres reales en el nombre de condicion, en `metadata.json` ni en la plantilla de sesion.

### 4.4 Comprobar contexto de git y Python

```bash
{
  echo "subject=$SUBJECT"
  echo "session=$SESSION"
  echo "branch=$(git branch --show-current)"
  echo "commit=$(git rev-parse HEAD)"
  echo "dirty=$(git status --short | wc -l)"
  echo "python=$(python3 --version 2>&1)"
  echo "date=$(date -Iseconds)"
} | tee "logs/capturas/${SESSION}_${SUBJECT}_context.txt"
```

La sesion ideal debe hacerse con `dirty=0`. Si hay cambios locales, anotarlos expresamente en la plantilla.

## 5. Preparacion hardware

### 5.1 Material minimo

- Arduino UNO Q con la aplicacion EEG_MIDI cargada.
- PCB/interfaz ADS1299-4PAG.
- Electrodos y cables identificados.
- Electrodo de referencia/BIAS/RLD si esta conectado fisicamente y validado.
- Gel/pasta conductora o electrodos preparados segun el montaje usado.
- Sistema MIDI conectado solo si se quiere registrar la respuesta sonora, manteniendo el mismo modelo.
- Ordenador o navegador para ver la WebUI.

### 5.2 Montaje electrico

Antes de colocar electrodos al sujeto:

1. Confirmar que la placa esta alimentada de forma estable.
2. Confirmar que no hay cables tensos ni conectores medio sueltos.
3. Confirmar que el cable de electrodos no pasa junto a fuentes de 50 Hz, cargadores, transformadores o cables de potencia.
4. Confirmar que el sujeto puede permanecer quieto sin tirar de los cables.
5. Si se usa salida MIDI fisica, no cambiar puerto, instrumento ni escala entre sujetos.

### 5.3 Modo ADS1299 esperado

Para la tanda multiusuario usar el modo final definido por el repositorio para captura real. En esta fase se asume:

```text
ADS_MODE=bias_ch1_only_loff_off
```

No cambiar `ADS_DIAGNOSTIC_MODE` entre sujetos salvo que se vaya a repetir toda la tanda con otro perfil y se documente como sesion distinta.

## 6. Colocacion de electrodos

### 6.1 Regla general

Mantener el mismo montaje durante todos los sujetos de una tanda. Si se cambia montaje, cambiar tambien `MONTAGE` y tratarlo como una tanda distinta.

Montajes recomendados para esta fase:

- `fp1_fp2_ch1_only`: diferencial frontal Fp1-Fp2 en CH1.
- `ear_eeg_ch1_only`: montaje auricular/mastoides si ya se ha validado fisicamente.

### 6.2 Procedimiento de colocacion

1. Explicar al sujeto que la prueba no es diagnostica ni clinica.
2. Retirar objetos que puedan molestar: auriculares, gorras, gafas si interfieren, cables sobre la cara.
3. Preparar la piel de forma suave segun el tipo de electrodo.
4. Colocar CH1P y CH1N segun el montaje elegido.
5. Colocar BIAS/RLD solo si la PCB y el modo activo lo tienen contemplado.
6. Fijar cables con holgura para que los movimientos de mandibula o parpadeos no arrastren electrodos.
7. Esperar 30-60 s antes de la primera captura para que el contacto se estabilice.

### 6.3 Consignas al sujeto

Usar siempre frases cortas y repetibles:

- Ojos abiertos: "Mira a un punto fijo, relajado, sin hablar y parpadeando lo minimo natural".
- Ojos cerrados: "Cierra los ojos, relajate, no aprietes la mandibula y no te duermas".
- Reposo neutro: "Permanece quieto, respira normal y no hagas movimientos voluntarios".
- Parpadeo: "Parpadea de forma marcada cada 2 o 3 segundos hasta que avise".
- Mandibula: "Aprieta o mueve suavemente la mandibula de forma repetida, sin mover la cabeza".

## 7. Comprobaciones previas por sujeto

Antes de la primera captura real de cada sujeto:

```bash
cd /home/arduino/ArduinoApps/eeg_midi
cat state/capture_status.json 2>/dev/null | python3 -m json.tool || true
cat state/snapshot.json 2>/dev/null | python3 -m json.tool | head -80 || true
```

Comprobar en la WebUI:

- La app esta en estado vivo/running.
- Hay tasa de frames cercana a 250 Hz.
- Hay tasa de bloques cercana a 31.25 bloques/s.
- `window_ready` llega a verdadero tras unos segundos.
- RMS y pico-pico no estan permanentemente en mV durante reposo.
- No hay contador creciente de `invalid_status`, `sample_gaps` o `block_gaps`.
- La senal no esta plana.
- La senal no esta saturada.
- Si hay 50 Hz dominante, recolocar cables/electrodos antes de grabar.

Captura corta opcional de precheck:

```bash
NOTE_BASE="subject=${SUBJECT};session=${SESSION};montage=${MONTAGE};model=${MODEL};operator=${OPERATOR};ads_mode=${ADS_MODE}"
python3 python/tools/capture_eeg_quality.py \
  --condition "${SUBJECT}_${SESSION}_${MONTAGE}_00_precheck_10s" \
  --duration 10 \
  --timeout-extra 60 \
  --notes "${NOTE_BASE};condition=precheck;order=00"
```

Analizar precheck si hay dudas:

```bash
DIR=$(ls -td captures/*_${SUBJECT}_${SESSION}_${MONTAGE}_00_precheck_10s /app/captures/*_${SUBJECT}_${SESSION}_${MONTAGE}_00_precheck_10s 2>/dev/null | head -1)
echo "$DIR"
python3 python/tools/analyze_eeg_capture.py "$DIR"
cat "$DIR/quality_report.md"
```

## 8. Orden fijo de pruebas

Usar este orden para todos los sujetos. El objetivo es separar condiciones limpias, comparables y artefactos controlados.

| Orden | Condicion | Nombre corto | Duracion | Uso principal |
| --- | --- | --- | ---: | --- |
| 00 | Precheck quieto | `precheck_10s` | 10 s | Ver contacto y app viva. |
| 01 | Ojos abiertos en reposo | `eyes_open_rest_60s` | 60 s | Baseline con entrada visual. |
| 02 | Ojos cerrados en reposo | `eyes_closed_rest_60s` | 60 s | Comparacion alpha/relajacion. |
| 03 | Reposo neutro quieto | `quiet_rest_60s` | 60 s | Baseline general para modelo fijo. |
| 04 | Parpadeo controlado | `blink_artifact_30s` | 30 s | Artefacto ocular. |
| 05 | Mandibula controlada | `jaw_artifact_30s` | 30 s | Artefacto EMG. |
| 06 | Repeticion ojos abiertos opcional | `eyes_open_repeat_30s` | 30 s | Comprobar recuperacion tras artefactos. |

Descanso recomendado entre condiciones: 15-30 s. En ese descanso no cambiar electrodos, modelo, root, main note, escala ni volumen.

## 9. Comandos rapidos de captura

Preparar variables una sola vez:

```bash
cd /home/arduino/ArduinoApps/eeg_midi
SUBJECT=s01
SESSION=$(date +"%Y%m%d")
MONTAGE=fp1_fp2_ch1_only
MODEL=final_v3_fixed_model
OPERATOR=victor
ADS_MODE=bias_ch1_only_loff_off
NOTE_BASE="subject=${SUBJECT};session=${SESSION};montage=${MONTAGE};model=${MODEL};operator=${OPERATOR};ads_mode=${ADS_MODE}"
```

### 9.1 Iniciar una captura individual

```bash
python3 python/tools/capture_eeg_quality.py \
  --condition "${SUBJECT}_${SESSION}_${MONTAGE}_01_eyes_open_rest_60s" \
  --duration 60 \
  --timeout-extra 120 \
  --notes "${NOTE_BASE};condition=eyes_open_rest;order=01;instruction=mirar_punto_fijo"
```

### 9.2 Parar una captura activa manualmente

Usar solo si te equivocas de condicion, el sujeto se mueve mucho o se cae un electrodo:

```bash
python3 - <<'PY'
import sys, time, uuid
from pathlib import Path
sys.path.insert(0, "python")
from app_state import atomic_write_json
from runtime_config import runtime_state_dir
root = Path.cwd()
request = {
    "command": "stop",
    "request_id": uuid.uuid4().hex,
    "requested_at_unix": time.time(),
}
atomic_write_json(runtime_state_dir(root) / "capture_request.json", request, indent=2, sort_keys=True)
print("stop requested")
PY
```

### 9.3 Secuencia completa por sujeto

```bash
python3 python/tools/capture_eeg_quality.py --condition "${SUBJECT}_${SESSION}_${MONTAGE}_01_eyes_open_rest_60s" --duration 60 --timeout-extra 120 --notes "${NOTE_BASE};condition=eyes_open_rest;order=01"
python3 python/tools/capture_eeg_quality.py --condition "${SUBJECT}_${SESSION}_${MONTAGE}_02_eyes_closed_rest_60s" --duration 60 --timeout-extra 120 --notes "${NOTE_BASE};condition=eyes_closed_rest;order=02"
python3 python/tools/capture_eeg_quality.py --condition "${SUBJECT}_${SESSION}_${MONTAGE}_03_quiet_rest_60s" --duration 60 --timeout-extra 120 --notes "${NOTE_BASE};condition=quiet_rest;order=03"
python3 python/tools/capture_eeg_quality.py --condition "${SUBJECT}_${SESSION}_${MONTAGE}_04_blink_artifact_30s" --duration 30 --timeout-extra 90 --notes "${NOTE_BASE};condition=blink_artifact;order=04;instruction=blink_every_2_3s"
python3 python/tools/capture_eeg_quality.py --condition "${SUBJECT}_${SESSION}_${MONTAGE}_05_jaw_artifact_30s" --duration 30 --timeout-extra 90 --notes "${NOTE_BASE};condition=jaw_artifact;order=05;instruction=jaw_movement_no_head"
python3 python/tools/capture_eeg_quality.py --condition "${SUBJECT}_${SESSION}_${MONTAGE}_06_eyes_open_repeat_30s" --duration 30 --timeout-extra 90 --notes "${NOTE_BASE};condition=eyes_open_repeat;order=06"
```

### 9.4 Localizar la ultima captura

```bash
ls -td captures/* /app/captures/* 2>/dev/null | head -10
```

Para una condicion concreta:

```bash
COND="${SUBJECT}_${SESSION}_${MONTAGE}_01_eyes_open_rest_60s"
DIR=$(ls -td captures/*_${COND} /app/captures/*_${COND} 2>/dev/null | head -1)
echo "$DIR"
ls -la "$DIR"
```

### 9.5 Analizar una captura sin generar plots

```bash
python3 python/tools/analyze_eeg_capture.py "$DIR"
python3 python/tools/validate_spectral_features.py "$DIR" --channel 0 --window-sec 4 --hop-samples 64
cat "$DIR/quality_report.md"
cat "$DIR/spectral_validation_report.md"
```

### 9.6 Analizar todas las capturas del sujeto

```bash
for DIR in $(ls -td captures/*_${SUBJECT}_${SESSION}_${MONTAGE}_* /app/captures/*_${SUBJECT}_${SESSION}_${MONTAGE}_* 2>/dev/null); do
  echo "=== $DIR ==="
  python3 python/tools/analyze_eeg_capture.py "$DIR"
  python3 python/tools/validate_spectral_features.py "$DIR" --channel 0 --window-sec 4 --hop-samples 64
  tail -n +1 "$DIR/quality_report.md" | head -60
  tail -n +1 "$DIR/spectral_validation_report.md" | head -60
 done
```

## 10. Convencion de nombres

Formato recomendado para `--condition`:

```text
<subject>_<session>_<montage>_<order>_<condition>_<duration>
```

Ejemplos:

```text
s01_20260528_fp1_fp2_ch1_only_01_eyes_open_rest_60s
s01_20260528_fp1_fp2_ch1_only_02_eyes_closed_rest_60s
s01_20260528_fp1_fp2_ch1_only_04_blink_artifact_30s
```

Reglas:

- Solo minusculas, numeros, guion bajo y guion medio.
- No incluir nombres reales.
- No incluir espacios ni tildes.
- Mantener `order` con dos digitos.
- Mantener la duracion en el nombre.
- Si se repite una condicion por error o mejora, no borrar la anterior: usar sufijo `repeat2` o anotar en plantilla cual se acepta.

## 11. Metadata adicional a guardar

### 11.1 En `--notes`

Usar pares `clave=valor` separados por `;`:

```text
subject=s01;session=20260528;montage=fp1_fp2_ch1_only;model=final_v3_fixed_model;operator=victor;ads_mode=bias_ch1_only_loff_off;condition=eyes_open_rest;order=01;instruction=mirar_punto_fijo
```

Campos recomendados:

| Campo | Ejemplo | Motivo |
| --- | --- | --- |
| `subject` | `s01` | Identificacion anonima. |
| `session` | `20260528` | Agrupar capturas del dia. |
| `montage` | `fp1_fp2_ch1_only` | Trazabilidad del montaje. |
| `model` | `final_v3_fixed_model` | Modelo fijo usado. |
| `operator` | `victor` | Responsable de adquisicion. |
| `ads_mode` | `bias_ch1_only_loff_off` | Trazabilidad ADS1299. |
| `condition` | `eyes_open_rest` | Condicion experimental. |
| `order` | `01` | Orden de presentacion. |
| `instruction` | `mirar_punto_fijo` | Consigna usada. |
| `electrode_contact` | `good/doubt/bad` | Calidad subjetiva inicial. |
| `movement_notes` | `none/blink/jaw/cable` | Incidencias observadas. |
| `environment` | `lab_quiet` | Entorno de captura. |

### 11.2 En la plantilla de sesion

La plantilla debe recoger:

- Consentimiento verbal/informado segun alcance academico.
- Sujeto anonimizado.
- Fecha, hora y operador.
- Rama, commit y dirty state.
- Montaje y ubicacion de electrodos.
- Configuracion musical fija.
- Orden de condiciones.
- Capturas aceptadas/repetidas/descartadas.
- Incidencias.
- Decision final de validez.

## 12. Criterios de aceptacion y descarte

### 12.1 Aceptar una captura limpia si

- Existe `eeg_timeseries.csv`.
- Existe `metadata.json`.
- `rx_summary.invalid_status_total == 0`.
- `rx_summary.sample_gaps_total == 0`.
- `rx_summary.block_gaps_total == 0`.
- La frecuencia efectiva esta cerca de 250 Hz.
- La duracion observada es coherente con la duracion pedida.
- Hay suficientes ventanas limpias para la condicion.
- No domina 50 Hz de forma persistente.
- No hay saturacion ni seÃ±al plana.
- RMS y pico-pico son compatibles con EEG real y no estan en mV en la mayoria de la captura.

### 12.2 Repetir o descartar si

- Se desconecta un electrodo.
- El sujeto habla, rie o mueve la cabeza durante una condicion limpia.
- Aparece `invalid_status_total > 0`.
- Aparecen gaps de muestra o bloque.
- La captura queda vacia o con duracion muy inferior a la pedida.
- La senal esta plana.
- La senal esta saturada o con clipping persistente.
- El RMS esta en rango de mV durante reposo.
- 50 Hz domina la captura y no se corrige recolocando cables.
- Se cambio root/main/scale/modelo durante la captura.
- Se cambio el montaje entre condiciones sin documentarlo.

### 12.3 Criterio para artefactos

Las capturas `blink_artifact_30s` y `jaw_artifact_30s` no se descartan por contener artefactos: se descartan solo si hay fallo tecnico de adquisicion, gaps, status invalidos, desconexion o instruccion mal ejecutada.

## 13. Checklist rapido por sujeto

Antes:

- [ ] Sujeto anonimizado: `sXX`.
- [ ] Rama correcta.
- [ ] Commit anotado.
- [ ] App Lab ejecutandose.
- [ ] Modelo musical fijo confirmado.
- [ ] Montaje elegido y anotado.
- [ ] Electrodos colocados y cables fijados.
- [ ] WebUI con datos vivos.
- [ ] RMS plausible.
- [ ] Sin gaps/status invalidos visibles.

Durante:

- [ ] Orden fijo respetado.
- [ ] Duracion correcta por condicion.
- [ ] Consigna verbal repetida igual.
- [ ] Sin hablar durante condiciones limpias.
- [ ] Descansos entre condiciones.
- [ ] Incidencias anotadas.

Despues:

- [ ] Localizar directorios `captures/`.
- [ ] Ejecutar `analyze_eeg_capture.py`.
- [ ] Ejecutar `validate_spectral_features.py`.
- [ ] Revisar `quality_report.md`.
- [ ] Revisar `spectral_validation_report.md`.
- [ ] Rellenar plantilla de sesion.
- [ ] Marcar capturas aceptadas/repetidas/descartadas.

## 14. Entrega por sesion

Por cada sujeto debe quedar:

```text
captures/<timestamp>_<condition>/eeg_timeseries.csv
captures/<timestamp>_<condition>/metadata.json
captures/<timestamp>_<condition>/quality_report.md
captures/<timestamp>_<condition>/quality_report.json
captures/<timestamp>_<condition>/spectral_validation_report.md
captures/<timestamp>_<condition>/spectral_validation_report.json
docs/04_protocolos_captura/sesiones_captura/<session>_<subject>_sesion.md
logs/capturas/<session>_<subject>_context.txt
```

No borrar capturas descartadas. Marcar en la plantilla que no se usaran como evidencia principal.







