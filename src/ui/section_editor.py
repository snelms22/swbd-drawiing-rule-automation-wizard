"""Editor for one section's contents: Above, Below, and the tie breaker.

Layout approved 2026-10-09 ("Section editor layout"). The editor changes the Section
object directly and emits `changed`, so the main window can re-run the layout. It makes
no layout decisions itself.

Levels in a Group Mounted Distribution are listed outward from the main bus (level 1 is
nearest the bus), so the reorder buttons say "Closer to bus" / "Further from bus".

Every library block the configurator places gets one field per attribute, labelled with
the prompt written in the block (read by Audit Blocks into catalog/blocks.json). A new
block therefore needs no code for its fields: give its attributes prompts and audit it.

CTs and power meters (decision 2026-10-21): mains, single breakers, ties and group-mounted
parts each have a "Current transformers" box; each section has "Devices in this section"
where its power meters are added.

Interlocks (decision 2026-10-26): a main breaker's "Interlock" box picks the main it is
interlocked with and whether the interlock is mechanical, electrical or both. Both mains
show the same interlock.

Incoming feeds (decision 2026-10-22): a main breaker's feed is "In this riser" (its
Incoming feed box) or an "Incoming feed" part in the section next to it. An Incoming feed
part that no main breaker picks is main lugs only. A "Line-side breaker" (load bank) picks
the feed it is fed from.
"""
import copy

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from src.layout.current_transformers import program_filled_tags
from src.layout.section_builder import single_level_sides
from src.model.devices import (
    LINE_SIDE, LOAD_SIDE, comms_choices, meters_in, mms_name, needs_ethernet_switch, power_supplies_in,
    tap_target_names, voltage_taps_in,
)
from src.model.feeds import all_feeds, main_fed_by, standalone_feeds
from src.model.interlocks import interlock_of, mains_in, set_interlock
from src.model.section_contents import (
    FEED_DIRECTIONS, MOUNTINGS, Breaker, CurrentTransformers, GroupMounted, IncomingFeed,
    MOLDED_CASE, LineSideBreaker, MainBreaker, PowerMeter, PowerSupply, Provision, SingleBreaker, SingleLevel, Space, TieBreaker, TwinLevel,
    VoltageTap, feed_directions, side_away_from_bus,
)
from src.ui.widgets import ScrollSafeComboBox

EMPTY = "Empty"
MAIN = "Main breaker"
SINGLE = "Single breaker"
GROUP = "Group Mounted"
FEED = "Incoming feed"
LINE_SIDE = "Line-side breaker"      # e.g. a load-bank breaker on a feed's line side
ARRANGEMENT_CHOICES = [EMPTY, MAIN, FEED, LINE_SIDE, SINGLE, GROUP]
IN_THIS_RISER = "In this riser"      # a main breaker's feed choice


def _set_quietly(widget, setter, value):
    """Change a widget's value without it announcing the change (we're only loading)."""
    widget.blockSignals(True)
    setter(value)
    widget.blockSignals(False)


NO_COMMS = "None"                  # comms drop-down: no communication module


def comms_combo(modules) -> QComboBox:
    """Drop-down of communication modules (config/devices.json), "None" first."""
    combo = ScrollSafeComboBox()
    combo.addItems([NO_COMMS] + list(modules))
    return combo


def set_comms(combo, module: str):
    if module and combo.findText(module) < 0:
        combo.addItem(module)            # a saved module no longer in the list: keep it
    _set_quietly(combo, combo.setCurrentText, module or NO_COMMS)


def read_comms(combo) -> str:
    return "" if combo.currentText() == NO_COMMS else combo.currentText()


SLOT_BREAKER = "Breaker"
SLOT_PROVISION = "Provision"
SLOT_SPACE = "Space"
SLOT_KINDS = [SLOT_BREAKER, SLOT_PROVISION, SLOT_SPACE]


def slot_kind(slot) -> str:
    if isinstance(slot, Provision):
        return SLOT_PROVISION
    if isinstance(slot, Space):
        return SLOT_SPACE
    return SLOT_BREAKER


def slot_text(slot) -> str:
    if isinstance(slot, Provision):
        return f"PROVISION {slot.info}".strip()
    if isinstance(slot, Space):
        return "SPACE"
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


NO_METER = "Choose a power meter"
NO_TAP_TARGET = "Choose what it feeds"


class CtEditor(QGroupBox):
    """CTs on a main, single or tie breaker, or at the base of a group-mounted part
    (decision 2026-10-21). Ticking the box adds a CT set. The engineer picks the power meter
    it feeds and the ratio; the program numbers it (CTs 1..3, STB-1, ...), places it wherever it
    fits and fills in the meter. `attribute` is where the set is kept on the part ("cts", or
    "base_cts" on a group-mounted part)."""
    changed = Signal()

    def __init__(self, title, attribute, settings, catalog=None, switchboard_provider=None):
        super().__init__(title)
        self._attribute = attribute
        self._settings = settings
        self._catalog = catalog
        self._switchboard = switchboard_provider or (lambda: None)
        self._owner = None
        self.setCheckable(True)
        self.meter_combo = ScrollSafeComboBox()
        self.ratio_edit = QLineEdit()
        self.ratio_edit.setPlaceholderText("e.g. 4000:5A")
        # Mains only (decision 2026-10-21, kept as a choice): measure on the main bus after
        # the mains have joined instead of on this main's riser.
        self.main_bus_check = QCheckBox("On the main bus after the mains join (drawn on the riser for now)")
        self.attributes_box = QGroupBox("CT block attributes")
        self.attributes_form = QFormLayout(self.attributes_box)
        form = QFormLayout(self)
        form.addRow("Power meter", self.meter_combo)
        form.addRow("Current ratio", self.ratio_edit)
        form.addRow(self.main_bus_check)
        form.addRow(self.attributes_box)
        self.toggled.connect(self._toggled)
        self.meter_combo.currentIndexChanged.connect(self._edited)
        self.ratio_edit.textEdited.connect(self._edited)
        self.main_bus_check.toggled.connect(self._edited)

    def set_catalog(self, catalog):
        self._catalog = catalog
        self.load(self._owner)

    def load(self, owner):
        """Show the CTs of `owner` (a part or tie), or hide this box when None."""
        self._owner = owner
        self.setVisible(owner is not None)
        cts = getattr(owner, self._attribute) if owner is not None else None
        _set_quietly(self, self.setChecked, cts is not None)
        self.refresh_meters()
        _set_quietly(self.ratio_edit, self.ratio_edit.setText, cts.ratio if cts else "")
        self.main_bus_check.setVisible(isinstance(owner, MainBreaker))
        _set_quietly(self.main_bus_check, self.main_bus_check.setChecked, bool(cts and cts.on_main_bus))
        block = self._catalog.get(self._settings.current_transformers.block) if self._catalog else None
        add_attribute_fields(self.attributes_form, block, cts.attributes if cts else {},
                             program_filled_tags(self._settings), self.changed.emit)
        has_fields = block is not None and self.attributes_form.rowCount() > 0
        self.attributes_box.setVisible(cts is not None and has_fields)

    def refresh_meters(self):
        """List every power meter in the lineup (meters are added in each section's
        Devices box), keeping the chosen one."""
        cts = getattr(self._owner, self._attribute) if self._owner is not None else None
        chosen = cts.meter_id if cts else ""
        switchboard = self._switchboard()
        self.meter_combo.blockSignals(True)
        self.meter_combo.clear()
        self.meter_combo.addItem(NO_METER, "")
        for info in meters_in(switchboard) if switchboard is not None else []:
            self.meter_combo.addItem(f"{info.name}   {info.meter.model or '(no model yet)'}", info.meter.id)
        index = self.meter_combo.findData(chosen)
        if index < 0 and chosen:
            self.meter_combo.addItem("(that meter was removed)", chosen)
            index = self.meter_combo.count() - 1
        self.meter_combo.setCurrentIndex(max(index, 0))
        self.meter_combo.blockSignals(False)

    def _toggled(self, on):
        if self._owner is None:
            return
        setattr(self._owner, self._attribute, CurrentTransformers() if on else None)
        self.load(self._owner)
        self.changed.emit()

    def _edited(self, *_):
        cts = getattr(self._owner, self._attribute) if self._owner is not None else None
        if cts is None:
            return
        cts.meter_id = self.meter_combo.currentData() or ""
        cts.ratio = self.ratio_edit.text().strip()
        cts.on_main_bus = isinstance(self._owner, MainBreaker) and self.main_bus_check.isChecked()
        self.changed.emit()


