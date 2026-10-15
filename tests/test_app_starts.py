"""The app's window code loads and the window opens (with no AutoCAD, offscreen).

Most tests check layout rules and never import the window. This one catches a broken
window module before a release does (2026-10-15: a typo in main_window.py was only found
when the packaged app failed to start).
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from src.layout.block_catalog import load_block_catalog  # noqa: E402
from src.layout.settings import load_settings  # noqa: E402
from src.model.switchboard import new_switchboard  # noqa: E402
from src.ui.main_window import MainWindow  # noqa: E402
from src.version import VERSION  # noqa: E402


def test_main_window_opens_with_the_real_settings():
    app = QApplication.instance() or QApplication([])
    window = MainWindow(load_settings("config/layout_settings.json"), new_switchboard(),
                        None, "no AutoCAD in tests", load_block_catalog("catalog/blocks.json"))
    assert window.windowTitle() == f"Switchboard Configurator {VERSION} - Untitled"
    window._unsaved = False
    window.close()
    del app
