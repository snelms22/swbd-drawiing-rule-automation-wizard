"""Editor for one section's contents: Above, Below, and the tie breaker.

Layout approved 2026-10-09 ("Section editor layout"). The editor changes the Section
object directly and emits `changed`, so the main window can re-run the layout. It makes
no layout decisions itself.

Levels in a Group Mounted Distribution are listed outward from the main bus (level 1 is
nearest the bus), so the reorder buttons say "Closer to bus" / "Further from bus".
"""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from src.layout.section_builder import single_level_sides
from src.model.section_contents import (
    Breaker, GroupMounted, MainBreaker, SingleBreaker, SingleLevel, Space, TieBreaker, TwinLevel,
)

EMPTY = "Empty"
MAIN = "Main breaker"
SINGLE = "Single breaker"
GROUP = "Group Mounted"
ARRANGEMENT_CHOICES = [EMPTY, MAIN, SINGLE, GROUP]


def _set_quietly(widget, setter, value):
    """Change a widget's value without it announcing the change (we're only loading)."""
    widget.blockSignals(True)
    setter(value)
    widget.blockSignals(False)


def slot_text(slot) -> str:
    if isinstance(slot, Space):
        return slot.text
    return slot.label or "(no label)"


class SlotEditor(QWidget):
    """One breaker position: a breaker label, or a Space."""
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText("e.g. 52-F1")
        self.space_check = QCheckBox("Space")
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.label_edit)
        row.addWidget(self.space_check)
        self.label_edit.textEdited.connect(self.changed)
        self.space_check.toggled.connect(self.changed)

    def load(self, slot):
        is_space = isinstance(slot, Space)
        _set_quietly(self.space_check, self.space_check.setChecked, is_space)
        _set_quietly(self.label_edit, self.label_edit.setText, slot.text if is_space else slot.label)

    def read(self, previous):
        """The slot as now edited. Keeps the same Breaker object when it stays a breaker,
        so anything else stored on it (block, ratings) is not lost."""
        text = self.label_edit.text().strip()
        if self.space_check.isChecked():
            return Space(text or "SPACE")
        if isinstance(previous, Breaker):
            previous.label = text
            return previous
        return Breaker(text)


