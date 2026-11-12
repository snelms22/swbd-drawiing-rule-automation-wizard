"""Device pages (decision 2026-10-23): power meters, power supplies and the fuses of voltage
taps, on pages after the 3-line: one page per section, titled "ELECTRICAL SCHEMATIC SECTION n"
(decision 2026-11-09, as in the hybrid NTT-013628).

       FROM SHEET 4                       FROM SHEET 5
        |  |  |    fuse FA-12             |  |  |   fuse FA-13 (its meter is
       [  fuse  ]                          [  fuse  ]  in another section)
        |  |  |    wires to the meter       |  |  |
     [      meter PM-1       ]           TO PM-2 SHEET 6
      FROM STB-1   FROM STB-2
       (CT inputs)

Where things live: a meter in the section it is mounted in; a voltage tap's fuse in the
tap's section; CTs and their shorting kit where the CTs are drawn (on the 3-line).

Connections: a fuse and its meter in the same section are joined by wires the program
draws (no block), one per phase, on the wire layers in config/devices.json, landing on the
meter's voltage terminals (UMG 801: A to V1, B to VN, C to V3). Anything leaving the section
gets a TO / FROM bracket (the bus-break bracket block), and so does anything coming from the
3-line: a fuse's line side ("FROM SHEET 4", the sheet its tap is on), and a meter's CT inputs (their
own block, "FROM STB-k SHEET n"). A meter whose fuse is in another section gets its
voltage input block ("FROM FA-n SHEET n").

Boxes until their blocks exist (Sammy, 2026-11-11): the Ethernet switch, in the section ticked
for it, and each breaker's comms module, in its breaker's section ("52-M1 Siemens COM190").
In a section with a power supply they stack to its right, fed + and - 24 V from its outputs
(a first look at 24 V wiring); otherwise they come after the section's other devices, unwired.

Power supplies (decision 2026-11-05, option A): the fuse lies down to the left of the power
supply, its load side lined up with the supply's inputs (L1-L3), so the three wires run
straight across; its line side comes FROM the 3-line through tildes and a bracket on the left:

    FROM SHEET 4 ]~--[ FA-2 ]-------[ PS-1 ]
                 ]~--[        ]-------[        ]
                 ]~--[        ]-------[        ]

A power supply whose fuse is in another section gets the same tildes and bracket on its
inputs, "FROM FA-n SHEET n"; the fuse, on its own, says "TO PS-n SHEET n". Its 24 V
outputs are not connected yet (they come with the communications page).

Layout: each meter (with its wired fuse and its CT inputs), each power supply (with its wired
fuse) and each fuse on its own is a "unit". Each section starts a new page; its units are
placed left to right in rows from the top left (power supplies first, then meters, then
fuses on their own), clear of the title block; a section that doesn't fit carries on on
another page. Sizes come from the blocks in the catalog; spacing from config
("device_pages"). How the devices will be arranged once they are wired together (power
left to right, as in the hybrid NTT-013628) comes with the 24 V chain.

Sheets: the device pages are numbered after the 3-line pages. Every cross-reference is
filled in both ways: on the 3-line, a CT set's SHEET# (its meter's page) and a tap's
TO_SHEET (its fuse's page); here, the CT inputs' and voltage inputs' sheets.

Pure Python, no AutoCAD. Coordinates are frame-relative.
"""
from dataclasses import dataclass, field
from itertools import permutations

from src.layout.main_breakers import BlockPlacement, Placeholder, _filled
from src.model.devices import (
    comms_modules_in, ct_sets_in, ethernet_switch_sections, meters_in, power_supplies_in,
    voltage_taps_in,
)

PHASES = "ABC"
UNKNOWN_SHEET = "#"
TOLERANCE = 1e-6


@dataclass
class Wire:
    """A wire the program draws itself (no block), on its own layer. Every straight piece of
    one wire run carries the run's label ("4A002"; "" = not labelled)."""
    layer: str
    start: tuple[float, float]
    end: tuple[float, float]
    label: str = ""


@dataclass
class WireLabel:
    """A wire's label on the page (decision 2026-11-09): its middle, and turned 90 degrees
    on an upright wire."""
    text: str
    x: float
    y: float
    rotation: float = 0.0


@dataclass
class Unit:
    """One meter with what is wired to it, or one fuse on its own, drawn around (0, 0)."""
    section_number: int
    names: list = field(default_factory=list)       # device names placed here ("PM-1", "FA-12")
    blocks: list = field(default_factory=list)
    wires: list = field(default_factory=list)
    placeholders: list = field(default_factory=list)

    def extents(self):
        xs, ys = [], []
        for b in self.blocks:
            left, bottom, right, top = b.extents
            xs += [b.position[0] + left, b.position[0] + right]
            ys += [b.position[1] + bottom, b.position[1] + top]
        for w in self.wires:
            xs += [w.start[0], w.end[0]]
            ys += [w.start[1], w.end[1]]
        for p in self.placeholders:
            xs += [p.left_x, p.right_x]
            ys += [p.bottom_y, p.top_y]
        return min(xs), min(ys), max(xs), max(ys)


@dataclass
class DevicePages:
    pages: list = field(default_factory=list)       # [(page number, PageParts-like dict)]
    sheets: dict = field(default_factory=dict)      # {device name: page number}
    warnings: list = field(default_factory=list)


def device_pages(switchboard, settings, devices, catalog, first_page: int, section_pages: dict) -> DevicePages:
    """Lay out the device pages. `first_page` is the first device page's number;
    `section_pages` is {section number: its 3-line page}."""
    result = DevicePages()
    if devices is None or catalog is None:
        return result
    builder = _Builder(switchboard, settings, devices, catalog, section_pages, result.warnings)
    groups = builder.groups()
    if not groups:
        return result
    # Sizes don't depend on the sheet numbers, so lay out once, then fill the sheets in.
    placements = _flow(groups, settings)
    for page_index, placed in enumerate(placements):
        for unit, _, _ in placed["units"]:
            for name in unit.names:
                result.sheets[name] = first_page + page_index
    builder.sheets = result.sheets
    builder.warnings = []                       # the second pass repeats them
    final = builder.groups()
    by_key = {(u.section_number, tuple(u.names)): u for _, units in final for u in units}
    for page_index, placed in enumerate(placements):
        title = settings.page_title.device_page_format.format(section=placed["section"])
        page = {"number": first_page + page_index, "blocks": [], "wires": [], "placeholders": [],
                "notes": [], "title": title, "wire_labels": []}
        for unit, dx, dy in placed["units"]:
            unit = by_key[(unit.section_number, tuple(unit.names))]
            page["blocks"] += [_moved_block(b, dx, dy) for b in unit.blocks]
            moved = [Wire(w.layer, (w.start[0] + dx, w.start[1] + dy), (w.end[0] + dx, w.end[1] + dy), w.label)
                     for w in unit.wires]
            page["wires"] += moved
            page["wire_labels"] += _wire_labels(moved, settings.wire_labels.gap)
            page["placeholders"] += [Placeholder(p.text, p.left_x + dx, p.bottom_y + dy, p.right_x + dx,
                                                 p.top_y + dy) for p in unit.placeholders]
        result.pages.append(page)
    # The shipping splits' females (the cables between sections), on a page at the very end.
    split_units = builder.female_units()
    for placed in _flow([(0, split_units)], settings) if split_units else []:
        page = {"number": first_page + len(result.pages), "blocks": [], "wires": [], "placeholders": [],
                "notes": [], "title": settings.page_title.shipping_split_page, "wire_labels": []}
        for unit, dx, dy in placed["units"]:
            page["blocks"] += [_moved_block(b, dx, dy) for b in unit.blocks]
            moved = [Wire(w.layer, (w.start[0] + dx, w.start[1] + dy), (w.end[0] + dx, w.end[1] + dy), w.label)
                     for w in unit.wires]
            page["wires"] += moved
            page["wire_labels"] += _wire_labels(moved, settings.wire_labels.gap)
        result.pages.append(page)
    return result


