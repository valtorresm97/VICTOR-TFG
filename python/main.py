from __future__ import annotations

import time

from arduino.app_utils import App

from backend_service import create_backend_service
from web_server import EEGWebServer

backend = create_backend_service()
web = EEGWebServer(backend=backend)
backend.start()
web.start()


def loop():
    backend.loop()
    snap = backend.get_latest_snapshot()
    if snap:
        web.publish_snapshot(snap)
    time.sleep(0.02)  # evita busy-loop sin bloquear la recepción Bridge


App.run(user_loop=loop)