NO_INTERLOCK = "None"


class InterlockEditor(QGroupBox):
    """A main breaker's interlock with another main breaker (decision 2026-10-26): which main,
    and mechanical, electrical or both. The interlock is kept on one of the two mains
    (src/model/interlocks.py); this box shows it on both and edits that one record."""
    changed = Signal()

    def __init__(self, switchboard_provider=None):
        super().__init__("Interlock")
        self._switchboard = switchboard_provider or (lambda: None)
        self._main = None
        self.with_combo = ScrollSafeComboBox()
        self.mechanical_check = QCheckBox("Mechanical")
        self.electrical_check = QCheckBox("Electrical")
        kinds = QHBoxLayout()
        kinds.addWidget(self.mechanical_check)
        kinds.addWidget(self.electrical_check)
        kinds.addStretch()
        form = QFormLayout(self)
        form.addRow("Interlocked with", self.with_combo)
        form.addRow("Interlock", kinds)
        self.with_combo.currentIndexChanged.connect(self._with_changed)
        self.mechanical_check.toggled.connect(self._kind_edited)
        self.electrical_check.toggled.connect(self._kind_edited)

    def load(self, main):
        """Show the interlock of `main` (a MainBreaker), or nothing when None."""
        self._main = main
        switchboard = self._switchboard()
        if main is None or switchboard is None:
            return
        found = interlock_of(switchboard, main)
        lock, other_id = found if found else (None, "")
        self.with_combo.blockSignals(True)
        self.with_combo.clear()
        self.with_combo.addItem(NO_INTERLOCK, "")
        for place in mains_in(switchboard):
            if place.main is main:
                continue
            taken = interlock_of(switchboard, place.main)
            if taken is not None and taken[1] != main.id and place.main.id != other_id:
                continue              # already interlocked with another main (one each for now)
            self.with_combo.addItem(place.name, place.main.id)
        index = self.with_combo.findData(other_id)
        if index < 0:
            self.with_combo.addItem("(that main breaker was removed)", other_id)
            index = self.with_combo.count() - 1
        self.with_combo.setCurrentIndex(index)
        self.with_combo.blockSignals(False)
        _set_quietly(self.mechanical_check, self.mechanical_check.setChecked, bool(lock and lock.mechanical))
        _set_quietly(self.electrical_check, self.electrical_check.setChecked, bool(lock and lock.electrical))
        for check in (self.mechanical_check, self.electrical_check):
            check.setEnabled(lock is not None)

    def _with_changed(self, *_):
        switchboard = self._switchboard()
        if self._main is None or switchboard is None:
            return
        set_interlock(switchboard, self._main, self.with_combo.currentData() or "",
                      self.mechanical_check.isChecked(), self.electrical_check.isChecked())
        self.load(self._main)
        self.changed.emit()

    def _kind_edited(self, *_):
        found = interlock_of(self._switchboard(), self._main) if self._main is not None else None
        if found is None:
            return
        lock, _ = found
        lock.mechanical = self.mechanical_check.isChecked()
        lock.electrical = self.electrical_check.isChecked()
        self.changed.emit()


