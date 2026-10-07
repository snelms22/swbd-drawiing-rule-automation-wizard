"""Main window: section table on the left, page preview on the right, warnings below.

Every edit in the table re-runs the layout engine and redraws the preview, so what you
see is always the current result of the page-fitting rules.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QHeaderView, QListWidget, QMainWindow, QPushButton, QScrollArea,
    QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.layout.page_fitter import fit_pages
from src.layout.settings import LayoutSettings
from src.model.switchboard import Section, Switchboard
from src.ui.page_preview import PagePreview

# Table columns, in order.
COL_NAME, COL_WIDTH, COL_HEIGHT, COL_PUSH, COL_LINK = range(5)
COLUMN_TITLES = ["Name", "Width", "Height", "Push", "Link next"]
# Hover text on the column titles, explaining the short names.
COLUMN_TOOLTIPS = [
    "Section name",
    "Outermost component to outermost component (dividers are added automatically)",
    "Top of highest component to bottom of lowest",
    "Start this section on a new page",
    "Keep this section on the same page as the one below it",
]

# Size given to a newly added section, just so it shows up. Edit it in the table.
NEW_SECTION_WIDTH = 90.0
NEW_SECTION_HEIGHT = 150.0


class MainWindow(QMainWindow):
    def __init__(self, settings: LayoutSettings, switchboard: Switchboard):
        super().__init__()
        self._settings = settings
        self._switchboard_name = switchboard.name
        self.setWindowTitle(f"Hyper Switchboard Configurator - {switchboard.name}")
        self.resize(1400, 850)

        # Left side: section table and buttons
        self.table = QTableWidget(0, len(COLUMN_TITLES))
        self.table.setHorizontalHeaderLabels(COLUMN_TITLES)
        for column, tooltip in enumerate(COLUMN_TOOLTIPS):
            self.table.horizontalHeaderItem(column).setToolTip(tooltip)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(COL_NAME, QHeaderView.Stretch)

        add_button = QPushButton("Add section")
        remove_button = QPushButton("Remove selected")
        add_button.clicked.connect(self._add_new_section)
        remove_button.clicked.connect(self._remove_selected_sections)

        buttons = QHBoxLayout()
        buttons.addWidget(add_button)
        buttons.addWidget(remove_button)
        buttons.addStretch()

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(self.table)
        left_layout.addLayout(buttons)

        # Right side: page preview (scrolls when there are many pages)
        self.preview = PagePreview(settings)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.preview)

        top_splitter = QSplitter(Qt.Horizontal)
        top_splitter.addWidget(left)
        top_splitter.addWidget(scroll)
        top_splitter.setSizes([480, 920])

        # Bottom: warnings
        self.warning_list = QListWidget()

        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.addWidget(top_splitter)
        main_splitter.addWidget(self.warning_list)
        main_splitter.setSizes([700, 150])
        self.setCentralWidget(main_splitter)

        for section in switchboard.sections:
            self._append_row(section)
        self.table.itemChanged.connect(self.refresh)
        self.refresh()

    # --- Table <-> data ---------------------------------------------------------------

    def _append_row(self, section: Section):
        # Block signals while filling the row, or every cell would trigger a refresh.
        self.table.blockSignals(True)
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, COL_NAME, QTableWidgetItem(section.name))
        self.table.setItem(row, COL_WIDTH, QTableWidgetItem(f"{section.width:g}"))
        self.table.setItem(row, COL_HEIGHT, QTableWidgetItem(f"{section.height:g}"))
        self.table.setItem(row, COL_PUSH, _checkbox_item(section.push_to_next_page))
        self.table.setItem(row, COL_LINK, _checkbox_item(section.link_with_next))
        self.table.blockSignals(False)

    def _read_switchboard(self) -> tuple[Switchboard, list[str]]:
        """Build a Switchboard from the table. Rows with bad numbers are skipped and reported."""
        sections = []
        problems = []
        for row in range(self.table.rowCount()):
            name = self.table.item(row, COL_NAME).text().strip() or f"Row {row + 1}"
            try:
                width = float(self.table.item(row, COL_WIDTH).text())
                height = float(self.table.item(row, COL_HEIGHT).text())
            except ValueError:
                problems.append(f'Row {row + 1} ("{name}"): width and height must be numbers. '
                                f"Left out of the layout until fixed.")
                continue
            sections.append(
                Section(
                    name=name,
                    width=width,
                    height=height,
                    push_to_next_page=self.table.item(row, COL_PUSH).checkState() == Qt.Checked,
                    link_with_next=self.table.item(row, COL_LINK).checkState() == Qt.Checked,
                )
            )
        return Switchboard(name=self._switchboard_name, sections=sections), problems

    # --- Actions ----------------------------------------------------------------------

    def _add_new_section(self):
        number = self.table.rowCount() + 1
        self._append_row(Section(f"Section {number}", NEW_SECTION_WIDTH, NEW_SECTION_HEIGHT))
        self.refresh()

    def _remove_selected_sections(self):
        rows = sorted({index.row() for index in self.table.selectedIndexes()}, reverse=True)
        for row in rows:  # bottom-up, so earlier row numbers stay valid
            self.table.removeRow(row)
        self.refresh()

    def refresh(self):
        switchboard, problems = self._read_switchboard()
        result = fit_pages(switchboard, self._settings)
        self.preview.show_layout(result)

        self.warning_list.clear()
        all_warnings = problems + result.warnings
        if all_warnings:
            self.warning_list.addItems(["⚠ " + text for text in all_warnings])
        else:
            self.warning_list.addItem("No warnings.")


def _checkbox_item(checked: bool) -> QTableWidgetItem:
    item = QTableWidgetItem()
    item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
    item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
    return item