def three_line_sheet_values(settings, devices, sheets: dict) -> dict:
    """{(block name, attribute that names the device): (attribute to fill, {device: sheet})}
    for the 3-line blocks that point at a device page: a CT set's meter, a tap's fuse."""
    sheet = settings.device_pages.sheet
    ct, tap = settings.current_transformers, settings.voltage_taps
    meters = {name: sheet(page) for name, page in sheets.items() if name.startswith("PM-")}
    fuses = {name[len("FA-"):]: sheet(page) for name, page in sheets.items() if name.startswith("FA-")}
    return {(ct.block, ct.meter_attribute): (ct.sheet_attribute, meters),
            (tap.block, tap.fuse_number_attribute): (tap.sheet_attribute, fuses)}


# --- Building the units ------------------------------------------------------------------

def _box_unit(section_number, name, text, width, height) -> Unit:
    """A device whose block doesn't exist yet: a box with its name, centred on (0, 0)."""
    unit = Unit(section_number, names=[name])
    unit.placeholders.append(Placeholder(text, -width / 2, -height / 2, width / 2, height / 2))
    return unit


class _Builder:
    def __init__(self, switchboard, settings, devices, catalog, section_pages, warnings):
        self.settings, self.devices, self.catalog = settings, devices, catalog
        self.section_pages = section_pages
        self.sheets = {}
        self.warnings = warnings
        self.meters = meters_in(switchboard)
        self.supplies = power_supplies_in(switchboard)
        self.taps = voltage_taps_in(switchboard)
        self.ct_sets = ct_sets_in(switchboard)
        self.comms = comms_modules_in(switchboard)
        self.switch_sections = ethernet_switch_sections(switchboard)
        self.section_count = len(switchboard.sections)
        self.split_pairs = []           # filled by groups(): one per shipping split
        self.feeding_number = None      # n of the PS-n whose 24 V feeds the lineup

    def groups(self) -> list[tuple[int, list[Unit]]]:
        """[(section number, its units)] in lineup order, sections with devices only."""
        meter_of = {m.meter.id: m for m in self.meters}
        supply_of = {s.supply.id: s for s in self.supplies}
        wired, elsewhere = {}, {}          # device id -> the tap wired to it / feeding it from elsewhere
        lone_taps = []
        for tap in self.taps:
            supply = supply_of.get(tap.tap.feeds)
            if supply is not None:
                # One tap per power supply: a second one is warned about (device_problems)
                # and drawn on its own.
                taken = supply.supply.id in wired or supply.supply.id in elsewhere
                if not taken and supply.section_number == tap.section_number and self._can_wire_supply():
                    wired[supply.supply.id] = tap
                    continue
                if not taken:
                    elsewhere[supply.supply.id] = tap
                lone_taps.append(tap)
                continue
            meter = meter_of.get(tap.tap.feeds)
            if meter is not None and meter.section_number == tap.section_number \
                    and meter.meter.id not in wired and self._can_wire(meter):
                wired[meter.meter.id] = tap
                continue
            lone_taps.append(tap)
            if meter is not None:
                if meter.meter.id in elsewhere or meter.meter.id in wired:
                    self.warnings.append(f"{meter.name} has more than one voltage tap; {tap.fuse} is drawn "
                                         f"on its own with a TO bracket.")
                else:
                    elsewhere[meter.meter.id] = tap
        # In each section: power supplies first, top left (Sammy, 2026-11-05: they power what
        # comes after them), then meters, then fuses on their own.
        units = {}
        feeder = None           # (unit, supply): the one power supply whose 24 V feeds the lineup
        for supply in self.supplies:
            unit = self._supply_unit(supply, wired.get(supply.supply.id), elsewhere.get(supply.supply.id))
            units.setdefault(supply.section_number, []).append(unit)
            if feeder is None and self._can_feed(unit):
                feeder = (unit, supply)
        if len(self.supplies) > 1:
            others = [s.name for s in self.supplies if feeder is None or s is not feeder[1]]
            self.warnings.append(f"A lineup has one 24 V power supply (Sammy, 2026-11-11); "
                                 f"{', '.join(others)} {'is' if len(others) == 1 else 'are'} drawn but not wired.")
        for meter in self.meters:
            sets = [s for s in self.ct_sets if s.cts.meter_id == meter.meter.id]
            units.setdefault(meter.section_number, []).append(
                self._meter_unit(meter, sets, wired.get(meter.meter.id), elsewhere.get(meter.meter.id)))
        fuse_units = []                 # (tap, target): fuses on their own, drawn after the splits are known
        for tap in lone_taps:
            if self.devices.fuse is None or self.devices.fuse.block not in self.catalog:
                continue
            fuse_units.append((tap, meter_of.get(tap.tap.feeds) or supply_of.get(tap.tap.feeds)))
        # Boxes until their blocks exist (Sammy, 2026-11-11): the Ethernet switch, then the
        # comms modules. The power supply's 24 V feeds them: in its own section directly,
        # in the other sections through shipping splits. Boxes it can't reach come last in
        # their section, unwired, so the devices already drawn don't move.
        dp = self.settings.device_pages
        boxes = {}              # section number -> [(name, text, width, height)]
        for section_number in self.switch_sections:
            boxes.setdefault(section_number, []).append(
                ("ETHERNET SWITCH", dp.ethernet_switch_text, dp.ethernet_switch_width, dp.ethernet_switch_height))
        for comms in self.comms:
            text = f"{comms.breaker.label} {comms.module}".strip()
            boxes.setdefault(comms.section_number, []).append(
                (f"COMMS-{comms.number}", text, dp.comms_width, dp.comms_height))
        # What crosses the section boundaries, through shipping splits (Sammy, 2026-11-11):
        # the 24 V (+ and -) from the supply's section to every section with a box, and the
        # three phases of a fuse to the meter or power supply it feeds in another section.
        self.split_wires = {}           # {wire key: (layer, label)}
        crossings = []                  # (first section, last section, [wire keys])
        self.feeding_number = feeder[1].number if feeder else None
        if feeder is not None and boxes:
            supply = feeder[1]
            layers = self.devices.power_supply.output_wire_layers
            for sign in "+-":
                self.split_wires[sign] = (layers[sign], self.settings.wire_labels.label(layers[sign], supply.number))
            ends = [supply.section_number, *boxes]
            crossings.append((min(ends), max(ends), ["+", "-"]))
        for tap in lone_taps:
            target = meter_of.get(tap.tap.feeds) or supply_of.get(tap.tap.feeds)
            if target is None or target.section_number == tap.section_number or self.devices.fuse is None:
                continue
            labels = self._labels(tap, "load")
            keys = [f"{tap.fuse} PHASE-{p}" for p in PHASES]
            for p, key in zip(PHASES, keys):
                self.split_wires[key] = (self.devices.fuse.wire_layers[p], labels[p])
            crossings.append((min(tap.section_number, target.section_number),
                              max(tap.section_number, target.section_number), keys))
        males = self._shipping_splits(crossings)
        # A fuse whose wires leave its section through a split lies down in the section's
        # split group and is wired straight into the male (Sammy, 2026-11-11); the others
        # stand on their own with a TO bracket.
        leaving = {}
        lying = bool(self.devices.fuse and self.devices.fuse.horizontal_state)
        for tap, target in fuse_units:
            if (lying and target is not None and target.section_number != tap.section_number
                    and tap.section_number in males):
                leaving.setdefault(tap.section_number, []).append(tap)
            else:
                units.setdefault(tap.section_number, []).append(self._fuse_unit(tap, target))
        if feeder is not None:
            unit, supply = feeder
            left, right = males.pop(supply.section_number, ([], []))
            self._feed(unit, supply, boxes.pop(supply.section_number, []), left, right,
                       leaving.pop(supply.section_number, []))
        for section_number, (left, right) in sorted(males.items()):
            # The section's shipping splits (and its 24 V group, if the 24 V reaches it) come
            # first on its page.
            unit = Unit(section_number)
            fed = feeder is not None and "+" in self.split_wires
            self._feed(unit, feeder[1] if fed else None, boxes.pop(section_number, []) if fed else [], left, right,
                       leaving.pop(section_number, []))
            units.setdefault(section_number, []).insert(0, unit)
        for section_number, specs in boxes.items():
            units.setdefault(section_number, []).extend(_box_unit(section_number, *spec) for spec in specs)
        if self.switch_sections or self.comms:
            self.warnings.append("The Ethernet switch and the comms modules are drawn as boxes until their "
                                 "blocks exist.")
        return sorted(units.items())

    def _model(self, meter):
        model = self.devices.power_meters.get(meter.meter.model)
        if model is None or not model.block or model.block not in self.catalog:
            return None
        return model

    def _can_wire(self, meter) -> bool:
        model = self._model(meter)
        fuse = self.devices.fuse
        return (model is not None and bool(model.voltage_terminals()) and fuse is not None
                and fuse.block in self.catalog)

    def _labels(self, tap, side) -> dict:
        """{phase: label} for a tap's wires: from the 3-line to its fuse ("line", number 2n-1)
        or from its fuse to what it feeds ("load", 2n), n = the tap's number (FA-n)."""
        number = 2 * tap.number - (1 if side == "line" else 0)
        return {p: self.settings.wire_labels.label(layer, number) for p, layer in self.devices.fuse.wire_layers.items()}

    def _sheet(self, page) -> str:
        return self.settings.device_pages.sheet(page) if page else UNKNOWN_SHEET

    def _meter_unit(self, meter, sets, wired_tap, tap_elsewhere) -> Unit:
        unit = Unit(meter.section_number, names=[meter.name])
        model = self._model(meter)
        if model is None:
            dp = self.settings.device_pages
            text = f"{meter.name} {meter.meter.model or '(no model)'}".strip()
            unit.placeholders.append(Placeholder(text, -dp.placeholder_width / 2, -dp.placeholder_height / 2,
                                                 dp.placeholder_width / 2, dp.placeholder_height / 2))
            if meter.meter.model:
                self.warnings.append(f"{meter.name} ({meter.meter.model}): its block isn't built yet, so a box "
                                     f"is drawn in its place.")
            return unit
        block = self.catalog[model.block]
        layer = self.devices.fuse.layer if self.devices.fuse else "0"
        unit.blocks.append(BlockPlacement(block=model.block, layer=layer, position=(0.0, 0.0),
                                          attributes=_filled({model.number_attribute: meter.code}),
                                          label=meter.name, extents=block.extents))
        # CT inputs: always FROM the shorting kit on the 3-line.
        if len(sets) > len(model.current_inputs):
            extra = ", ".join(s.shorting_kit for s in sets[len(model.current_inputs):])
            self.warnings.append(f"{meter.name} takes {len(model.current_inputs)} CT sets; {extra} not drawn.")
        for ct_set, connected in zip(sets, model.current_inputs):
            unit.blocks += self._input_block(block, connected, ct_set.code,
                                             self._sheet(self.section_pages.get(ct_set.section_number)),
                                             f"FROM {ct_set.shorting_kit}")
        self._remote_display(unit, block, model, meter)
        # Voltage: wired to its fuse in the same section, or FROM a fuse elsewhere.
        if wired_tap is not None:
            self._wire_fuse(unit, block, model, wired_tap)
            unit.names.append(wired_tap.fuse)
        elif tap_elsewhere is not None and model.voltage_input is not None:
            unit.blocks += self._input_block(block, model.voltage_input, tap_elsewhere.code,
                                             self._sheet(self.sheets.get(tap_elsewhere.fuse)),
                                             f"FROM {tap_elsewhere.fuse}")
        return unit

    def _remote_display(self, unit, meter_block, model, meter):
        """The meter's remote display to its left, joined meter USB to display USB: left
        `remote_display_gap`, then up `remote_display_rise` into the display (decision
        2026-10-23)."""
        rd, dp = self.devices.remote_display, self.settings.device_pages
        if not meter.meter.remote_display or rd is None:
            return
        block = self.catalog.get(rd.block)
        if block is None or rd.usb_marker not in (block.markers or {}) or model.usb_marker not in meter_block.markers:
            self.warnings.append(f"{meter.name}: its remote display isn't drawn (block \"{rd.block}\" or the USB "
                                 f"markers aren't in catalog/blocks.json; run Audit Blocks).")
            return
        sx, sy = meter_block.markers[model.usb_marker]
        ux, uy = sx - dp.remote_display_gap, sy + dp.remote_display_rise
        mx, my = block.markers[rd.usb_marker]
        unit.blocks.append(BlockPlacement(block=rd.block, layer=rd.layer, position=(ux - mx, uy - my),
                                          attributes=_filled({rd.number_attribute: meter.display_code}),
                                          label=f"RD-{meter.display_code}", extents=block.extents))
        unit.wires += [Wire(rd.usb_layer, (sx, sy), (ux, sy)), Wire(rd.usb_layer, (ux, sy), (ux, uy))]

    def _input_block(self, meter_block, connected, number, sheet, label) -> list:
        own = self.catalog.get(connected.block)
        if own is None:
            self.warnings.append(f'Block "{connected.block}" isn\'t in catalog/blocks.json (run Audit Blocks).')
            return []
        marker, target = next(iter(connected.lands_on.items()))
        tx, ty = meter_block.markers[target]
        mx, my = own.markers[marker]
        values = {connected.number_attribute: number, connected.sheet_attribute: sheet}
        return [BlockPlacement(block=connected.block, layer=self.devices.fuse.layer if self.devices.fuse else "0",
                               position=(tx - mx, ty - my), attributes=_filled(values), label=label,
                               extents=own.extents)]

    def _fuse_block(self, tap, position, state="") -> BlockPlacement:
        """The tap's fuse, standing up (its usual state) or in `state`."""
        fuse = self.devices.fuse
        block = self.catalog[fuse.block]
        state = state or fuse.state
        values = {**tap.tap.fuse_attributes, fuse.number_attribute: tap.code}
        return BlockPlacement(block=fuse.block, layer=fuse.layer, position=position, attributes=_filled(values),
                              visibility=state, label=tap.fuse, extents=tuple(block.states[state]["extents"]))

    def _fuse_points(self, position, markers_by_phase):
        block = self.catalog[self.devices.fuse.block]
        return {p: (position[0] + block.markers[markers_by_phase[p]][0],
                    position[1] + block.markers[markers_by_phase[p]][1]) for p in PHASES}

    def _wire_fuse(self, unit, meter_block, model, tap):
        """The fuse above the meter, its load side wired to the meter's voltage terminals,
        its line side FROM the 3-line page of its tap."""
        fuse = self.devices.fuse
        dp = self.settings.device_pages
        block = self.catalog[fuse.block]
        targets = {p: meter_block.markers[m] for p, m in model.voltage_terminals().items()}
        top_y = max(y for _, y in targets.values())
        load = {p: block.markers[fuse.load_markers[p]] for p in PHASES}
        # The fuse's A sits over the leftmost terminal, its load side 4 wire spacings up.
        position = (min(x for x, _ in targets.values()) - load["A"][0], top_y + 4 * dp.wire_spacing - load["A"][1])
        unit.blocks.append(self._fuse_block(tap, position))
        load_points = self._fuse_points(position, fuse.load_markers)
        unit.wires += _route(load_points, targets, top_y, dp.wire_spacing, fuse.wire_layers, self._labels(tap, "load"))
        self._from_bracket(unit, tap, position)

    def _from_bracket(self, unit, tap, position):
        """The fuse's line side: stubs up to a bracket FROM the 3-line page of its tap."""
        br, dp = self.settings.bus_break, self.settings.device_pages
        page = self.section_pages.get(tap.section_number)
        label = dp.from_tap_label.format(page=br.page_reference.format(sheet=dp.sheet_number(page)) if page else UNKNOWN_SHEET)
        line_points = self._fuse_points(position, self.devices.fuse.line_markers)
        labels = self._labels(tap, "line")
        unit.wires += [Wire(self.devices.fuse.wire_layers[p], (x, y), (x, y + dp.stub_length), labels[p])
                       for p, (x, y) in line_points.items()]
        unit.blocks += self._wire_breaks([(x, y + dp.stub_length) for x, y in line_points.values()])
        b_x, end_y = line_points["B"][0], line_points["B"][1] + dp.stub_length
        unit.blocks.append(self._bracket((b_x, end_y + br.bracket_gap), label, flipped=False))

    # --- Power supplies (decision 2026-11-05) ---------------------------------------------

    def _can_wire_supply(self) -> bool:
        """Can a fuse lie down beside a power supply? (Its horizontal state and markers.)"""
        fuse, supply = self.devices.fuse, self.devices.power_supply
        if fuse is None or supply is None or fuse.block not in self.catalog or supply.block not in self.catalog:
            return False
        block = self.catalog[fuse.block]
        markers = list((fuse.horizontal_line_markers or {}).values()) + list((fuse.horizontal_load_markers or {}).values())
        return (bool(fuse.horizontal_state) and fuse.horizontal_state in (block.states or {})
                and bool(markers) and all(m in (block.markers or {}) for m in markers))

    def _supply_unit(self, info, wired_tap, tap_elsewhere) -> Unit:
        """A power supply at (0, 0), with its fuse lying down to its left (same section) or
        FROM its fuse in another section."""
        unit = Unit(info.section_number, names=[info.name])
        settings = self.devices.power_supply
        block = self.catalog.get(settings.block) if settings else None
        if block is None or any(m not in (block.markers or {}) for m in settings.inputs.values()):
            dp = self.settings.device_pages
            unit.placeholders.append(Placeholder(f"{info.name} power supply", -dp.placeholder_width / 2,
                                                 -dp.placeholder_height / 2, dp.placeholder_width / 2,
                                                 dp.placeholder_height / 2))
            self.warnings.append(f"{info.name}: the power supply block (or its input markers) isn't in "
                                 f"catalog/blocks.json, so a box is drawn in its place (run Audit Blocks).")
            return unit
        unit.blocks.append(BlockPlacement(block=settings.block, layer=settings.layer, position=(0.0, 0.0),
                                          attributes=_filled({**info.supply.attributes,
                                                              settings.number_attribute: info.code}),
                                          label=info.name, extents=block.extents))
        inputs = {p: block.markers[m] for p, m in settings.inputs.items()}
        if wired_tap is not None:
            self._fuse_beside(unit, block, inputs, wired_tap)
            unit.names.append(wired_tap.fuse)
        elif tap_elsewhere is not None:
            dp = self.settings.device_pages
            label = dp.from_fuse_label.format(fuse=tap_elsewhere.fuse,
                                              sheet=self._sheet(self.sheets.get(tap_elsewhere.fuse)))
            self._side_bracket(unit, inputs, label, self._labels(tap_elsewhere, "load"))
        return unit

    def _can_feed(self, unit) -> bool:
        """Is this power supply drawn with its block, which has the 24 V output markers?"""
        settings = self.devices.power_supply
        if settings is None or not unit.blocks or unit.blocks[0].block != settings.block:
            return False
        markers = self.catalog[settings.block].markers or {}
        return (set(settings.outputs) == {"+", "-"} and all(m in markers for m in settings.outputs.values())
                and set(settings.output_wire_layers) == {"+", "-"})

    def _shipping_splits(self, crossings) -> dict:
        """The males each section draws, {section: (left males, right males)}, each male
        (name, {wire key: pin}); and self.split_pairs, one per split, for the page of
        females at the end (Sammy, 2026-11-11).

        `crossings` is [(first section, last section, wire keys)]: those wires cross every
        boundary from the first section to the last. At each boundary the wires take the next
        free pins, in that order (24 V first); a boundary with more wires than one split has
        pins gets more splits. Names are numbered within their section, males and females
        separately, left boundary first. Empty without the split blocks."""
        self.split_pairs = []
        ss = self.devices.shipping_split
        if (not crossings or ss is None or ss.male_block not in self.catalog
                or ss.female_block not in self.catalog):
            return {}
        per_boundary = {}
        for first, last, keys in crossings:
            for b in range(first, last):
                per_boundary.setdefault(b, []).extend(keys)
        groups = {b: [wires[i:i + ss.pins] for i in range(0, len(wires), ss.pins)]
                  for b, wires in per_boundary.items()}
        count = {}

        def name(section, female=False):
            count[(section, female)] = count.get((section, female), 0) + 1
            return (ss.female_name if female else ss.male_name).format(
                section=section, number=count[(section, female)])

        def pins(group):
            return {wire: index + 1 for index, wire in enumerate(group)}

        males = {}
        for section in range(1, self.section_count + 1):
            left = [(name(section), pins(g)) for g in groups.get(section - 1, [])]
            right = [(name(section), pins(g)) for g in groups.get(section, [])]
            if left or right:
                males[section] = (left, right)
        pairs = []
        for b in sorted(groups):
            for (left_male, used), (right_male, _) in zip(males[b][1], males[b + 1][0]):
                pairs.append((b, left_male, right_male, used))
        # Female names: each section's left boundary first, then its right.
        female_of = {}
        for section in range(1, self.section_count + 1):
            for b, left_male, right_male, _ in pairs:
                if b + 1 == section:
                    female_of[right_male] = name(section, True)
            for b, left_male, right_male, _ in pairs:
                if b == section:
                    female_of[left_male] = name(section, True)
        self.split_pairs = [(b, female_of[lm], lm, female_of[rm], rm, used) for b, lm, rm, used in pairs]
        return males

    def _feed(self, unit, supply, specs, left_males, right_males, fuses=()):
        """A section's shipping splits and 24 V group (Sammy, 2026-11-11).

        Left column, top down: the power supply's outputs (in its own section), the males
        from the left boundary (flush with the page's left edge), then any fuse whose wires
        leave the section through a split, lying down with its line side FROM the 3-line.
        Right: the males to the right boundary at the page's right edge, each lined up with
        the first wire it shares with the left column, so wires passing through (and a
        fuse's wires on their way out) run straight across the page. The boxes stack down
        below those wires, fed from a + rail and a - rail. The 24 V always joins the rails,
        with a dot where three wires meet. A pin with nothing to meet here (the wire ends at
        a meter or power supply that keeps its FROM bracket) gets a short labelled stub.
        `supply` None: no 24 V here.

            [SSM] + -----+--------------------------------[SSM] +
                  - -----|--+-----------------------------[   ] -
                  A ---------------------------------------[   ] A
                         |  |
                         +--|------->[ box 1 ]
                            +------->[       ]
        """
        ps, ss, dp = self.devices.power_supply, self.devices.shipping_split, self.settings.device_pages
        spacing = dp.wire_spacing
        left, right = [], []        # (wire key, point): "+" / "-" join the rails
        first_middle = None
        if supply is not None and unit.blocks and unit.blocks[0].block == ps.block:   # the supply's section
            block = self.catalog[ps.block]
            plus, minus = block.markers[ps.outputs["+"]], block.markers[ps.outputs["-"]]
            left += [("+", plus), ("-", minus)]
            pin_x = max(plus[0], minus[0])
            top = block.extents[1] - dp.feed_box_spacing             # below the supply
            first_middle = (plus[1] + minus[1]) / 2
        else:
            pin_x, top = 0.0, 0.0
        male = self.catalog[ss.male_block] if (left_males or right_males) else None
        m_left, m_bottom, m_right, m_top = male.extents if male else (0, 0, 0, 0)

        def pin_point(number):
            return male.markers[ss.pin_marker.format(pin=number)]

        # Left column.
        left_male_blocks = []
        male_entries = []                       # which entries of `left` are the left males' pins
        from_left_males = set()
        for name, used in left_males:          # facing right: its pins on its right side
            position = (pin_x - pin_point(1)[0], top - m_top)
            block = BlockPlacement(block=ss.male_block, layer=ss.layer, position=position,
                                   attributes={ss.name_attribute: name}, label=name, extents=male.extents)
            unit.blocks.append(block)
            left_male_blocks.append(block)
            unit.names.append(name)
            points = {key: (position[0] + pin_point(n)[0], position[1] + pin_point(n)[1]) for key, n in used.items()}
            male_entries += range(len(left), len(left) + len(points))
            left += list(points.items())
            from_left_males |= set(points)
            if first_middle is None and "+" in points:
                first_middle = (points["+"][1] + points["-"][1]) / 2
            top = position[1] + m_bottom - dp.feed_box_spacing
        fuse = self.devices.fuse
        column_right = pin_x                    # the rails start this far right of the left column
        for tap in fuses:                       # lying down, its load side at the pin column
            state = fuse.horizontal_state
            block = self.catalog[fuse.block]
            load_a = block.markers[fuse.horizontal_load_markers["A"]]
            position = (pin_x - load_a[0], top - block.states[state]["extents"][3])
            load = self._lying_fuse(unit, tap, position)
            unit.names.append(tap.fuse)
            left += [(f"{tap.fuse} PHASE-{p}", load[p]) for p in PHASES]
            top = position[1] + block.states[state]["extents"][1] - dp.feed_box_spacing
            column_right = max(column_right, position[0] + block.states[state]["extents"][2])
        rail = {"+": column_right + dp.feed_rail_gap}
        rail["-"] = rail["+"] + spacing
        box_left = rail["-"] + dp.feed_box_gap
        wire_end = box_left + dp.feed_into_box
        # The left males sit flush with the page's left edge (the left of everything here).
        if left_male_blocks:
            shift = unit.extents()[0] - min(b.position[0] + m_left for b in left_male_blocks)
            if shift < 0:
                for b in left_male_blocks:
                    b.position = (b.position[0] + shift, b.position[1])
                for i in male_entries:
                    key, (x, y) = left[i]
                    left[i] = (key, (x + shift, y))

        left_points = {}
        for key, point in left:
            left_points.setdefault(key, []).append(point)

        # Right males: at the page's right edge, lined up with a wire from the left column:
        # first choice a wire that isn't 24 V (a fuse's or one passing through), so it runs
        # straight in; else the 24 V from a left male (never the supply's own outputs: the
        # 24 V reaches a male along the rails anyway).
        group_left = unit.extents()[0] if (unit.blocks or unit.wires or unit.placeholders) else 0.0
        group_top = unit.extents()[3] if (unit.blocks or unit.wires or unit.placeholders) else 0.0
        page_width = self.settings.drawable_width - 2 * self.settings.margin_standard
        far_x = group_left + page_width + m_left          # base point of a flipped male flush right

        def right_male_points(x, base_y, used):
            return {key: (x - pin_point(n)[0], base_y + pin_point(n)[1]) for key, n in used.items()}

        def on_page_bottom(base_y):
            return self.settings.main_bus.content_top_y - (group_top - (base_y + m_bottom))

        lined_up, later = [], []
        lowest = None
        for name, used in right_males:
            in_order = sorted(used, key=used.get)
            anchor = (next((k for k in in_order if k in left_points and k not in ("+", "-")), None)
                      or next((k for k in in_order if k in left_points and k in from_left_males), None))
            if anchor is None:
                later.append((name, used))
                continue
            base_y = left_points[anchor][0][1] - pin_point(used[anchor])[1]
            if lowest is not None and base_y + m_top > lowest:
                base_y = lowest - m_top                 # below the one before
            x = far_x if on_page_bottom(base_y) >= self.settings.keepout_height else wire_end + pin_point(1)[0]
            lined_up.append((name, used, (x, base_y)))
            lowest = base_y + m_bottom - dp.feed_box_spacing

        # Wires crossing the box column (to the lined-up males): the boxes go below them.
        band = [p[1] for _, used, (x, y) in lined_up for p in right_male_points(x, y, used).values()]
        band += [left_points[k][0][1] for _, used, _ in lined_up for k in used if k in left_points]
        left_minus = [p[1] for k, p in left if k == "-"]

        def clear_of_left(plus_y):
            # A + wire going right must not run along a - wire coming from the left.
            return all(abs(plus_y - y) > TOLERANCE for y in left_minus)

        if band:
            y_top = min(band) - dp.feed_box_spacing
        elif specs and first_middle is not None:
            y_top = first_middle + specs[0][3] / 2
        else:
            y_top = 0.0
        for name, text, width, height in specs:
            while not clear_of_left(y_top - height / 2 + spacing / 2):
                y_top -= spacing
            unit.placeholders.append(Placeholder(text, box_left, y_top - height, box_left + width, y_top))
            unit.names.append(name)
            middle = y_top - height / 2
            right += [("+", (wire_end, middle + spacing / 2)), ("-", (wire_end, middle - spacing / 2))]
            y_top -= height + dp.feed_box_spacing
        if lowest is not None:
            y_top = min(y_top, lowest)

        # The other right males below the boxes, at the right edge (beside the boxes if that
        # would reach the title block).
        for name, used in later:
            while True:
                base_y = y_top - m_top
                x = far_x if on_page_bottom(base_y) >= self.settings.keepout_height else wire_end + pin_point(1)[0]
                points = right_male_points(x, base_y, used)
                if "+" not in points or clear_of_left(points["+"][1]):
                    break
                y_top -= spacing
            lined_up.append((name, used, (x, base_y)))
            y_top = base_y + m_bottom - dp.feed_box_spacing
        for name, used, (x, base_y) in lined_up:
            unit.blocks.append(BlockPlacement(block=ss.male_block, layer=ss.layer, position=(x, base_y),
                                              attributes={ss.name_attribute: name}, label=name,
                                              extents=(-m_right, m_bottom, -m_left, m_top), flipped=True))
            unit.names.append(name)
            right += list(right_male_points(x, base_y, used).items())

        # Wires that aren't 24 V: left to right straight across (or across, up or down near
        # the male, and in); two ends on the left (a fuse going out the left side): out,
        # up or down, and back; one end only: a short stub.
        right_points = {}
        for key, point in right:
            right_points.setdefault(key, []).append(point)
        keys = [k for k in dict.fromkeys([k for k, _ in left] + [k for k, _ in right]) if k not in ("+", "-")]
        for index, key in enumerate(keys):
            layer, label = self.split_wires[key]
            ends_left, ends_right = left_points.get(key, []), right_points.get(key, [])
            if ends_left and ends_right:
                (lx, ly), (rx, ry) = ends_left[0], ends_right[0]
                if abs(ly - ry) < TOLERANCE:
                    unit.wires.append(Wire(layer, (lx, ly), (rx, ry), label))
                else:
                    turn = rx - dp.split_stub_length
                    unit.wires += [Wire(layer, (lx, ly), (turn, ly), label), Wire(layer, (turn, ly), (turn, ry), label),
                                   Wire(layer, (turn, ry), (rx, ry), label)]
            elif len(ends_left) == 2:
                (ax, ay), (bx, by) = ends_left
                turn = max(ax, bx) + 2.0 + 1.5 * index
                unit.wires += [Wire(layer, (ax, ay), (turn, ay), label), Wire(layer, (turn, ay), (turn, by), label),
                               Wire(layer, (turn, by), (bx, by), label)]
            else:
                for (x, y) in ends_left:
                    unit.wires.append(Wire(layer, (x, y), (x + dp.split_stub_length, y), label))
                for (x, y) in ends_right:
                    unit.wires.append(Wire(layer, (x, y), (x - dp.split_stub_length, y), label))

        if supply is None:
            return
        # The 24 V: each point across to its rail; the rail joins them; a dot where 3+ meet.
        layers = ps.output_wire_layers
        labels = {k: self.settings.wire_labels.label(layers[k], supply.number) for k in "+-"}
        dot = self.settings.main_bus.junction_dot_block
        dot_extents = self.catalog[dot].extents if dot in self.catalog else (-0.75, -0.75, 0.75, 0.75)
        for sign in "+-":
            x = rail[sign]
            ends = [(p, "left") for k, p in left if k == sign] + [(p, "right") for k, p in right if k == sign]
            for point, side in ends:
                start, end = (point, (x, point[1])) if side == "left" else ((x, point[1]), point)
                unit.wires.append(Wire(layers[sign], start, end, labels[sign]))
            ys = sorted({p[1] for p, _ in ends})
            if len(ys) > 1:
                unit.wires.append(Wire(layers[sign], (x, ys[-1]), (x, ys[0]), labels[sign]))
            for y in ys:
                meeting = (any(side == "left" and abs(p[1] - y) < TOLERANCE for p, side in ends)
                           + any(side == "right" and abs(p[1] - y) < TOLERANCE for p, side in ends)
                           + (y < ys[-1]) + (y > ys[0]))
                if meeting >= 3 and dot in self.catalog:
                    unit.blocks.append(BlockPlacement(block=dot, layer=layers[sign], position=(x, y),
                                                      extents=dot_extents))

    def female_units(self) -> list:
        """The page at the end (Sammy, 2026-11-11): for each shipping split, the cable's two
        females side by side, the left section's facing right and the right section's
        facing left, with a labelled wire between them for each pin used."""
        if not self.split_pairs:
            return []
        ss, dp = self.devices.shipping_split, self.settings.device_pages
        female = self.catalog[ss.female_block]
        l, b, r, t = female.extents
        pin_x = female.markers[ss.pin_marker.format(pin=1)][0]
        units = []
        for _, left_name, _, right_name, _, used in self.split_pairs:
            unit = Unit(0, names=[left_name, right_name])
            # Flipped, the left one's pins are on its right side, at x 0; the right one's
            # are on its left side, `shipping_split_cable` further right.
            unit.blocks.append(BlockPlacement(block=ss.female_block, layer=ss.layer, position=(pin_x, 0.0),
                                              attributes={ss.name_attribute: left_name}, label=left_name,
                                              extents=(-r, b, -l, t), flipped=True))
            unit.blocks.append(BlockPlacement(block=ss.female_block, layer=ss.layer,
                                              position=(dp.shipping_split_cable - pin_x, 0.0),
                                              attributes={ss.name_attribute: right_name}, label=right_name,
                                              extents=female.extents))
            for key, number in used.items():
                layer, label = self.split_wires[key]
                y = female.markers[ss.pin_marker.format(pin=number)][1]
                unit.wires.append(Wire(layer, (0.0, y), (dp.shipping_split_cable, y), label))
            units.append(unit)
        return units

    def _fuse_beside(self, unit, supply_block, inputs, tap):
        """The fuse lying down to the left of the power supply: its load side level with the
        supply's inputs, its right edge `wire_spacing` clear of the supply, three wires
        straight across; its line side FROM the 3-line page of its tap, on the left."""
        fuse, dp = self.devices.fuse, self.settings.device_pages
        block = self.catalog[fuse.block]
        load_a = block.markers[fuse.horizontal_load_markers["A"]]
        fuse_right = block.states[fuse.horizontal_state]["extents"][2]
        wire_length = (fuse_right - load_a[0]) + dp.wire_spacing + (inputs["A"][0] - supply_block.extents[0])
        position = (inputs["A"][0] - wire_length - load_a[0], inputs["A"][1] - load_a[1])
        load_points = self._lying_fuse(unit, tap, position)
        load_labels = self._labels(tap, "load")
        for p in PHASES:
            if p in inputs:
                unit.wires += _across(load_points[p], inputs[p], fuse.wire_layers[p], load_labels[p])

    def _lying_fuse(self, unit, tap, position) -> dict:
        """The tap's fuse lying down at `position`, its line side FROM the 3-line page of its
        tap on the left. Returns its load side points {phase: (x, y)}."""
        fuse, dp = self.devices.fuse, self.settings.device_pages
        unit.blocks.append(self._fuse_block(tap, position, fuse.horizontal_state))
        page = self.section_pages.get(tap.section_number)
        br = self.settings.bus_break
        label = dp.from_tap_label.format(page=br.page_reference.format(sheet=dp.sheet_number(page)) if page else UNKNOWN_SHEET)
        self._side_bracket(unit, self._fuse_points(position, fuse.horizontal_line_markers), label,
                           self._labels(tap, "line"))
        return self._fuse_points(position, fuse.horizontal_load_markers)

    def _side_bracket(self, unit, points, label, wire_labels):
        """Wires arriving from the left: a stub left from each point (labelled with
        `wire_labels`, {phase: label}), a tilde on each end (horizontal state), and the bracket
        mirrored to face them, with its label."""
        br, dp = self.settings.bus_break, self.settings.device_pages
        layers = self.devices.fuse.wire_layers
        ends = {p: (x - dp.stub_length, y) for p, (x, y) in points.items()}
        unit.wires += [Wire(layers[p], points[p], ends[p], wire_labels.get(p, "")) for p in points]
        unit.blocks += self._wire_breaks(list(ends.values()), dp.wire_break_state_horizontal,
                                         flip_parameter=dp.wire_break_flip_horizontal)
        bracket = self.catalog[br.bracket_block]
        state = br.bracket_state_horizontal_bus
        left, bottom, right, top = (bracket.states[state]["extents"] if bracket.states and state in bracket.states
                                    else bracket.extents)
        b_x, b_y = ends["B"]
        unit.blocks.append(BlockPlacement(block=br.bracket_block, layer=br.layer, position=(b_x - br.bracket_gap, b_y),
                                          attributes={br.label_attribute_horizontal_bus: label}, label=label,
                                          visibility=state, extents=(-right, bottom, -left, top), flipped=True,
                                          flip_parameter=br.bracket_flip_horizontal_bus))

    def _fuse_unit(self, tap, meter) -> Unit:
        """A fuse on its own: FROM the 3-line above, TO what it feeds (a meter or a power
        supply in another section) below."""
        unit = Unit(tap.section_number, names=[tap.fuse])
        fuse, br, dp = self.devices.fuse, self.settings.bus_break, self.settings.device_pages
        position = (0.0, 0.0)
        unit.blocks.append(self._fuse_block(tap, position))
        self._from_bracket(unit, tap, position)
        load_points = self._fuse_points(position, fuse.load_markers)
        labels = self._labels(tap, "load")
        unit.wires += [Wire(fuse.wire_layers[p], (x, y), (x, y - dp.stub_length), labels[p])
                       for p, (x, y) in load_points.items()]
        if meter is not None:
            unit.blocks += self._wire_breaks([(x, y - dp.stub_length) for x, y in load_points.values()])
            label = dp.to_meter_label.format(meter=meter.name, sheet=self._sheet(self.sheets.get(meter.name)))
            b_x, end_y = load_points["B"][0], load_points["B"][1] - dp.stub_length
            unit.blocks.append(self._bracket((b_x, end_y - br.bracket_gap), label, flipped=True))
        return unit

    def _wire_breaks(self, ends, state_name="", flip_parameter="") -> list:
        """A tilde on each wire end that goes on through a TO / FROM bracket: its CONN point on
        the end, in its vertical state (or `state_name`), mirrored with `flip_parameter` when
        given (lying tildes face wires arriving from the left). Every text attribute it has is
        set empty on purpose, not left to the block's default. None if it isn't catalogued."""
        dp = self.settings.device_pages
        state_name = state_name or dp.wire_break_state
        block = self.catalog.get(dp.wire_break_block)
        if block is None or not block.states or state_name not in block.states:
            return []
        state = block.states[state_name]
        mx, my = state["markers"][dp.wire_break_marker]
        left, bottom, right, top = state["extents"]
        extents = (-right, bottom, -left, top) if flip_parameter else (left, bottom, right, top)
        blank = {dp.wire_break_text_attribute: "", **{a.tag: "" for a in block.attributes}}
        return [BlockPlacement(block=dp.wire_break_block, layer=self.settings.bus_break.layer,
                               position=(x - mx, y - my), attributes=blank, visibility=state_name,
                               extents=extents, flipped=bool(flip_parameter), flip_parameter=flip_parameter)
                for x, y in ends]

    def _bracket(self, position, label, flipped) -> BlockPlacement:
        """The bus-break bracket across three vertical wires, label above (or, flipped, below)."""
        br = self.settings.bus_break
        bracket = self.catalog[br.bracket_block]
        left, bottom, right, top = bracket.states[br.bracket_state_vertical_bus]["extents"] \
            if bracket.states and br.bracket_state_vertical_bus in bracket.states else bracket.extents
        extents = (left, -top, right, -bottom) if flipped else (left, bottom, right, top)
        return BlockPlacement(block=br.bracket_block, layer=br.layer, position=position,
                              attributes={br.label_attribute_vertical_bus: label}, label=label,
                              visibility=br.bracket_state_vertical_bus, extents=extents, flipped=flipped,
                              flip_parameter=br.bracket_flip_vertical_bus if flipped else "")