class VoltageTapsEditor(QGroupBox):
    """Voltage taps on an incoming feed (decision 2026-10-22) and, for a main breaker, on its
    load side (decision 2026-10-23): each tap says which side of the main it is on. Each tap
    feeds a power meter's voltage input or a power supply (decision 2026-11-05); its fuse is
    numbered FA-n (decision 2026-10-23)."""
    changed = Signal()

    def __init__(self, switchboard_provider=None, catalog=None, fuse=None):
        """`fuse`: the fuse settings (config/devices.json): its block's attributes get one
        field each, except the number the program fills in (decision 2026-10-23)."""
        super().__init__("Voltage taps")
        self._switchboard = switchboard_provider or (lambda: None)
        self._catalog = catalog
        self._fuse = fuse
        self._feed = None
        self._main = None
        self.taps_list = QListWidget()
        self.taps_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.taps_list.currentRowChanged.connect(self._tap_selected)
        add_button = QPushButton("+ Voltage tap")
        add_button.clicked.connect(self._add_tap)
        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self._remove_tap)
        # Which side of the main breaker: its line side (on its feed) or its load side.
        self.side_combo = ScrollSafeComboBox()
        self.side_combo.addItem("Line side", LINE_SIDE)
        self.side_combo.addItem("Load side", LOAD_SIDE)
        self.side_combo.currentIndexChanged.connect(self._side_changed)
        self.feeds_combo = ScrollSafeComboBox()
        self.feeds_combo.currentIndexChanged.connect(self._feeds_changed)
        buttons = QHBoxLayout()
        buttons.addWidget(add_button)
        buttons.addWidget(self.remove_button)
        buttons.addStretch()
        layout = QVBoxLayout(self)
        layout.addWidget(self.taps_list)
        layout.addLayout(buttons)
        self.tap_form = QFormLayout()
        self.tap_form.addRow("Side of the main breaker", self.side_combo)
        self.tap_form.addRow("Feeds", self.feeds_combo)
        layout.addLayout(self.tap_form)
        self.fuse_box = QGroupBox("Fuse block attributes")
        self.fuse_form = QFormLayout(self.fuse_box)
        layout.addWidget(self.fuse_box)

    def set_catalog(self, catalog):
        self._catalog = catalog
        self.refresh_meters()

    def load(self, feed, main=None, select_row=0):
        """Show the taps of `feed` (line side) and of `main` (its load side), or hide this box
        when both are None."""
        self._feed, self._main = feed, main
        self.setVisible(feed is not None or main is not None)
        self.tap_form.setRowVisible(self.side_combo, main is not None)
        rows = self._rows()
        fuses = self._fuse_names()
        targets = self._target_names()
        self.taps_list.blockSignals(True)
        self.taps_list.clear()
        for taps, index in rows:
            tap = taps[index]
            target = targets.get(tap.feeds, "(choose what it feeds)" if not tap.feeds else "(device removed)")
            side = ""
            if main is not None:
                side = "   (load side)" if taps is main.load_side_taps else "   (line side)"
            self.taps_list.addItem(f"{fuses.get(id(tap), 'FA-?')}   to {target}{side}")
        self.taps_list.blockSignals(False)
        count = max(len(rows), 1)
        row_height = self.taps_list.sizeHintForRow(0) if rows else 18
        self.taps_list.setFixedHeight(count * row_height + 2 * self.taps_list.frameWidth() + 4)
        if rows:
            self.taps_list.setCurrentRow(min(max(select_row, 0), len(rows) - 1))
        self._tap_selected(self.taps_list.currentRow())

    def refresh_meters(self):
        if self._feed is not None or self._main is not None:
            self.load(self._feed, self._main, self.taps_list.currentRow())

    def _rows(self) -> list:
        """(list the tap is in, its index) for each row: the feed's taps, then the main's
        load-side taps (the order they are numbered in)."""
        rows = []
        for taps in (self._feed.voltage_taps if self._feed is not None else None,
                     self._main.load_side_taps if self._main is not None else None):
            if taps is not None:
                rows += [(taps, index) for index in range(len(taps))]
        return rows

    def _selected(self):
        """(list, index) of the selected tap, or None."""
        rows = self._rows()
        row = self.taps_list.currentRow()
        return rows[row] if 0 <= row < len(rows) else None

    def _fuse_names(self) -> dict:
        switchboard = self._switchboard()
        return {id(info.tap): info.fuse for info in voltage_taps_in(switchboard)} if switchboard else {}

    def _target_names(self) -> dict:
        switchboard = self._switchboard()
        return tap_target_names(switchboard) if switchboard else {}

    def _tap_selected(self, *_):
        selected = self._selected()
        tap = selected[0][selected[1]] if selected else None
        self.feeds_combo.setEnabled(tap is not None)
        self.remove_button.setEnabled(tap is not None)
        # Only a main with its feed in this riser has a line side to put taps on.
        self.side_combo.setEnabled(tap is not None and self._feed is not None)
        on_load_side = (self._main is not None and selected is not None
                        and selected[0] is self._main.load_side_taps)
        _set_quietly(self.side_combo, self.side_combo.setCurrentIndex, 1 if on_load_side else 0)
        chosen = tap.feeds if tap is not None else ""
        switchboard = self._switchboard()
        self.feeds_combo.blockSignals(True)
        self.feeds_combo.clear()
        self.feeds_combo.addItem(NO_TAP_TARGET, "")
        for info in meters_in(switchboard) if switchboard is not None else []:
            self.feeds_combo.addItem(f"{info.name}   {info.meter.model or '(no model yet)'}", info.meter.id)
        for info in power_supplies_in(switchboard) if switchboard is not None else []:
            self.feeds_combo.addItem(f"{info.name}   power supply", info.supply.id)
        index = self.feeds_combo.findData(chosen)
        if index < 0 and chosen:
            self.feeds_combo.addItem("(that device was removed)", chosen)
            index = self.feeds_combo.count() - 1
        self.feeds_combo.setCurrentIndex(max(index, 0))
        self.feeds_combo.blockSignals(False)
        # The fuse's own fields (e.g. its rating), from its block.
        block = (self._catalog.get(self._fuse.block) if self._catalog and self._fuse and tap is not None
                 else None)
        add_attribute_fields(self.fuse_form, block, tap.fuse_attributes if tap is not None else {},
                             {self._fuse.number_attribute} if self._fuse else set(), self.changed.emit)
        self.fuse_box.setVisible(block is not None and self.fuse_form.rowCount() > 0)

    def _add_tap(self):
        # On the feed (line side) when there is one, else on the main's load side.
        taps = self._feed.voltage_taps if self._feed is not None else self._main.load_side_taps
        taps.append(VoltageTap())
        self.load(self._feed, self._main, self._row_of(taps, len(taps) - 1))
        self.changed.emit()

    def _row_of(self, taps, index) -> int:
        for row, (row_taps, row_index) in enumerate(self._rows()):
            if row_taps is taps and row_index == index:
                return row
        return 0

    def _remove_tap(self):
        selected = self._selected()
        if selected is not None:
            taps, index = selected
            del taps[index]
            self.load(self._feed, self._main, self.taps_list.currentRow())
            self.changed.emit()

    def _feeds_changed(self, *_):
        selected = self._selected()
        if selected is not None:
            taps, index = selected
            taps[index].feeds = self.feeds_combo.currentData() or ""
            self.load(self._feed, self._main, self.taps_list.currentRow())
            self.changed.emit()

    def _side_changed(self, *_):
        """Move the selected tap to the end of the other side's list."""
        selected = self._selected()
        if selected is None or self._main is None or self._feed is None:
            return
        taps, index = selected
        to_load_side = self.side_combo.currentData() == LOAD_SIDE
        target = self._main.load_side_taps if to_load_side else self._feed.voltage_taps
        if target is taps:
            return
        target.append(taps.pop(index))
        self.load(self._feed, self._main, self._row_of(target, len(target) - 1))
        self.changed.emit()


