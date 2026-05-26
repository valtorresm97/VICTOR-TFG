from __future__ import annotations

# -----------------------------------------------------------------------------
# Persistencia ligera del estado runtime entre backend y dashboard.
# Este archivo:
#   1) asegura la carpeta state/
#   2) limpia snapshot/history cuando corresponde
#   3) serializa de forma segura a JSON
#   4) escribe de forma atómica para evitar lecturas parciales
#   5) permite lectura tolerante a errores
# -----------------------------------------------------------------------------

import json
import math
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from runtime_config import runtime_state_dir

# -----------------------------------------------------------------------------
# Rutas de persistencia del estado público.
# -----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = runtime_state_dir(PROJECT_ROOT)
SNAPSHOT_PATH = STATE_DIR / "snapshot.json"
HISTORY_PATH = STATE_DIR / "history.json"

# -----------------------------------------------------------------------------
# Sentinel interno para distinguir:
#   - "no se ha pasado default"
#   - "el default explícito es None"
# -----------------------------------------------------------------------------
_MISSING = object()


# -----------------------------------------------------------------------------
# Asegura que exista el directorio de estado.
# -----------------------------------------------------------------------------
def ensure_state_dir() -> None:
    """Crea la carpeta de estado si no existe."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------------------------------------------------------
# Limpieza del estado runtime público.
# Se usa al arrancar o detener el backend para evitar datos residuales.
# -----------------------------------------------------------------------------
def clear_runtime_state() -> None:
    """Elimina snapshot e history de la ejecución anterior."""
    ensure_state_dir()
    for path in (SNAPSHOT_PATH, HISTORY_PATH):
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass


# -----------------------------------------------------------------------------
# Conversión segura a JSON:
#   - elimina NaN / inf
#   - convierte numpy scalars/arrays cuando existen
#   - degrada a str cuando no haya mejor opción
# -----------------------------------------------------------------------------
def _json_safe(obj: Any):
    """Convierte un objeto arbitrario a una estructura segura para JSON."""
    if obj is None or isinstance(obj, (str, bool, int)):
        return obj

    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None

    try:
        if hasattr(obj, "item"):
            return _json_safe(obj.item())
    except Exception:
        pass

    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]

    try:
        if hasattr(obj, "tolist"):
            return _json_safe(obj.tolist())
    except Exception:
        pass

    try:
        return str(obj)
    except Exception:
        return None


# -----------------------------------------------------------------------------
# Escritura atómica en disco:
#   - se escribe primero en temporal
#   - se hace flush + fsync
#   - luego replace atómico sobre el destino
#
# Esto es clave para evitar que el dashboard lea un JSON a medio escribir.
# -----------------------------------------------------------------------------
def _atomic_write_json(path: Path, payload: dict) -> None:
    """Escribe un JSON de forma atómica sobre el path destino."""
    ensure_state_dir()

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=str(path.parent),
        delete=False,
    ) as tmp:
        json.dump(payload, tmp, ensure_ascii=False, separators=(",", ":"))
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = tmp.name

    os.replace(tmp_path, path)


# -----------------------------------------------------------------------------
# Construcción del snapshot público.
# Aquí se reduce el payload a una forma segura/estable para consumo de UI.
# Además se añade published_at_unix, que representa el instante físico de
# publicación del JSON, no la edad lógica del dato EEG.
# -----------------------------------------------------------------------------
def _make_public_snapshot(snapshot: dict) -> dict:
    """Convierte el snapshot interno del backend en un snapshot público JSON."""
    out = _json_safe(snapshot if isinstance(snapshot, dict) else {})
    if not isinstance(out, dict):
        out = {}
    out["published_at_unix"] = time.time()
    return out


# -----------------------------------------------------------------------------
# Publicación del snapshot live.
# -----------------------------------------------------------------------------
def publish_snapshot(snapshot: dict) -> None:
    """Publica el snapshot live actual en snapshot.json."""
    _atomic_write_json(SNAPSHOT_PATH, _make_public_snapshot(snapshot))


# -----------------------------------------------------------------------------
# Publicación del history ligero.
# -----------------------------------------------------------------------------
def publish_history(history: dict) -> None:
    """Publica el histórico resumido en history.json."""
    _atomic_write_json(
        HISTORY_PATH,
        {"published_at_unix": time.time(), "history": _json_safe(history)},
    )


# -----------------------------------------------------------------------------
# Publicación conjunta del estado runtime.
# Se usa normalmente para la primera publicación consistente.
# -----------------------------------------------------------------------------
def publish_runtime_state(snapshot: dict, history: dict) -> None:
    """Publica snapshot e history de forma secuencial."""
    publish_snapshot(snapshot)
    publish_history(history)


# -----------------------------------------------------------------------------
# Lectura tolerante del snapshot.
# Mejora respecto a la versión anterior:
#   - ahora se puede pasar default=None de verdad
#   - si no se pasa default, se mantiene el comportamiento típico ({})
# -----------------------------------------------------------------------------
def read_snapshot(default: Any = _MISSING):
    """Lee snapshot.json y devuelve default si falla."""
    if default is _MISSING:
        default = {}

    try:
        with open(SNAPSHOT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


# -----------------------------------------------------------------------------
# Lectura tolerante del history.
# Igual que read_snapshot, pero con un default razonable para history.
# -----------------------------------------------------------------------------
def read_history(default: Any = _MISSING):
    """Lee history.json y devuelve default si falla."""
    if default is _MISSING:
        default = {"history": {}}

    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default