def _route(starts: dict, ends: dict, end_y: float, spacing: float, layers: dict, labels=None) -> list[Wire]:
    """Wires from each phase's start (above) down to its end (the meter terminal, at
    `end_y`): down, across at its own level, down. Levels are `spacing` apart; the order is
    picked so no two wires run on top of each other (they may cross). `labels`: {phase: label}."""
    labels = labels or {}
    phases = [p for p in PHASES if p in starts and p in ends]
    for order in permutations(phases):
        levels = {p: end_y + spacing * (len(order) - k) for k, p in enumerate(order)}
        runs = []
        for p in phases:
            sx, sy = starts[p]
            ex, ey = ends[p]
            runs.append((p, sx, levels[p], sy))       # upper vertical: from the level up to the start
            runs.append((p, ex, ey, levels[p]))       # lower vertical: from the end up to the level
        if not any(a[0] != b[0] and abs(a[1] - b[1]) < TOLERANCE
                   and min(a[3], b[3]) - max(a[2], b[2]) > TOLERANCE
                   for i, a in enumerate(runs) for b in runs[i + 1:]):
            break
    wires = []
    for p in phases:
        (sx, sy), (ex, ey), level = starts[p], ends[p], levels[p]
        points = [(sx, sy), (sx, level), (ex, level), (ex, ey)]
        for a, b in zip(points, points[1:]):
            if abs(a[0] - b[0]) > TOLERANCE or abs(a[1] - b[1]) > TOLERANCE:
                wires.append(Wire(layers[p], a, b, labels.get(p, "")))
    return wires


