"""Starts the Switchboard Configurator.

Run from the project folder (with the virtual environment activated):
    python run_configurator.py

Layout numbers are read from config/layout_settings.json when the app starts.
After editing that file, close and reopen the app to see the change.
"""
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from src.autocad.settings import load_autocad_settings
from src.layout.block_catalog import load_block_catalog
from src.layout.settings import SettingsError, load_settings
from src.model.devices import load_device_settings
from src.model.drawing_info import load_drawing_info_settings
from src.model.switchboard import new_switchboard
from src.ui.main_window import MainWindow

# The folder holding config/, catalog/, templates/, ... In the released app (built by
# PyInstaller) they are unpacked next to the program, in sys._MEIPASS.
PROJECT_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
SETTINGS_FILE = PROJECT_ROOT / "config" / "layout_settings.json"
AUTOCAD_SETTINGS_FILE = PROJECT_ROOT / "config" / "autocad_settings.json"
BLOCK_CATALOG_FILE = PROJECT_ROOT / "catalog" / "blocks.json"
DRAWING_INFO_FILE = PROJECT_ROOT / "config" / "drawing_info.json"
DEVICES_FILE = PROJECT_ROOT / "config" / "devices.json"


def main() -> int:
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(PROJECT_ROOT / "assets" / "swbd.ico")))
    try:
        settings = load_settings(SETTINGS_FILE)
    except SettingsError as error:
        QMessageBox.critical(None, "Problem with layout settings", str(error))
        return 1
    try:
        drawing_info_settings = load_drawing_info_settings(DRAWING_INFO_FILE)
        device_settings = load_device_settings(DEVICES_FILE)
    except SettingsError as error:
        QMessageBox.critical(None, "Problem with drawing information settings", str(error))
        return 1
    # The app still opens without AutoCAD settings; only "Generate drawing" is disabled.
    autocad_settings, autocad_problem = None, ""
    try:
        autocad_settings = load_autocad_settings(AUTOCAD_SETTINGS_FILE, PROJECT_ROOT)
    except SettingsError as error:
        autocad_problem = str(error)
    try:
        catalog = load_block_catalog(BLOCK_CATALOG_FILE)
    except SettingsError as error:
        QMessageBox.warning(None, "Block catalog problem",
                            f"{error}\n\nMain breakers will be shown as placeholder boxes.")
        catalog = None
    window = MainWindow(settings, new_switchboard(), autocad_settings, autocad_problem, catalog,
                        drawing_info_settings, device_settings)
    window.show()
    window.show_updates_since_last_session(PROJECT_ROOT / "CHANGELOG.md")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