class DevicesEditor(QGroupBox):
    """Devices mounted in this section, drawn on the device pages: power meters, named PM-n
    (n through the lineup; decision 2026-11-10), whose model the engineer picks;
    and power supplies, named PS-n (decision 2026-11-05), with one field per attribute of
    their block. A voltage tap says which of them it feeds."""
    changed = Signal()

    def __init__(self, meter_models=(), switchboard_provider=None, catalog=None, power_supply=None):
        """`power_supply`: the power supply settings (config/devices.json); None = none offered."""
        super().__init__("Devices in this section")
        self._meter_models = list(meter_models)
        self._switchboard = switchboard_provider or (lambda: None)
        self._catalog = catalog
        self._power_supply = power_supply
        self._section = None
        self.meters_list = QListWidget()
        self.meters_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.meters_list.currentRowChanged.connect(self._meter_selected)
        add_button = QPushButton("+ Power meter")
        add_button.clicked.connect(self._add_meter)
        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self._remove_meter)
        self.model_combo = ScrollSafeComboBox()
        self.model_combo.currentTextChanged.connect(self._model_changed)
        buttons = QHBoxLayout()
        buttons.addWidget(add_button)
        buttons.addWidget(self.remove_button)
        buttons.addStretch()
        layout = QVBoxLayout(self)
        layout.addWidget(self.meters_list)
        layout.addLayout(buttons)
        self.remote_display_check = QCheckBox("Remote display (on the meter's USB)")
        self.remote_display_check.toggled.connect(self._remote_display_toggled)
        model_form = QFormLayout()
        model_form.addRow("Model", self.model_combo)
        model_form.addRow(self.remote_display_check)
        layout.addLayout(model_form)

        # Power supplies (decision 2026-11-05).
        self.supplies_list = QListWidget()
        self.supplies_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.supplies_list.currentRowChanged.connect(self._supply_selected)
        add_supply = QPushButton("+ Power supply")
        add_supply.clicked.connect(self._add_supply)
        self.remove_supply_button = QPushButton("Remove")
        self.remove_supply_button.clicked.connect(self._remove_supply)
        supply_buttons = QHBoxLayout()
        supply_buttons.addWidget(add_supply)
        supply_buttons.addWidget(self.remove_supply_button)
        supply_buttons.addStretch()
        self.supply_attributes_box = QGroupBox("Power supply block attributes")
        self.supply_attributes_form = QFormLayout(self.supply_attributes_box)
        self.supplies_widget = QWidget()
        supplies_layout = QVBoxLayout(self.supplies_widget)
        supplies_layout.setContentsMargins(0, 0, 0, 0)
        supplies_layout.addWidget(self.supplies_list)
        supplies_layout.addLayout(supply_buttons)
        supplies_layout.addWidget(self.supply_attributes_box)
        self.supplies_widget.setVisible(power_supply is not None)
        layout.addWidget(self.supplies_widget)

        # The switchboard's one Ethernet switch (decision 2026-11-09): shown when there are
        # comms modules or power meters; ticking it here unticks every other section.
        self.ethernet_check = QCheckBox("Ethernet switch in this section")
        self.ethernet_check.toggled.connect(self._ethernet_toggled)
        layout.addWidget(self.ethernet_check)

    def set_catalog(self, catalog):
        self._catalog = catalog
        if self._section is not None:
            self._supply_selected(self.supplies_list.currentRow())

    def load(self, section, select_row=0, select_supply=0):
        self._section = section
        self._load_supplies(select_supply)
        self.refresh_ethernet()
        meters = section.contents.power_meters
        names = self._names()
        self.meters_list.blockSignals(True)
        self.meters_list.clear()
        for meter in meters:
            self.meters_list.addItem(f"{names.get(meter.id, 'PM-?')}   {meter.model or '(choose a model)'}")
        self.meters_list.blockSignals(False)
        rows = max(len(meters), 1)
        row_height = self.meters_list.sizeHintForRow(0) if meters else 18
        self.meters_list.setFixedHeight(rows * row_height + 2 * self.meters_list.frameWidth() + 4)
        if meters:
            self.meters_list.setCurrentRow(min(max(select_row, 0), len(meters) - 1))
        self._meter_selected(self.meters_list.currentRow())

    def _names(self) -> dict:
        switchboard = self._switchboard()
        return {info.meter.id: info.name for info in meters_in(switchboard)} if switchboard else {}

    # --- Ethernet switch ---------------------------------------------------------------

    def refresh_ethernet(self):
        """Show the Ethernet switch box when the lineup needs one (or it is already ticked)."""
        if self._section is None:
            return
        switchboard = self._switchboard()
        ticked = self._section.contents.ethernet_switch
        self.ethernet_check.setVisible(ticked or (switchboard is not None and needs_ethernet_switch(switchboard)))
        _set_quietly(self.ethernet_check, self.ethernet_check.setChecked, ticked)

    def _ethernet_toggled(self, on):
        switchboard = self._switchboard()
        if on and switchboard is not None:
            for section in switchboard.sections:
                section.contents.ethernet_switch = False      # only one in the switchboard
        self._section.contents.ethernet_switch = on
        self.changed.emit()

    # --- Power supplies ---------------------------------------------------------------

    def _load_supplies(self, select_row):
        supplies = self._section.contents.power_supplies
        switchboard = self._switchboard()
        names = {info.supply.id: info.name for info in power_supplies_in(switchboard)} if switchboard else {}
        self.supplies_list.blockSignals(True)
        self.supplies_list.clear()
        for supply in supplies:
            self.supplies_list.addItem(f"{names.get(supply.id, 'PS-?')}   3-pole, 480 V to 24 V")
        self.supplies_list.blockSignals(False)
        rows = max(len(supplies), 1)
        row_height = self.supplies_list.sizeHintForRow(0) if supplies else 18
        self.supplies_list.setFixedHeight(rows * row_height + 2 * self.supplies_list.frameWidth() + 4)
        if supplies:
            self.supplies_list.setCurrentRow(min(max(select_row, 0), len(supplies) - 1))
        self._supply_selected(self.supplies_list.currentRow())

    def _supply_selected(self, row):
        supplies = self._section.contents.power_supplies if self._section is not None else []
        supply = supplies[row] if 0 <= row < len(supplies) else None
        self.remove_supply_button.setEnabled(supply is not None)
        settings = self._power_supply
        block = (self._catalog.get(settings.block) if self._catalog and settings and supply is not None
                 else None)
        add_attribute_fields(self.supply_attributes_form, block, supply.attributes if supply else {},
                             {settings.number_attribute} if settings else set(), self.changed.emit)
        self.supply_attributes_box.setVisible(block is not None and self.supply_attributes_form.rowCount() > 0)

    def _add_supply(self):
        supplies = self._section.contents.power_supplies
        supplies.append(PowerSupply())
        self._load_supplies(len(supplies) - 1)
        self.changed.emit()

    def _remove_supply(self):
        row = self.supplies_list.currentRow()
        supplies = self._section.contents.power_supplies
        if 0 <= row < len(supplies):
            del supplies[row]
            self._load_supplies(row)
            self.changed.emit()

    def _meter_selected(self, row):
        meters = self._section.contents.power_meters if self._section is not None else []
        has_meter = 0 <= row < len(meters)
        self.model_combo.setEnabled(has_meter)
        self.remove_button.setEnabled(has_meter)
        model = meters[row].model if has_meter else ""
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self.model_combo.addItems([""] + self._meter_models)
        if model and self.model_combo.findText(model) < 0:
            self.model_combo.addItem(model)          # a saved model no longer in the list
        self.model_combo.setCurrentText(model)
        self.model_combo.blockSignals(False)
        self.remote_display_check.setEnabled(has_meter)
        _set_quietly(self.remote_display_check, self.remote_display_check.setChecked,
                     meters[row].remote_display if has_meter else False)

    def _remote_display_toggled(self, on):
        row = self.meters_list.currentRow()
        meters = self._section.contents.power_meters if self._section is not None else []
        if 0 <= row < len(meters):
            meters[row].remote_display = on
            self.changed.emit()

    def _add_meter(self):
        meters = self._section.contents.power_meters
        meters.append(PowerMeter())
        self.load(self._section, len(meters) - 1)
        self.changed.emit()

    def _remove_meter(self):
        row = self.meters_list.currentRow()
        meters = self._section.contents.power_meters
        if 0 <= row < len(meters):
            del meters[row]
            self.load(self._section, row)
            self.changed.emit()

    def _model_changed(self, model):
        row = self.meters_list.currentRow()
        meters = self._section.contents.power_meters
        if 0 <= row < len(meters):
            meters[row].model = model
            self.load(self._section, row)
            self.changed.emit()