class ArrangementEditor(QGroupBox):
    """Edits the Above or the Below part of a section."""
    changed = Signal()

    def __init__(self, title: str, part: str, settings):
        super().__init__(title)
        self._part = part            # "above" or "below"
        self._settings = settings
        self._section = None

        self.kind_combo = QComboBox()
        self.kind_combo.addItems(ARRANGEMENT_CHOICES)
        self.kind_combo.currentTextChanged.connect(self._kind_changed)

        # Page for Main breaker / Single breaker: just the breaker's label.
        self.breaker_label = QLineEdit()
        self.breaker_label.setPlaceholderText("e.g. 52-MCB-01")
        self.breaker_label.textEdited.connect(self._breaker_label_edited)
        breaker_page = QWidget()
        breaker_form = QFormLayout(breaker_page)
        breaker_form.addRow("Label", self.breaker_label)

        self.stack = QStackedWidget()
        self.stack.addWidget(QWidget())          # 0: Empty
        self.stack.addWidget(breaker_page)       # 1: Main / Single breaker
        self.stack.addWidget(self._build_group_page())  # 2: Group Mounted

        layout = QVBoxLayout(self)
        layout.addWidget(self.kind_combo)
        layout.addWidget(self.stack)

    # --- Group Mounted page -------------------------------------------------------------

    def _build_group_page(self) -> QWidget:
        self.levels_list = QListWidget()
        self.levels_list.currentRowChanged.connect(self._level_selected)

        # Two rows of buttons so the editor stays narrow enough to sit beside the preview.
        button_rows = [
            [("+ Twin", self._add_twin), ("+ Single", self._add_single), ("Remove", self._remove_level)],
            [("Closer to bus", self._move_closer), ("Further from bus", self._move_further),
             ("Flip", self._flip_level)],
        ]
        button_layouts = []
        for row in button_rows:
            row_layout = QHBoxLayout()
            for text, action in row:
                button = QPushButton(text)
                button.clicked.connect(action)
                row_layout.addWidget(button)
                if text == "Flip":
                    self.flip_button = button
            button_layouts.append(row_layout)

        self.left_slot = SlotEditor()
        self.right_slot = SlotEditor()
        self.single_slot = SlotEditor()
        for editor in (self.left_slot, self.right_slot, self.single_slot):
            editor.changed.connect(self._slot_edited)

        twin_page = QWidget()
        twin_form = QFormLayout(twin_page)
        twin_form.addRow("Left", self.left_slot)
        twin_form.addRow("Right", self.right_slot)
        single_page = QWidget()
        QFormLayout(single_page).addRow("Breaker", self.single_slot)
        self.level_stack = QStackedWidget()
        self.level_stack.addWidget(QLabel("Add or select a level."))  # 0: nothing selected
        self.level_stack.addWidget(twin_page)                        # 1
        self.level_stack.addWidget(single_page)                      # 2

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Levels, starting nearest the main bus:"))
        layout.addWidget(self.levels_list)
        for row_layout in button_layouts:
            layout.addLayout(row_layout)
        layout.addWidget(self.level_stack)
        return page

    # --- Loading ------------------------------------------------------------------------

    def load(self, section):
        self._section = section
        arrangement = self._arrangement()
        kind = {MainBreaker: MAIN, SingleBreaker: SINGLE, GroupMounted: GROUP}.get(
            type(arrangement), EMPTY
        )
        _set_quietly(self.kind_combo, self.kind_combo.setCurrentText, kind)
        self._show_page_for(kind)
        if kind in (MAIN, SINGLE):
            _set_quietly(self.breaker_label, self.breaker_label.setText, arrangement.breaker.label)
        if kind == GROUP:
            self._reload_levels(select_row=0)

    def _arrangement(self):
        return getattr(self._section.contents, self._part)

    def _set_arrangement(self, arrangement):
        setattr(self._section.contents, self._part, arrangement)

    def _show_page_for(self, kind):
        self.stack.setCurrentIndex({EMPTY: 0, MAIN: 1, SINGLE: 1, GROUP: 2}[kind])

    def _reload_levels(self, select_row):
        group = self._arrangement()
        sides = single_level_sides(group, self._settings)
        self.levels_list.blockSignals(True)
        self.levels_list.clear()
        for number, (level, side) in enumerate(zip(group.levels, sides), start=1):
            if isinstance(level, TwinLevel):
                text = f"{number}  Twin     {slot_text(level.left)}  |  {slot_text(level.right)}"
            else:
                text = f"{number}  Single   {slot_text(level.slot)}   ({side})"
            self.levels_list.addItem(text)
        self.levels_list.blockSignals(False)
        if group.levels:
            self.levels_list.setCurrentRow(min(max(select_row, 0), len(group.levels) - 1))
        self._level_selected(self.levels_list.currentRow())

    # --- Reactions to edits -------------------------------------------------------------

    def _kind_changed(self, kind):
        current = self._arrangement()
        # Keep the breaker when switching between Main and Single, so the label survives.
        kept = current.breaker if isinstance(current, (MainBreaker, SingleBreaker)) else Breaker("")
        new = {EMPTY: None, MAIN: MainBreaker(kept), SINGLE: SingleBreaker(kept),
               GROUP: GroupMounted()}[kind]
        self._set_arrangement(new)
        self.load(self._section)
        self.changed.emit()

    def _breaker_label_edited(self, text):
        self._arrangement().breaker.label = text.strip()
        self.changed.emit()

    def _level_selected(self, row):
        group = self._arrangement()
        if not isinstance(group, GroupMounted) or row < 0 or row >= len(group.levels):
            self.level_stack.setCurrentIndex(0)
            self.flip_button.setEnabled(False)
            return
        level = group.levels[row]
        if isinstance(level, TwinLevel):
            self.left_slot.load(level.left)
            self.right_slot.load(level.right)
            self.level_stack.setCurrentIndex(1)
        else:
            self.single_slot.load(level.slot)
            self.level_stack.setCurrentIndex(2)
        self.flip_button.setEnabled(isinstance(level, SingleLevel))

    def _slot_edited(self):
        group = self._arrangement()
        row = self.levels_list.currentRow()
        level = group.levels[row]
        if isinstance(level, TwinLevel):
            level.left = self.left_slot.read(level.left)
            level.right = self.right_slot.read(level.right)
        else:
            level.slot = self.single_slot.read(level.slot)
        self._refresh_level_text(row)
        self.changed.emit()

    def _refresh_level_text(self, row):
        """Update the list text without reloading the slot editors (keeps the cursor)."""
        group = self._arrangement()
        sides = single_level_sides(group, self._settings)
        level = group.levels[row]
        if isinstance(level, TwinLevel):
            text = f"{row + 1}  Twin     {slot_text(level.left)}  |  {slot_text(level.right)}"
        else:
            text = f"{row + 1}  Single   {slot_text(level.slot)}   ({sides[row]})"
        self.levels_list.item(row).setText(text)

    def _add_twin(self):
        self._arrangement().levels.append(TwinLevel(Breaker(""), Breaker("")))
        self._after_level_change(len(self._arrangement().levels) - 1)

    def _add_single(self):
        self._arrangement().levels.append(SingleLevel(Breaker("")))
        self._after_level_change(len(self._arrangement().levels) - 1)

    def _remove_level(self):
        row = self.levels_list.currentRow()
        if row >= 0:
            del self._arrangement().levels[row]
            self._after_level_change(row)

    def _move_closer(self):
        self._swap_levels(self.levels_list.currentRow(), -1)

    def _move_further(self):
        self._swap_levels(self.levels_list.currentRow(), +1)

    def _swap_levels(self, row, step):
        levels = self._arrangement().levels
        other = row + step
        if 0 <= row < len(levels) and 0 <= other < len(levels):
            levels[row], levels[other] = levels[other], levels[row]
            self._after_level_change(other)

    def _flip_level(self):
        row = self.levels_list.currentRow()
        level = self._arrangement().levels[row]
        if isinstance(level, SingleLevel):
            level.flipped = not level.flipped
            self._after_level_change(row)

    def _after_level_change(self, select_row):
        # Sides of later single levels can change, so redraw the whole list.
        self._reload_levels(select_row)
        self.changed.emit()


