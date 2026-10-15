"""Makes the app's icon images: the letters "SWBD" for now (decision 2026-10-15; a picture
comes in a later update). Run once after changing the look; the images are kept in
assets/ and used by the app window, the desktop shortcut and the AutoCAD ribbon button.

    python distribution/icons.py

Run it normally (not with QT_QPA_PLATFORM=offscreen): offscreen Qt has no fonts and draws
empty boxes instead of letters.
"""
import sys
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS = PROJECT_ROOT / "assets"

BACKGROUND = QColor("#1F4E79")   # dark blue
LETTERS = QColor("#FFFFFF")
TEXT = "SWBD"


def draw_icon(size: int) -> QImage:
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.TextAntialiasing)
    corner = size * 0.15
    painter.setBrush(BACKGROUND)
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(QRectF(0, 0, size, size), corner, corner)
    font = QFont("Arial")
    font.setBold(True)
    font.setPixelSize(max(5, int(size * 0.34)))
    painter.setFont(font)
    painter.setPen(LETTERS)
    painter.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, TEXT)
    painter.end()
    return image


def main() -> int:
    app = QGuiApplication(sys.argv)   # Qt needs this to draw text
    ASSETS.mkdir(exist_ok=True)
    draw_icon(256).save(str(ASSETS / "swbd.ico"))        # app window, desktop shortcut
    draw_icon(256).save(str(ASSETS / "swbd_256.png"))
    draw_icon(32).save(str(ASSETS / "swbd_32.png"))      # AutoCAD ribbon, large button
    draw_icon(16).save(str(ASSETS / "swbd_16.png"))      # AutoCAD ribbon, small button
    print(f"Icons written to {ASSETS}")
    del app
    return 0


if __name__ == "__main__":
    sys.exit(main())