class SlotEditor(QWidget):
    """One position on a group-mounted level: a feeder breaker (label and its block's
    attributes), a Provision (one line of info), or a Space (nothing to fill in)."""
    changed = Signal()

    def __init__(self, settings, catalog=None, comms_modules=()):
        super().__init__()
        self._settings = settings
        self._catalog = catalog
        self._slot = None
        self.label_edit = QLineEdit()
        self.kind_combo = ScrollSafeComboBox()
        self.kind_combo.addItems(SLOT_KINDS)
        self.attributes_box = QGroupBox("Breaker block attributes")
        self.attributes_form = QFormLayout(self.attributes_box)
        row = QHBoxLayout()
        row.addWidget(self.label_edit)
        row.addWidget(self.kind_combo)
        # Communication module on this breaker (decision 2026-10-19; drawing logic later).
        # A group-mounted breaker is a 3VA (decision 2026-11-09).
        self.comms_combo = comms_combo(comms_choices(comms_modules, MOLDED_CASE))
        self.comms_combo.setToolTip("Communication module")
        row.addWidget(self.comms_combo)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(row)
        layout.addWidget(self.attributes_box)
        self.label_edit.textEdited.connect(self.changed)
        self.kind_combo.currentTextChanged.connect(self.changed)
        self.comms_combo.currentTextChanged.connect(self.changed)

    def set_catalog(self, catalog):
        self._catalog = catalog
        if self._slot is not None:
            self._rebuild_fields()

    def load(self, slot):
        self._slot = slot
        _set_quietly(self.kind_combo, self.kind_combo.setCurrentText, slot_kind(slot))
        text = slot.info if isinstance(slot, Provision) else getattr(slot, "label", "")
        _set_quietly(self.label_edit, self.label_edit.setText, text)
        self._rebuild_fields()

    def read(self, previous):
        """The slot as now edited. Keeps the same object when it stays the same kind, so
        anything else stored on it (attributes) is not lost."""
        text = self.label_edit.text().strip()
        kind = self.kind_combo.currentText()
        if kind == SLOT_PROVISION:
            slot = previous if isinstance(previous, Provision) else Provision()
            slot.info = text
        elif kind == SLOT_SPACE:
            slot = previous if isinstance(previous, Space) else Space()
        else:
            slot = previous if isinstance(previous, Breaker) else Breaker("")
            slot.label = text
            slot.comms_module = read_comms(self.comms_combo)
        if slot is not self._slot:          # changed kind: its fields change too
            self._slot = slot
            self._rebuild_fields()
        return slot

    def _rebuild_fields(self):
        is_breaker = isinstance(self._slot, Breaker)
        is_space = isinstance(self._slot, Space)
        self.label_edit.setEnabled(not is_space)            # a space has nothing to type
        if is_space:
            self.label_edit.clear()
        self.label_edit.setPlaceholderText(
            "e.g. 52-F1" if is_breaker else "" if is_space else "Provision for, e.g. 3VA62 250AF")
        block = self._catalog.get(self._settings.feeder.block) if self._catalog and is_breaker else None
        add_attribute_fields(self.attributes_form, block,
                             self._slot.attributes if is_breaker else {},
                             {self._settings.feeder.label_attribute},   # filled by the label
                             self.changed.emit)
        self.attributes_box.setVisible(block is not None and bool(block.attributes))
        self.comms_combo.setVisible(is_breaker)             # only breakers have comms
        set_comms(self.comms_combo, self._slot.comms_module if is_breaker else "")