class TieEditor(QGroupBox):
    """Optional tie breaker. It sits at the section's right edge (approved)."""
    changed = Signal()

    def __init__(self):
        super().__init__("Tie breaker")
        self._section = None
        self.include_check = QCheckBox("Include a tie breaker")
        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText("e.g. 52-TB02")
        self.steps_combo = QComboBox()
        self.steps_combo.addItems(["down", "up"])
        form = QFormLayout(self)
        form.addRow(self.include_check)
        form.addRow("Label", self.label_edit)
        form.addRow("Bus steps", self.steps_combo)
        self.include_check.toggled.connect(self._include_toggled)
        self.label_edit.textEdited.connect(self._edited)
        self.steps_combo.currentTextChanged.connect(self._edited)

    def load(self, section):
        self._section = section
        tie = section.contents.tie
        _set_quietly(self.include_check, self.include_check.setChecked, tie is not None)
        _set_quietly(self.label_edit, self.label_edit.setText, tie.breaker.label if tie else "")
        _set_quietly(self.steps_combo, self.steps_combo.setCurrentText, tie.bus_steps if tie else "down")
        self.label_edit.setEnabled(tie is not None)
        self.steps_combo.setEnabled(tie is not None)

    def _include_toggled(self, included):
        if included:
            self._section.contents.tie = TieBreaker(
                Breaker(self.label_edit.text().strip()), self.steps_combo.currentText()
            )
        else:
            self._section.contents.tie = None
        self.load(self._section)
        self.changed.emit()

    def _edited(self, *_):
        tie = self._section.contents.tie
        if tie is not None:
            tie.breaker.label = self.label_edit.text().strip()
            tie.bus_steps = self.steps_combo.currentText()
            self.changed.emit()


class SectionEditor(QWidget):
    """Everything about the selected section."""
    changed = Signal()

    def __init__(self, settings):
        super().__init__()
        self.title = QLabel()
        self.title.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.above_editor = ArrangementEditor("Above the main bus", "above", settings)
        self.below_editor = ArrangementEditor("Below the main bus", "below", settings)
        self.tie_editor = TieEditor()
        for editor in (self.above_editor, self.below_editor, self.tie_editor):
            editor.changed.connect(self.changed)

        layout = QVBoxLayout(self)
        layout.addWidget(self.title)
        layout.addWidget(self.above_editor)
        layout.addWidget(self.below_editor)
        layout.addWidget(self.tie_editor)
        layout.addStretch()
        self.load(None, 0)

    def load(self, section, number):
        has_section = section is not None
        for editor in (self.above_editor, self.below_editor, self.tie_editor):
            editor.setEnabled(has_section)
        if not has_section:
            self.title.setText("No section selected")
            return
        self.title.setText(f"Section {number}")
        self.above_editor.load(section)
        self.below_editor.load(section)
        self.tie_editor.load(section)