def _across(start, end, layer, label="") -> list[Wire]:
    """A wire from `start` right to `end`: straight when they are level, otherwise across,
    up or down halfway, and across again."""
    (sx, sy), (ex, ey) = start, end
    if abs(sy - ey) < TOLERANCE:
        return [Wire(layer, start, end, label)]
    mid_x = (sx + ex) / 2
    return [Wire(layer, start, (mid_x, sy), label), Wire(layer, (mid_x, sy), (mid_x, ey), label),
            Wire(layer, (mid_x, ey), end, label)]


def _wire_labels(wires, gap) -> list[WireLabel]:
    """One label per labelled wire run (its pieces share the label): centred on the run's
    longest across piece, `gap` above it; a run that only goes up and down gets its label
    turned 90 degrees, `gap` to the left of its longest piece (decision 2026-11-09)."""
    runs = {}
    for w in wires:
        if w.label:
            runs.setdefault(w.label, []).append(w)
    labels = []
    for text, pieces in runs.items():
        across = [w for w in pieces if abs(w.start[1] - w.end[1]) < TOLERANCE]
        if across:
            w = max(across, key=lambda w: abs(w.end[0] - w.start[0]))
            labels.append(WireLabel(text, (w.start[0] + w.end[0]) / 2, w.start[1] + gap))
        else:
            w = max(pieces, key=lambda w: abs(w.end[1] - w.start[1]))
            labels.append(WireLabel(text, w.start[0] - gap, (w.start[1] + w.end[1]) / 2, rotation=90.0))
    return labels