class ArrangementEditor(QGroupBox):
    """Edits the Above or the Below part of a section."""
    changed = Signal()

    def __init__(self, title: str, part: str, settings, catalog=None, comms_modules=(),
                 switchboard_provider=None, fuse=None):
        super().__init__(title)
        self._part = part            # "above" or "below"
        self._switchboard_provider = switchboard_provider
        self._comms_modules = comms_modules   # communication modules to choose from
        self._settings = settings
        self._catalog = catalog      # library blocks (attributes, prompts); None = no fields
        self._section = None

        self.kind_combo = ScrollSafeComboBox()
        self.kind_combo.addItems(ARRANGEMENT_CHOICES)
        self.kind_combo.currentTextChanged.connect(self._kind_changed)

        # Page for Main breaker / Single breaker: just the breaker's label.
        self.breaker_label = QLineEdit()
        self.breaker_label.setPlaceholderText("e.g. 52-MCB-01")
        self.breaker_label.textEdited.connect(self._breaker_label_edited)
        # Main breakers only: fixed or draw-out (each is a library block, set in config).
        self.mounting_combo = ScrollSafeComboBox()
        self.mounting_combo.addItems(MOUNTINGS)
        self.mounting_combo.currentTextChanged.connect(self._mounting_changed)
        self.mounting_label = QLabel("Mounting")
        # Main and single breakers: which end of the breaker the cables connect to, and
        # which side of the cabinet they come in from (decision 2026-10-13). When the two
        # differ, the bus U-turns between the breaker and the termination.
        self.breaker_feed_combo = ScrollSafeComboBox()
        self.breaker_feed_combo.addItems(FEED_DIRECTIONS)
        self.breaker_feed_combo.currentTextChanged.connect(self._feeds_changed)
        self.termination_feed_combo = ScrollSafeComboBox()
        self.termination_feed_combo.addItems(FEED_DIRECTIONS)
        self.termination_feed_combo.currentTextChanged.connect(self._feeds_changed)
        breaker_page = QWidget()
        breaker_form = QFormLayout(breaker_page)
        self.breaker_form = breaker_form
        breaker_form.addRow("Label", self.breaker_label)
        self.breaker_comms_combo = comms_combo(comms_choices(comms_modules))     # a 3WA
        self.breaker_comms_combo.currentTextChanged.connect(self._breaker_comms_changed)
        breaker_form.addRow("Comms module", self.breaker_comms_combo)
        # Every 3WA has a DAS/MMS, added by the program (decision 2026-11-09).
        self.mms_info = QLabel()
        breaker_form.addRow("DAS/MMS", self.mms_info)
        breaker_form.addRow(self.mounting_label, self.mounting_combo)
        breaker_form.addRow("Breaker Feed Direction", self.breaker_feed_combo)
        # One field per block attribute, labelled with the prompt written in the block.
        self.breaker_attributes_box = QGroupBox("Breaker block attributes")
        self.breaker_attributes_form = QFormLayout(self.breaker_attributes_box)
        breaker_form.addRow(self.breaker_attributes_box)
        self.ct_editor = CtEditor("Current transformers", "cts", settings, catalog, switchboard_provider)
        self.ct_editor.changed.connect(self.changed)
        breaker_form.addRow(self.ct_editor)
        # Main breakers: interlocked with another main (decision 2026-10-26).
        self.interlock_editor = InterlockEditor(switchboard_provider)
        self.interlock_editor.changed.connect(self.changed)
        breaker_form.addRow(self.interlock_editor)
        # Main breakers: where the feed is (decision 2026-10-22).
        self.feed_source_combo = ScrollSafeComboBox()
        self.feed_source_combo.currentIndexChanged.connect(self._feed_source_changed)
        breaker_form.addRow("Feed", self.feed_source_combo)
        # An Incoming feed part: what it goes to (worked out from the lineup).
        self.feed_info = QLabel()
        breaker_form.addRow(self.feed_info)
        # A line-side breaker: the feed it is fed from.
        self.fed_from_combo = ScrollSafeComboBox()
        self.fed_from_combo.currentIndexChanged.connect(self._fed_from_changed)
        breaker_form.addRow("Fed from", self.fed_from_combo)
        # The termination: a main breaker's incoming feed, an Incoming feed part, or a
        # single breaker's output.
        self.termination_box = QGroupBox("Incoming feed")
        termination_form = QFormLayout(self.termination_box)
        self.termination_form = termination_form
        termination_form.addRow("Termination Feed Direction", self.termination_feed_combo)
        self.input_attributes_box = QGroupBox("Input block attributes")
        self.input_attributes_form = QFormLayout(self.input_attributes_box)
        termination_form.addRow(self.input_attributes_box)
        breaker_form.addRow(self.termination_box)
        # Voltage taps: on the feed, and on a main's load side (decisions 2026-10-22/23). Below
        # the feed's box, so a main fed from another section still shows its load-side taps.
        self.taps_editor = VoltageTapsEditor(switchboard_provider, catalog, fuse)
        self.taps_editor.changed.connect(self.changed)
        breaker_form.addRow(self.taps_editor)

        self.stack = QStackedWidget()
        self.stack.addWidget(QWidget())          # 0: Empty
        self.stack.addWidget(breaker_page)       # 1: Main / Single breaker / Incoming feed
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

        self.left_slot = SlotEditor(self._settings, self._catalog, self._comms_modules)
        self.right_slot = SlotEditor(self._settings, self._catalog, self._comms_modules)
        self.single_slot = SlotEditor(self._settings, self._catalog, self._comms_modules)
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
        self.base_ct_editor = CtEditor("Current transformers at the base of the vertical bus", "base_cts",
                                       self._settings, self._catalog, self._switchboard_provider)
        self.base_ct_editor.changed.connect(self.changed)
        layout.addWidget(self.base_ct_editor)
        return page

    # --- Loading ------------------------------------------------------------------------

    def load(self, section):
        self._section = section
        arrangement = self._arrangement()
        kind = {MainBreaker: MAIN, SingleBreaker: SINGLE, GroupMounted: GROUP, IncomingFeed: FEED,
                LineSideBreaker: LINE_SIDE}.get(type(arrangement), EMPTY)
        _set_quietly(self.kind_combo, self.kind_combo.setCurrentText, kind)
        self._show_page_for(kind)
        if kind in (MAIN, SINGLE, LINE_SIDE):
            _set_quietly(self.breaker_label, self.breaker_label.setText, arrangement.breaker.label)
            set_comms(self.breaker_comms_combo, arrangement.breaker.comms_module)
            switchboard = self._switchboard_provider() if self._switchboard_provider else None
            name = mms_name(switchboard, arrangement.breaker) if switchboard is not None else ""
            self.mms_info.setText(f"{name or 'MMS'} (added automatically)")
        self.breaker_form.setRowVisible(self.mms_info, kind in (MAIN, SINGLE, LINE_SIDE))
        if kind in (MAIN, SINGLE):
            breaker_feed, termination_feed = feed_directions(arrangement, self._part)
            _set_quietly(self.breaker_feed_combo, self.breaker_feed_combo.setCurrentText, breaker_feed)
            _set_quietly(self.termination_feed_combo, self.termination_feed_combo.setCurrentText,
                         termination_feed)
        is_main = kind == MAIN
        is_feed = kind == FEED
        is_line_side = kind == LINE_SIDE
        if is_feed:
            _set_quietly(self.termination_feed_combo, self.termination_feed_combo.setCurrentText,
                         arrangement.termination_feed or side_away_from_bus(self._part))
        # An Incoming feed part shows only its feed; a main breaker also says where its feed is.
        for widget in (self.breaker_label, self.breaker_comms_combo, self.breaker_attributes_box):
            self.breaker_form.setRowVisible(widget, not is_feed)
        # A line-side breaker's feed directions are fixed for now; it has no CTs yet.
        for widget in (self.breaker_feed_combo, self.ct_editor):
            self.breaker_form.setRowVisible(widget, not is_feed and not is_line_side)
        self.breaker_form.setRowVisible(self.mounting_combo, kind in (MAIN, SINGLE, LINE_SIDE))
        self.breaker_form.setRowVisible(self.feed_source_combo, is_main)
        self.breaker_form.setRowVisible(self.interlock_editor, is_main)
        self.breaker_form.setRowVisible(self.feed_info, is_feed)
        self.breaker_form.setRowVisible(self.fed_from_combo, is_line_side)
        self.termination_form.setRowVisible(self.termination_feed_combo, not is_line_side)
        if kind in (MAIN, SINGLE, LINE_SIDE):
            _set_quietly(self.mounting_combo, self.mounting_combo.setCurrentText, arrangement.mounting)
        if is_main:
            self._load_feed_sources(arrangement)
        if is_line_side:
            self._load_fed_from(arrangement)
        if is_feed:
            self.feed_info.setText(self._feed_goes_to(arrangement))
        self._rebuild_attribute_fields()
        self.ct_editor.load(arrangement if kind in (MAIN, SINGLE) else None)
        self.interlock_editor.load(arrangement if is_main else None)
        self.base_ct_editor.load(arrangement if kind == GROUP else None)
        feed = arrangement if is_feed else arrangement.feed if is_main else None
        self.termination_box.setTitle("Output" if kind in (SINGLE, LINE_SIDE) else "Incoming feed")
        self.breaker_form.setRowVisible(self.termination_box, kind in (SINGLE, LINE_SIDE) or feed is not None)
        self.taps_editor.load(feed, arrangement if is_main else None)
        if kind == GROUP:
            self._reload_levels(select_row=0)

    def _load_feed_sources(self, main):
        """"In this riser", or any Incoming feed part in the lineup."""
        switchboard = self._switchboard_provider() if self._switchboard_provider else None
        chosen = "" if main.feed is not None else main.feed_from
        self.feed_source_combo.blockSignals(True)
        self.feed_source_combo.clear()
        self.feed_source_combo.addItem(IN_THIS_RISER, "")
        for place in standalone_feeds(switchboard) if switchboard is not None else []:
            self.feed_source_combo.addItem(f"Incoming feed, {place.where.lower()}", place.feed.id)
        index = self.feed_source_combo.findData(chosen)
        if main.feed is None and index <= 0:
            self.feed_source_combo.addItem("(choose a feed)" if not chosen else "(that feed was removed)", chosen)
            index = self.feed_source_combo.count() - 1
        self.feed_source_combo.setCurrentIndex(max(index, 0))
        self.feed_source_combo.blockSignals(False)

    def _load_fed_from(self, line_side):
        """Every incoming feed in the lineup (a main breaker's own, or one by itself)."""
        switchboard = self._switchboard_provider() if self._switchboard_provider else None
        self.fed_from_combo.blockSignals(True)
        self.fed_from_combo.clear()
        self.fed_from_combo.addItem("(choose a feed)", "")
        for found in all_feeds(switchboard) if switchboard is not None else []:
            self.fed_from_combo.addItem(found.where, found.feed.id)
        index = self.fed_from_combo.findData(line_side.fed_from)
        if index < 0:
            self.fed_from_combo.addItem("(that feed was removed)", line_side.fed_from)
            index = self.fed_from_combo.count() - 1
        self.fed_from_combo.setCurrentIndex(index)
        self.fed_from_combo.blockSignals(False)

    def _fed_from_changed(self, *_):
        line_side = self._arrangement()
        if isinstance(line_side, LineSideBreaker):
            line_side.fed_from = self.fed_from_combo.currentData() or ""
            self.changed.emit()

    def _feed_goes_to(self, feed) -> str:
        switchboard = self._switchboard_provider() if self._switchboard_provider else None
        found = main_fed_by(switchboard, feed.id) if switchboard is not None else None
        if found is None:
            return "Goes to: the main bus (main lugs only)"
        index, part, main = found
        return f"Feeds: {main.breaker.label or 'the main breaker'} (section {index + 1} {part})"

    def _feed_source_changed(self, *_):
        main = self._arrangement()
        if not isinstance(main, MainBreaker):
            return
        chosen = self.feed_source_combo.currentData() or ""
        if self.feed_source_combo.currentText() == IN_THIS_RISER:
            main.feed = main.feed or IncomingFeed()
            main.feed_from = ""
        else:
            main.feed = None
            main.feed_from = chosen
        self.load(self._section)
        self.changed.emit()

    def refresh_meters(self):
        """The lineup's power meters changed: update the meter choices."""
        self.ct_editor.refresh_meters()
        self.base_ct_editor.refresh_meters()
        self.taps_editor.refresh_meters()

    def _arrangement(self):
        return getattr(self._section.contents, self._part)

    def _set_arrangement(self, arrangement):
        setattr(self._section.contents, self._part, arrangement)

    def _show_page_for(self, kind):
        self.stack.setCurrentIndex({EMPTY: 0, MAIN: 1, SINGLE: 1, FEED: 1, LINE_SIDE: 1, GROUP: 2}[kind])

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
        switchboard = self._switchboard_provider() if self._switchboard_provider else None
        if isinstance(current, MainBreaker) and switchboard is not None:
            set_interlock(switchboard, current, "")   # it is no longer a main: no interlock
        # Keep the breaker (and its feed directions) when switching between Main and
        # Single, so what was entered survives.
        was_breaker = isinstance(current, (MainBreaker, SingleBreaker))
        has_breaker = isinstance(current, (MainBreaker, SingleBreaker, LineSideBreaker))
        kept = current.breaker if has_breaker else Breaker("")
        new = {EMPTY: None, MAIN: MainBreaker(kept), SINGLE: SingleBreaker(kept),
               GROUP: GroupMounted(), FEED: IncomingFeed(), LINE_SIDE: LineSideBreaker(kept)}[kind]
        # Mains, single and line-side breakers use the same blocks: keep the mounting.
        if has_breaker and isinstance(new, (MainBreaker, SingleBreaker, LineSideBreaker)):
            new.mounting = current.mounting
        # A main breaker's own feed and an Incoming feed part carry over into each other.
        if kind == FEED and isinstance(current, MainBreaker) and current.feed is not None:
            new = current.feed
        if kind == MAIN and isinstance(current, IncomingFeed):
            new.feed = current
        if was_breaker and isinstance(new, (MainBreaker, SingleBreaker)):
            new.breaker_feed = current.breaker_feed
            _, termination_feed = feed_directions(current, self._part)
            if isinstance(new, MainBreaker):
                new.feed.termination_feed = termination_feed
            else:
                new.termination_feed = termination_feed
            new.cts = current.cts
            if isinstance(new, SingleBreaker) and new.cts is not None:
                new.cts.on_main_bus = False          # a choice for mains only
        self._set_arrangement(new)
        self.load(self._section)
        self.changed.emit()

    def set_catalog(self, catalog):
        self._catalog = catalog
        for editor in (self.left_slot, self.right_slot, self.single_slot):
            editor.set_catalog(catalog)
        self.ct_editor.set_catalog(catalog)
        self.base_ct_editor.set_catalog(catalog)
        self.taps_editor.set_catalog(catalog)
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
            breaker_block = self._catalog.get(self._settings.main_breaker.blocks[arrangement.mounting])
            breaker_values = arrangement.breaker.attributes
            if not is_main or arrangement.feed is not None:
                io_block = self._catalog.get(self._settings.input_output.block)
                io_values = arrangement.feed.input_attributes if is_main else arrangement.output_attributes
            self.input_attributes_box.setTitle("Input block attributes" if is_main
                                               else "Output block attributes")
        elif isinstance(arrangement, IncomingFeed) and self._catalog:
            io_block = self._catalog.get(self._settings.input_output.block)
            io_values = arrangement.input_attributes
            self.input_attributes_box.setTitle("Input block attributes")
        elif isinstance(arrangement, LineSideBreaker) and self._catalog:
            breaker_block = self._catalog.get(self._settings.main_breaker.blocks[arrangement.mounting])
            breaker_values = arrangement.breaker.attributes
            io_block = self._catalog.get(self._settings.input_output.block)
            io_values = arrangement.output_attributes
            self.input_attributes_box.setTitle("Output block attributes")
        skip = {self._settings.main_breaker.label_attribute}   # filled by the Label field
        add_attribute_fields(self.breaker_attributes_form, breaker_block, breaker_values, skip,
                             self.changed.emit)
        add_attribute_fields(self.input_attributes_form, io_block, io_values, set(),
                             self.changed.emit)
        self.breaker_attributes_box.setVisible(breaker_block is not None and bool(breaker_block.attributes))
        self.input_attributes_box.setVisible(io_block is not None and bool(io_block.attributes))

    def _mounting_changed(self, mounting):
        arrangement = self._arrangement()
        if isinstance(arrangement, (MainBreaker, SingleBreaker, LineSideBreaker)):
            arrangement.mounting = mounting
            self._rebuild_attribute_fields()     # the other block may have other attributes
            self.changed.emit()

    def _feeds_changed(self, *_):
        arrangement = self._arrangement()
        if isinstance(arrangement, IncomingFeed):
            arrangement.termination_feed = self.termination_feed_combo.currentText()
            self.changed.emit()
        if isinstance(arrangement, (MainBreaker, SingleBreaker)):
            arrangement.breaker_feed = self.breaker_feed_combo.currentText()
            termination_feed = self.termination_feed_combo.currentText()
            if isinstance(arrangement, MainBreaker):
                if arrangement.feed is not None:     # a feed elsewhere has its own direction
                    arrangement.feed.termination_feed = termination_feed
            else:
                arrangement.termination_feed = termination_feed
            self.changed.emit()

    def _breaker_comms_changed(self, *_):
        self._arrangement().breaker.comms_module = read_comms(self.breaker_comms_combo)
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

    def __init__(self, settings, catalog=None, comms_modules=(), switchboard_provider=None):
        super().__init__("Tie breaker")
        self._settings = settings
        self._catalog = catalog
        self._section = None
        self.include_check = QCheckBox("Include a tie breaker")
        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText("e.g. 52-TB02")
        self.steps_combo = ScrollSafeComboBox()
        self.steps_combo.addItems(["down", "up"])
        self.mounting_combo = ScrollSafeComboBox()
        self.mounting_combo.addItems(MOUNTINGS)
        form = QFormLayout(self)
        form.addRow(self.include_check)
        form.addRow("Label", self.label_edit)
        self._switchboard = switchboard_provider or (lambda: None)
        self.comms_combo = comms_combo(comms_choices(comms_modules))      # a tie is a 3WA
        form.addRow("Comms module", self.comms_combo)
        self.comms_combo.currentTextChanged.connect(self._edited)
        self.mms_info = QLabel()
        form.addRow("DAS/MMS", self.mms_info)
        form.addRow("Bus steps", self.steps_combo)
        form.addRow("Mounting", self.mounting_combo)
        self.attributes_box = QGroupBox("Breaker block attributes")
        self.attributes_form = QFormLayout(self.attributes_box)
        form.addRow(self.attributes_box)
        self.ct_editor = CtEditor("Current transformers", "cts", settings, catalog, switchboard_provider)
        self.ct_editor.changed.connect(self.changed)
        form.addRow(self.ct_editor)
        self.include_check.toggled.connect(self._include_toggled)
        self.label_edit.textEdited.connect(self._edited)
        self.steps_combo.currentTextChanged.connect(self._edited)
        self.mounting_combo.currentTextChanged.connect(self._edited)

    def load(self, section):
        self._section = section
        tie = section.contents.tie
        _set_quietly(self.include_check, self.include_check.setChecked, tie is not None)
        _set_quietly(self.label_edit, self.label_edit.setText, tie.breaker.label if tie else "")
        set_comms(self.comms_combo, tie.breaker.comms_module if tie else "")
        _set_quietly(self.steps_combo, self.steps_combo.setCurrentText, tie.bus_steps if tie else "down")
        _set_quietly(self.mounting_combo, self.mounting_combo.setCurrentText, tie.mounting if tie else MOUNTINGS[0])
        for widget in (self.label_edit, self.steps_combo, self.mounting_combo, self.comms_combo):
            widget.setEnabled(tie is not None)
        switchboard = self._switchboard()
        name = mms_name(switchboard, tie.breaker) if tie is not None and switchboard is not None else ""
        self.mms_info.setText(f"{name} (added automatically)" if tie is not None else "")
        self._rebuild_attribute_fields()
        self.ct_editor.load(tie)

    def set_catalog(self, catalog):
        self._catalog = catalog
        self.ct_editor.set_catalog(catalog)
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
            tie.breaker.comms_module = read_comms(self.comms_combo)
            tie.bus_steps = self.steps_combo.currentText()
            tie.mounting = self.mounting_combo.currentText()
            if mounting_changed:
                self._rebuild_attribute_fields()     # the other block may have other attributes
            self.changed.emit()


