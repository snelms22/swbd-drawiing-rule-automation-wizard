"""The "Drawing Information" page (decisions 2026-10-19/20): the job number (required) and
the item name (from Arena; pasted in for now, "Fetch from Arena" comes later).

Shown in the middle of the window when "Drawing Information" (the first entry in the section
list) is selected. Changes the switchboard's DrawingInfo directly and emits `changed`. The
preview shows what goes in the title block.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout, QGroupBox, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

from src.model.drawing_info import (
    drawing_number, fgd_number, item_name_lines, job_number_problem,
)


class DrawingInfoEditor(QWidget):
    changed = Signal()

    def __init__(self, settings):
        super().__init__()
        self._settings = settings          # DrawingInfoSettings
        self._switchboard = None

        title = QLabel("General Drawing Information")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.job_number = QLineEdit()
        self.job_number.setPlaceholderText("required, e.g. 011484")
        self.job_number.textEdited.connect(lambda text: self._store("job_number", text.strip()))
        self.item_name = QLineEdit()
        self.item_name.setPlaceholderText("copy from Arena, e.g. SWBD, 5000A, 480V, 100KAIC, ...")
        self.item_name.textEdited.connect(lambda text: self._store("item_name", text.strip()))
        self.missing = QLabel()
        self.missing.setStyleSheet("color: #b00020;")
        self.missing.setWordWrap(True)

        job_box = QGroupBox("Job")
        form = QFormLayout(job_box)
        form.addRow("Job number", self.job_number)
        form.addRow("Item name", self.item_name)
        form.addRow(self.missing)
        arena = QPushButton("Fetch from Arena")
        arena.setEnabled(False)
        arena.setToolTip("Coming later: fill the item name from Arena by job number.")
        form.addRow(arena)

        preview_box = QGroupBox("Title block preview")
        self.preview = QLabel()
        self.preview.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.preview.setWordWrap(True)
        QVBoxLayout(preview_box).addWidget(self.preview)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(job_box)
        layout.addWidget(preview_box)
        layout.addStretch()

    def load(self, switchboard):
        self._switchboard = switchboard
        for widget, value in ((self.job_number, switchboard.drawing_info.job_number),
                              (self.item_name, switchboard.drawing_info.item_name)):
            widget.blockSignals(True)
            widget.setText(value)
            widget.blockSignals(False)
        self.refresh_preview()

    def refresh_preview(self):
        if self._switchboard is None:
            return
        problem = job_number_problem(self._switchboard)
        self.missing.setText(problem)
        self.missing.setVisible(bool(problem))
        job = self._switchboard.drawing_info.job_number.strip()
        line_1, line_2 = item_name_lines(self._switchboard.drawing_info.item_name,
                                         self._settings.item_name_line_length)
        if not job:
            numbers = "FGD: (job number)     DWG: (job number)"
        else:
            types = ", ".join(drawing_number(self._switchboard, self._settings, kind)
                              for kind in self._settings.drawing_number_formats)
            numbers = f"FGD: {fgd_number(self._switchboard, self._settings)}     DWG: {types}"
        self.preview.setText(f"ITEM NAME:\n  {line_1 or '(item name)'}\n  {line_2}\n{numbers}")

    def _store(self, name, value):
        if self._switchboard is None:
            return
        setattr(self._switchboard.drawing_info, name, value)
        self.refresh_preview()
        self.changed.emit()
