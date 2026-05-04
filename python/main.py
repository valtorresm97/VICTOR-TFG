from __future__ import annotations

import logging
import time

from arduino.app_utils import App
from arduino.app_bricks.webui_html import ui

from backend_service import create_backend_service
from web_server import EEGWebServer

logger = logging.getLogger("EEG_MAIN")

backend = create_backend_service()
web = EEGWebServer(ui=ui, backend=backend)
web.setup_routes()


def loop():
    backend.step()
    time.sleep(0.02)


App.run(user_loop=loop)
