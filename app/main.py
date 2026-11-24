"""Entry point for each Flet session (a desktop window or a browser tab)."""

import logging
import os
import threading
from pathlib import Path

import flet as ft

from .config import ICON_PATH

from . import theme as t
from .core import StudyCore
from .login import SignIn
from .shell import Shell

APP_NAME = "StudyGenie – AI Study Companion"

_core = None
_core_lock = threading.Lock()


def shared_core():
    """One data core for the whole server. A desktop window and phone
    browsers then share the same in-memory data instead of overwriting
    each other's saves."""
    global _core
    with _core_lock:
        if _core is None:
            # STUDYGENIE_DB points at another data file (used for testing).
            custom = os.environ.get("STUDYGENIE_DB")
            _core = StudyCore(Path(custom), Path(custom).with_suffix(".json")) if custom else StudyCore()
        return _core


def main(page: ft.Page):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    page.title = APP_NAME
    page.bgcolor = t.BG
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = page.dark_theme = t.page_theme()
    page.padding = 0
    page.spacing = 0
    try:  # desktop window only
        page.window.min_width, page.window.min_height = 380, 600
        if ICON_PATH.exists():
            page.window.icon = str(ICON_PATH)
        page.window.width, page.window.height = 1280, 820
    except AttributeError:
        pass

    core = shared_core()

    def show_sign_in():
        SignIn(page, core, on_ready=start_app).show()

    def start_app():
        Shell(page, core, on_sign_out=show_sign_in).start()

    show_sign_in()
