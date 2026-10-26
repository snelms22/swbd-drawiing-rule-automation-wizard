"""Small widgets shared by the editors."""
from PySide6.QtWidgets import QComboBox


class ScrollSafeComboBox(QComboBox):
    """A drop-down the mouse wheel never changes while it is closed (Sammy, 2026-10-23).

    A plain QComboBox changes its choice when the wheel turns over it, so scrolling down the
    editor could quietly change a breaker's settings. Here a closed drop-down passes the wheel
    on to the editor's scroll area instead. Once the list is open (clicked), the wheel scrolls
    the list as usual: the open list is a separate widget and doesn't come through here.
    """

    def wheelEvent(self, event):
        event.ignore()      # an ignored wheel event goes to the parent: the editor scrolls