class SectionEditor(QWidget):
    """Everything about the selected section."""
    changed = Signal()

    def __init__(self, settings, catalog=None, comms_modules=(), meter_models=(),
                 switchboard_provider=None, fuse=None, power_supply=None):
        """`switchboard_provider()` returns the whole lineup (for the power meter list)."""
        super().__init__()
        self.title = QLabel()
        self.title.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.above_editor = ArrangementEditor("Above the main bus", "above", settings, catalog,
                                              comms_modules, switchboard_provider, fuse)
        self.below_editor = ArrangementEditor("Below the main bus", "below", settings, catalog,
                                              comms_modules, switchboard_provider, fuse)
        self.tie_editor = TieEditor(settings, catalog, comms_modules, switchboard_provider)
        self.devices_editor = DevicesEditor(meter_models, switchboard_provider, catalog, power_supply)
        for editor in (self.above_editor, self.below_editor, self.tie_editor, self.devices_editor):
            editor.changed.connect(self.changed)
            # A comms module or a meter may now need the Ethernet switch (decision 2026-11-09).
            editor.changed.connect(self.devices_editor.refresh_ethernet)
        self.devices_editor.changed.connect(self._meters_changed)

        layout = QVBoxLayout(self)
        layout.addWidget(self.title)
        layout.addWidget(self.above_editor)
        layout.addWidget(self.below_editor)
        layout.addWidget(self.tie_editor)
        layout.addWidget(self.devices_editor)
        layout.addStretch()
        self.load(None, 0)

    def set_catalog(self, catalog):
        self.above_editor.set_catalog(catalog)
        self.below_editor.set_catalog(catalog)
        self.tie_editor.set_catalog(catalog)
        self.devices_editor.set_catalog(catalog)

    def load(self, section, number):
        has_section = section is not None
        for editor in (self.above_editor, self.below_editor, self.tie_editor, self.devices_editor):
            editor.setEnabled(has_section)
        if not has_section:
            self.title.setText("No section selected")
            return
        self.title.setText(f"Section {number}")
        self.above_editor.load(section)
        self.below_editor.load(section)
        self.tie_editor.load(section)
        self.devices_editor.load(section)

    def _meters_changed(self):
        self.above_editor.refresh_meters()
        self.below_editor.refresh_meters()
        self.tie_editor.ct_editor.refresh_meters()
