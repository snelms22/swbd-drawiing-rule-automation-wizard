"""Main window: section list | section editor | page preview, with warnings below.

Every edit re-runs the layout engine and redraws the preview, so what you see is always
the current result of the layout rules.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QHBoxLayout, QListWidget, QMainWindow, QMessageBox, QPushButton,
    QScrollArea, QSplitter, QVBoxLayout, QWidget,
)

from src.layout.page_fitter import fit_pages
from src.layout.settings import LayoutSettings
from src.model.switchboard import Section, Switchboard
from src.ui.page_preview import PagePreview
from src.ui.section_editor import SectionEditor


class MainWindow(QMainWindow):
    def __init__(self, settings: LayoutSettings, switchboard: Switchboard,
                 autocad_settings=None, autocad_settings_problem: str = "", catalog=None):
        super().__init__()
        self._catalog = catalog     # library block sizes/terminals; None = placeholders only
        self._settings = settings
        self._switchboard = switchboard
        self._autocad_settings = autocad_settings
        self.setWindowTitle(f"Hyper Switchboard Configurator - {switchboard.name}")
        self.resize(1500, 900)

        # Left: the lineup. Sections have no names; the list shows "Section n".
        self.section_list = QListWidget()
        self.section_list.currentRowChanged.connect(self._section_selected)
        self.push_check = QCheckBox("Push to next page")
        self.link_check = QCheckBox("Link with next section")
        self.push_check.toggled.connect(self._page_controls_changed)
        self.link_check.toggled.connect(self._page_controls_changed)

        list_buttons = QHBoxLayout()
        for text, action in (("+ Add", self._add_section), ("Remove", self._remove_section),
                             ("▲", self._move_up), ("▼", self._move_down)):
            button = QPushButton(text)
            button.clicked.connect(action)
            list_buttons.addWidget(button)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(self.section_list)
        left_layout.addLayout(list_buttons)
        left_layout.addWidget(self.push_check)
        left_layout.addWidget(self.link_check)

        self.generate_button = QPushButton("Generate drawing")
        self.generate_button.clicked.connect(self._generate_drawing)
        if autocad_settings is None:
            self.generate_button.setEnabled(False)
            self.generate_button.setToolTip(autocad_settings_problem or "AutoCAD settings not loaded.")
        left_layout.addWidget(self.generate_button)

        # Middle: editor for the selected section.
        self.editor = SectionEditor(settings)
        self.editor.changed.connect(self.refresh)
        editor_scroll = QScrollArea()
        editor_scroll.setWidgetResizable(True)
        editor_scroll.setWidget(self.editor)

        # Right: page preview (scrolls when there are many pages).
        self.preview = PagePreview(settings)
        preview_scroll = QScrollArea()
        preview_scroll.setWidgetResizable(True)
        preview_scroll.setWidget(self.preview)

        top_splitter = QSplitter(Qt.Horizontal)
        top_splitter.addWidget(left)
        top_splitter.addWidget(editor_scroll)
        top_splitter.addWidget(preview_scroll)
        editor_scroll.setMinimumWidth(460)   # room for the editor's buttons and slot fields
        top_splitter.setSizes([160, 480, 860])

        # Bottom: warnings
        self.warning_list = QListWidget()

        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.addWidget(top_splitter)
        main_splitter.addWidget(self.warning_list)
        main_splitter.setSizes([750, 150])
        self.setCentralWidget(main_splitter)

        self._rebuild_list(select_row=0)
        self.refresh()

    # --- Section list -------------------------------------------------------------------

    def _sections(self) -> list[Section]:
        return self._switchboard.sections

    def _rebuild_list(self, select_row):
        self.section_list.blockSignals(True)
        self.section_list.clear()
        for number in range(1, len(self._sections()) + 1):
            self.section_list.addItem(f"Section {number}")
        self.section_list.blockSignals(False)
        if self._sections():
            self.section_list.setCurrentRow(min(max(select_row, 0), len(self._sections()) - 1))
        self._section_selected(self.section_list.currentRow())

    def _selected(self) -> Section | None:
        row = self.section_list.currentRow()
        return self._sections()[row] if 0 <= row < len(self._sections()) else None

    def _section_selected(self, row):
        section = self._selected()
        self.editor.load(section, row + 1)
        for check, value in ((self.push_check, section.push_to_next_page if section else False),
                             (self.link_check, section.link_with_next if section else False)):
            check.blockSignals(True)
            check.setChecked(value)
            check.setEnabled(section is not None)
            check.blockSignals(False)

    def _page_controls_changed(self, *_):
        section = self._selected()
        if section is not None:
            section.push_to_next_page = self.push_check.isChecked()
            section.link_with_next = self.link_check.isChecked()
            self.refresh()

    def _add_section(self):
        # New sections go right after the selected one (or at the end).
        row = self.section_list.currentRow()
        insert_at = row + 1 if row >= 0 else len(self._sections())
        self._sections().insert(insert_at, Section())
        self._rebuild_list(insert_at)
        self.refresh()

    def _remove_section(self):
        row = self.section_list.currentRow()
        if row >= 0:
            del self._sections()[row]
            self._rebuild_list(row)
            self.refresh()

    def _move_up(self):
        self._swap(self.section_list.currentRow(), -1)

    def _move_down(self):
        self._swap(self.section_list.currentRow(), +1)

    def _swap(self, row, step):
        sections = self._sections()
        other = row + step
        if 0 <= row < len(sections) and 0 <= other < len(sections):
            sections[row], sections[other] = sections[other], sections[row]
            self._rebuild_list(other)
            self.refresh()

    # --- AutoCAD ------------------------------------------------------------------------

    def _generate_drawing(self):
        # Imported here so the app still opens (preview only) where AutoCAD isn't installed.
        from src.autocad.generate import GenerateError, generate_drawing

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            result = generate_drawing(self._switchboard, self._settings, self._autocad_settings,
                                      self._catalog)
        except GenerateError as error:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "Drawing not made", str(error))
            return
        except Exception as error:     # AutoCAD/COM errors: show them rather than crash
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "AutoCAD problem", f"{type(error).__name__}: {error}")
            return
        QApplication.restoreOverrideCursor()
        message = f"Drawing saved:\n{result.drawing_file}"
        if result.problems:
            message += "\n\nPlease check:\n" + "\n".join(f"- {p}" for p in result.problems)
        QMessageBox.information(self, "Drawing made", message)

    # --- Layout -------------------------------------------------------------------------

    def refresh(self):
        result = fit_pages(self._switchboard, self._settings, self._catalog)
        self.preview.show_layout(result)
        self.warning_list.clear()
        if result.warnings:
            self.warning_list.addItems(["⚠ " + text for text in result.warnings])
        else:
            self.warning_list.addItem("No warnings.")