def _moved_block(b, dx, dy) -> BlockPlacement:
    return BlockPlacement(block=b.block, layer=b.layer, position=(b.position[0] + dx, b.position[1] + dy),
                          attributes=dict(b.attributes), visibility=b.visibility, label=b.label,
                          extents=b.extents, flipped=b.flipped, flip_parameter=b.flip_parameter)


# --- Placing the units on pages ------------------------------------------------------------

def _flow(groups, settings) -> list[dict]:
    """One page per section (decision 2026-11-09). Its units go left to right in a row from
    the top left, `unit_gap` apart; when the next one doesn't fit across (or would reach
    the title block) a new row starts `row_gap` below the tallest unit of the row above;
    when no row fits, the section carries on on another page.
    Returns per page {"section": n, "units": [(unit, dx, dy)]}."""
    dp = settings.device_pages
    left = settings.margin_standard
    right = settings.drawable_width - settings.margin_standard
    top = settings.main_bus.content_top_y
    bottom = settings.divider.bottom_y
    pages = []

    def in_title_block(x_right, y_bottom):
        return x_right > settings.keepout_left_x and y_bottom < settings.keepout_height

    def fits(x, row_top, width, height):
        return x + width <= right and row_top - height >= bottom and not in_title_block(x + width, row_top - height)

    for section, units in groups:
        pages.append({"section": section, "units": []})
        x, row_top, row_height = left, top, 0.0
        for unit in units:
            l, b, r, t = unit.extents()
            width, height = r - l, t - b
            if x > left and not fits(x, row_top, width, height):
                x, row_top, row_height = left, row_top - row_height - dp.row_gap, 0.0       # next row
            if pages[-1]["units"] and not fits(x, row_top, width, height):
                pages.append({"section": section, "units": []})                           # next page
                x, row_top, row_height = left, top, 0.0
            pages[-1]["units"].append((unit, x - l, row_top - t))
            x += width + dp.unit_gap
            row_height = max(row_height, height)
    return pages
