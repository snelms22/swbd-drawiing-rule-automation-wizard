"""Editor for one section's contents: Above, Below, and the tie breaker.

Layout approved 2026-10-09 ("Section editor layout"). The editor changes the Section
object directly and emits `changed`, so the main window can re-run the layout. It makes
no layout decisions itself.

Levels in a Group Mounted Distribution are listed outward from the main bus (level 1 is
nearest the bus), so the reorder buttons say "Closer to bus" / "Further from bus".

Every library block the configurator places gets one field per attribute, labelled with
the prompt written in the block (read by Audit Blocks into catalog/blocks.json). A new
block therefore needs no code for its fields: give its attributes prompts and audit it.
"""
import copy

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from src.layout.section_builder import single_level_sides
from src.model.section_contents import (
    FEED_DIRECTIONS, FIXED, MOUNTINGS, Breaker, GroupMounted, MainBreaker, Provision,
    SingleBreaker, SingleLevel, TieBreaker, TwinLevel, feed_directions,
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
    if isinstance(slot, Provision):
        return f"PROVISION {slot.info}".strip()
    return slot.label or "(no label)"


def add_attribute_fields(form, block, values: dict, skip: set, on_edit):
    """One field per attribute of `block`, labelled with its prompt. `values` is the dict
    on the model, so an edit writes straight into it; `on_edit` is then called.
    Attributes that share a tag get one field (they can only hold the same text)."""
    while form.rowCount():
        form.removeRow(0)
    if block is None:
        return
    shown = set(skip)
    for attribute in block.attributes:
        if attribute.tag in shown:
            continue
        shown.add(attribute.tag)
        field = QLineEdit(values.get(attribute.tag, ""))
        field.setPlaceholderText(attribute.default)       # empty = the block's default
        field.setToolTip(f"Attribute {attribute.tag}")
        field.textEdited.connect(
            lambda text, tag=attribute.tag: _store_and_report(values, tag, text, on_edit))
        form.addRow(attribute.prompt or attribute.tag, field)


def _store_and_report(values: dict, tag: str, text: str, on_edit):
    values[tag] = text.strip()
    on_edit()


class SlotEditor(QWidget):
    """One position on a group-mounted level: a feeder breaker (label and its block's
    attributes), or a Provision (one line of info)."""
    changed = Signal()

    def __init__(self, settings, catalog=None):
        super().__init__()
        self._settings = settings
        self._catalog = catalog
        self._slot = None
        self.label_edit = QLineEdit()
        self.provision_check = QCheckBox("Provision")
        self.attributes_box = QGroupBox("Breaker block attributes")
        self.attributes_form = QFormLayout(self.attributes_box)
        row = QHBoxLayout()
        row.addWidget(self.label_edit)
        row.addWidget(self.provision_check)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(row)
        layout.addWidget(self.attributes_box)
        self.label_edit.textEdited.connect(self.changed)
        self.provision_check.toggled.connect(self.changed)

    def set_catalog(self, catalog):
        self._catalog = catalog
        if self._slot is not None:
            self._rebuild_fields()

    def load(self, slot):
        self._slot = slot
        is_provision = isinstance(slot, Provision)
        _set_quietly(self.provision_check, self.provision_check.setChecked, is_provision)
        _set_quietly(self.label_edit, self.label_edit.setText,
                     slot.info if is_provision else slot.label)
        self._rebuild_fields()

    def read(self, previous):
        """The slot as now edited. Keeps the same object when it stays the same kind, so
        anything else stored on it (attributes) is not lost."""
        text = self.label_edit.text().strip()
        if self.provision_check.isChecked():
            slot = previous if isinstance(previous, Provision) else Provision()
            slot.info = text
        else:
            slot = previous if isinstance(previous, Breaker) else Breaker("")
            slot.label = text
        if slot is not self._slot:          # changed kind: its fields change too
            self._slot = slot
            self._rebuild_fields()
        return slot

    def _rebuild_fields(self):
        is_breaker = isinstance(self._slot, Breaker)
        self.label_edit.setPlaceholderText("e.g. 52-F1" if is_breaker else "Provision for, e.g. 3VA62 250AF")
        block = self._catalog.get(self._settings.feeder.block) if self._catalog and is_breaker else None
        add_attribute_fields(self.attributes_form, block,
                             self._slot.attributes if is_breaker else {},
                             {self._settings.feeder.label_attribute},   # filled by the label
                             self.changed.emit)
        self.attributes_box.setVisible(block is not None and bool(block.attributes))


class ArrangementEditor(QGroupBox):
    """Edits the Above or the Below part of a section."""
    changed = Signal()

    def __init__(self, title: str, part: str, settings, catalog=None):
        super().__init__(title)
        self._part = part            # "above" or "below"
        self._settings = settings
        self._catalog = catalog      # library blocks (attributes, prompts); None = no fields
        self._section = None

        self.kind_combo = QComboBox()
        self.kind_combo.addItems(ARRANGEMENT_CHOICES)
        self.kind_combo.currentTextChanged.connect(self._kind_changed)

        # Page for Main breaker / Single breaker: just the breaker's label.
        self.breaker_label = QLineEdit()
        self.breaker_label.setPlaceholderText("e.g. 52-MCB-01")
        self.breaker_label.textEdited.connect(self._breaker_label_edited)
        # Main breakers only: fixed or draw-out (each is a library block, set in config).
        self.mounting_combo = QComboBox()
        self.mounting_combo.addItems(MOUNTINGS)
        self.mounting_combo.currentTextChanged.connect(self._mounting_changed)
        self.mounting_label = QLabel("Mounting")
        # Main and single breakers: which end of the breaker the cables connect to, and
        # which side of the cabinet they come in from (decision 2026-10-13). When the two
        # differ, the bus U-turns between the breaker and the termination.
        self.breaker_feed_combo = QComboBox()
        self.breaker_feed_combo.addItems(FEED_DIRECTIONS)
        self.breaker_feed_combo.currentTextChanged.connect(self._feeds_changed)
        self.termination_feed_combo = QComboBox()
        self.termination_feed_combo.addItems(FEED_DIRECTIONS)
        self.termination_feed_combo.currentTextChanged.connect(self._feeds_changed)
        breaker_page = QWidget()
        breaker_form = QFormLayout(breaker_page)
        breaker_form.addRow("Label", self.breaker_label)
        breaker_form.addRow(self.mounting_label, self.mounting_combo)
        breaker_form.addRow("Breaker Feed Direction", self.breaker_feed_combo)
        breaker_form.addRow("Termination Feed Direction", self.termination_feed_combo)
        # One field per block attribute, labelled with the prompt written in the block.
        self.breaker_attributes_box = QGroupBox("Breaker block attributes")
        self.breaker_attributes_form = QFormLayout(self.breaker_attributes_box)
        self.input_attributes_box = QGroupBox("Input block attributes")
        self.input_attributes_form = QFormLayout(self.input_attributes_box)
        breaker_form.addRow(self.breaker_attributes_box)
        breaker_form.addRow(self.input_attributes_box)

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
        # Show every level at once: the list grows with its contents instead of scrolling.
        self.levels_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Two rows of buttons so the editor stays narrow enough to sit beside the preview.
        button_rows = [
            [("+ Twin", self._add_twin), ("+ Single", self._add_single),
             ("Duplicate", self._duplicate_level), ("Remove", self._remove_level)],
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

        self.left_slot = SlotEditor(self._settings, self._catalog)
        self.right_slot = SlotEditor(self._settings, self._catalog)
        self.single_slot = SlotEditor(self._settings, self._catalog)
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
            breaker_feed, termination_feed = feed_directions(arrangement, self._part)
            _set_quietly(self.breaker_feed_combo, self.breaker_feed_combo.setCurrentText, breaker_feed)
            _set_quietly(self.termination_feed_combo, self.termination_feed_combo.setCurrentText,
                         termination_feed)
        is_main = kind == MAIN
        self.mounting_combo.setVisible(is_main)
        self.mounting_label.setVisible(is_main)
        if is_main:
            _set_quietly(self.mounting_combo, self.mounting_combo.setCurrentText, arrangement.mounting)
        self._rebuild_attribute_fields()
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
        self._fit_levels_list_to_contents()
        if group.levels:
            self.levels_list.setCurrentRow(min(max(select_row, 0), len(group.levels) - 1))
        self._level_selected(self.levels_list.currentRow())

    # --- Reactions to edits -------------------------------------------------------------

    def _kind_changed(self, kind):
        current = self._arrangement()
        # Keep the breaker (and its feed directions) when switching between Main and
        # Single, so what was entered survives.
        was_breaker = isinstance(current, (MainBreaker, SingleBreaker))
        kept = current.breaker if was_breaker else Breaker("")
        new = {EMPTY: None, MAIN: MainBreaker(kept), SINGLE: SingleBreaker(kept),
               GROUP: GroupMounted()}[kind]
        if was_breaker and isinstance(new, (MainBreaker, SingleBreaker)):
            new.breaker_feed = current.breaker_feed
            new.termination_feed = current.termination_feed
        self._set_arrangement(new)
        self.load(self._section)
        self.changed.emit()

    def set_catalog(self, catalog):
        self._catalog = catalog
        for editor in (self.left_slot, self.right_slot, self.single_slot):
            editor.set_catalog(catalog)
        if self._section is not None:
            self._rebuild_attribute_fields()

    def _rebuild_attribute_fields(self):
        """Fields for the breaker's block and its input (main breaker) or output (single
        breaker) block, from the catalog."""
        arrangement = self._arrangement() if self._section is not None else None
        breaker_block = io_block = None
        breaker_values, io_values = {}, {}
        if isinstance(arrangement, (MainBreaker, SingleBreaker)) and self._catalog:
            is_main = isinstance(arrangement, MainBreaker)
            mounting = arrangement.mounting if is_main else FIXED
            breaker_block = self._catalog.get(self._settings.main_breaker.blocks[mounting])
            io_block = self._catalog.get(self._settings.input_output.block)
            breaker_values = arrangement.breaker.attributes
            io_values = arrangement.input_attributes if is_main else arrangement.output_attributes
            self.input_attributes_box.setTitle("Input block attributes" if is_main
                                               else "Output block attributes")
        skip = {self._settings.main_breaker.label_attribute}   # filled by the Label field
        add_attribute_fields(self.breaker_attributes_form, breaker_block, breaker_values, skip,
                             self.changed.emit)
        add_attribute_fields(self.input_attributes_form, io_block, io_values, set(),
                             self.changed.emit)
        self.breaker_attributes_box.setVisible(breaker_block is not None and bool(breaker_block.attributes))
        self.input_attributes_box.setVisible(io_block is not None and bool(io_block.attributes))

    def _mounting_changed(self, mounting):
        arrangement = self._arrangement()
        if isinstance(arrangement, MainBreaker):
            arrangement.mounting = mounting
            self._rebuild_attribute_fields()     # the other block may have other attributes
            self.changed.emit()

    def _feeds_changed(self, *_):
        arrangement = self._arrangement()
        if isinstance(arrangement, (MainBreaker, SingleBreaker)):
            arrangement.breaker_feed = self.breaker_feed_combo.currentText()
            arrangement.termination_feed = self.termination_feed_combo.currentText()
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

    def _fit_levels_list_to_contents(self):
        rows = max(self.levels_list.count(), 1)
        row_height = self.levels_list.sizeHintForRow(0) if self.levels_list.count() else 18
        frame = 2 * self.levels_list.frameWidth()
        self.levels_list.setFixedHeight(rows * row_height + frame + 4)

    def _duplicate_level(self):
        """Copy the selected level (breakers, attributes, provision info) right after it.
        Breaker labels are left empty: duplicates are usually the same breaker under a
        new name, so the engineer types the name."""
        row = self.levels_list.currentRow()
        levels = self._arrangement().levels
        if not 0 <= row < len(levels):
            return
        duplicate = copy.deepcopy(levels[row])
        slots = [duplicate.left, duplicate.right] if isinstance(duplicate, TwinLevel) else [duplicate.slot]
        for slot in slots:
            if isinstance(slot, Breaker):
                slot.label = ""
        levels.insert(row + 1, duplicate)
        self._after_level_change(row + 1)

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
    """Optional tie breaker. It sits at the section's right edge (approved). Like a main
    breaker, it gets one field per attribute of its mounting's block."""
    changed = Signal()

    def __init__(self, settings, catalog=None):
        super().__init__("Tie breaker")
        self._settings = settings
        self._catalog = catalog
        self._section = None
        self.include_check = QCheckBox("Include a tie breaker")
        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText("e.g. 52-TB02")
        self.steps_combo = QComboBox()
        self.steps_combo.addItems(["down", "up"])
        self.mounting_combo = QComboBox()
        self.mounting_combo.addItems(MOUNTINGS)
        form = QFormLayout(self)
        form.addRow(self.include_check)
        form.addRow("Label", self.label_edit)
        form.addRow("Bus steps", self.steps_combo)
        form.addRow("Mounting", self.mounting_combo)
        self.attributes_box = QGroupBox("Breaker block attributes")
        self.attributes_form = QFormLayout(self.attributes_box)
        form.addRow(self.attributes_box)
        self.include_check.toggled.connect(self._include_toggled)
        self.label_edit.textEdited.connect(self._edited)
        self.steps_combo.currentTextChanged.connect(self._edited)
        self.mounting_combo.currentTextChanged.connect(self._edited)

    def load(self, section):
        self._section = section
        tie = section.contents.tie
        _set_quietly(self.include_check, self.include_check.setChecked, tie is not None)
        _set_quietly(self.label_edit, self.label_edit.setText, tie.breaker.label if tie else "")
        _set_quietly(self.steps_combo, self.steps_combo.setCurrentText, tie.bus_steps if tie else "down")
        _set_quietly(self.mounting_combo, self.mounting_combo.setCurrentText, tie.mounting if tie else MOUNTINGS[0])
        for widget in (self.label_edit, self.steps_combo, self.mounting_combo):
            widget.setEnabled(tie is not None)
        self._rebuild_attribute_fields()

    def set_catalog(self, catalog):
        self._catalog = catalog
        if self._section is not None:
            self._rebuild_attribute_fields()

    def _rebuild_attribute_fields(self):
        """Fields for the tie's breaker block (fixed or draw-out), from the catalog. The
        Label field fills the breaker-name attribute, so that one isn't shown twice."""
        tie = self._section.contents.tie if self._section is not None else None
        block = None
        if tie is not None and self._catalog:
            block = self._catalog.get(self._settings.main_breaker.blocks[tie.mounting])
        add_attribute_fields(self.attributes_form, block, tie.breaker.attributes if tie else {},
                             {self._settings.main_breaker.label_attribute}, self.changed.emit)
        self.attributes_box.setVisible(block is not None and bool(block.attributes))

    def _include_toggled(self, included):
        if included:
            self._section.contents.tie = TieBreaker(
                Breaker(self.label_edit.text().strip()), self.steps_combo.currentText(),
                self.mounting_combo.currentText(),
            )
        else:
            self._section.contents.tie = None
        self.load(self._section)
        self.changed.emit()

    def _edited(self, *_):
        tie = self._section.contents.tie
        if tie is not None:
            mounting_changed = tie.mounting != self.mounting_combo.currentText()
            tie.breaker.label = self.label_edit.text().strip()
            tie.bus_steps = self.steps_combo.currentText()
            tie.mounting = self.mounting_combo.currentText()
            if mounting_changed:
                self._rebuild_attribute_fields()     # the other block may have other attributes
            self.changed.emit()


class SectionEditor(QWidget):
    """Everything about the selected section."""
    changed = Signal()

    def __init__(self, settings, catalog=None):
        super().__init__()
        self.title = QLabel()
        self.title.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.above_editor = ArrangementEditor("Above the main bus", "above", settings, catalog)
        self.below_editor = ArrangementEditor("Below the main bus", "below", settings, catalog)
        self.tie_editor = TieEditor(settings, catalog)
        for editor in (self.above_editor, self.below_editor, self.tie_editor):
            editor.changed.connect(self.changed)

        layout = QVBoxLayout(self)
        layout.addWidget(self.title)
        layout.addWidget(self.above_editor)
        layout.addWidget(self.below_editor)
        layout.addWidget(self.tie_editor)
        layout.addStretch()
        self.load(None, 0)

    def set_catalog(self, catalog):
        self.above_editor.set_catalog(catalog)
        self.below_editor.set_catalog(catalog)
        self.tie_editor.set_catalog(catalog)

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
