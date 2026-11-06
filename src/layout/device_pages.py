"""Device pages (decision 2026-10-23): power meters and the fuses of voltage taps, on pages
after the 3-line, grouped by the section each device lives in.

    SECTION 3
       FROM ES_01                         FROM ES_02
        |  |  |    fuse FA-3-12             |  |  |   fuse FA-3-13 (its meter is
       [  fuse  ]                          [  fuse  ]  in another section)
        |  |  |    wires to the meter       |  |  |
     [      meter PM-3-1       ]           TO PM-2-1 SHEET 4
      FROM STB-3-1   FROM STB-3-2
       (CT inputs)

Where things live: a meter in the section it is mounted in; a voltage tap's fuse in the
tap's section; CTs and their shorting kit where the CTs are drawn (on the 3-line).

Connections: a fuse and its meter in the same section are joined by wires the program
draws (no block), one per phase, on the wire layers in config/devices.json, landing on the
meter's voltage terminals (UMG 801: A to V1, B to VN, C to V3). Anything leaving the section
gets a TO / FROM bracket (the bus-break bracket block), and so does anything coming from the
3-line: a fuse's line side ("FROM ES_01", where its tap is), and a meter's CT inputs (their
own block, "FROM STB-s-k SHEET n"). A meter whose fuse is in another section gets its
voltage input block ("FROM FA-s-n SHEET n").

Power supplies (decision 2026-11-05, option A): the fuse lies down to the left of the power
supply, its load side lined up with the supply's inputs (L1-L3), so the three wires run
straight across; its line side comes FROM the 3-line through tildes and a bracket on the left:

    FROM ES_01 ]~--[ FA-3-2 ]-------[ PS-3-1 ]
               ]~--[        ]-------[        ]
               ]~--[        ]-------[        ]

A power supply whose fuse is in another section gets the same tildes and bracket on its
inputs, "FROM FA-s-n SHEET n"; the fuse, on its own, says "TO PS-s-n SHEET n". Its 24 V
outputs are not connected yet (they come with the communications page).

Layout: each meter (with its wired fuse and its CT inputs), each power supply (with its wired
fuse) and each fuse on its own is a "unit". Units are placed in rows, left to right, then down, under a "SECTION n" heading per
section, as many per page as fit, clear of the title block. Sizes come from the blocks in
the catalog; spacing from config ("device_pages").

Sheets: the device pages are numbered after the 3-line pages. Every cross-reference is
filled in both ways: on the 3-line, a CT set's SHEET# (its meter's page) and a tap's
TO_SHEET (its fuse's page); here, the CT inputs' and voltage inputs' sheets.

Pure Python, no AutoCAD. Coordinates are frame-relative.
"""
from dataclasses import dataclass, field
from itertools import permutations

from src.layout.main_breakers import BlockPlacement, Note, Placeholder, _filled
from src.model.devices import ct_sets_in, meters_in, power_supplies_in, voltage_taps_in

PHASES = "ABC"
UNKNOWN_SHEET = "#"
TOLERANCE = 1e-6


@dataclass
class Wire:
    """A wire the program draws itself (no block), on its own layer."""
    layer: str
    start: tuple[float, float]
    end: tuple[float, float]


@dataclass
class Unit:
    """One meter with what is wired to it, or one fuse on its own, drawn around (0, 0)."""
    section_number: int
    names: list = field(default_factory=list)       # device names placed here ("PM-3-1", "FA-3-12")
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
        page = {"number": first_page + page_index, "blocks": [], "wires": [], "placeholders": [],
                "notes": list(placed["notes"])}
        for unit, dx, dy in placed["units"]:
            unit = by_key[(unit.section_number, tuple(unit.names))]
            page["blocks"] += [_moved_block(b, dx, dy) for b in unit.blocks]
            page["wires"] += [Wire(w.layer, (w.start[0] + dx, w.start[1] + dy), (w.end[0] + dx, w.end[1] + dy))
                              for w in unit.wires]
            page["placeholders"] += [Placeholder(p.text, p.left_x + dx, p.bottom_y + dy, p.right_x + dx,
                                                 p.top_y + dy) for p in unit.placeholders]
        result.pages.append(page)
    return result


def three_line_sheet_values(settings, devices, sheets: dict) -> dict:
    """{(block name, attribute that names the device): (attribute to fill, {device: sheet})}
    for the 3-line blocks that point at a device page: a CT set's meter, a tap's fuse."""
    fmt = settings.device_pages.sheet_format
    ct, tap = settings.current_transformers, settings.voltage_taps
    meters = {name: fmt.format(page=page) for name, page in sheets.items() if name.startswith("PM-")}
    fuses = {name[len("FA-"):]: fmt.format(page=page) for name, page in sheets.items() if name.startswith("FA-")}
    return {(ct.block, ct.meter_attribute): (ct.sheet_attribute, meters),
            (tap.block, tap.fuse_number_attribute): (tap.sheet_attribute, fuses)}


# --- Building the units ------------------------------------------------------------------

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
        for supply in self.supplies:
            units.setdefault(supply.section_number, []).append(
                self._supply_unit(supply, wired.get(supply.supply.id), elsewhere.get(supply.supply.id)))
        for meter in self.meters:
            sets = [s for s in self.ct_sets if s.cts.meter_id == meter.meter.id]
            units.setdefault(meter.section_number, []).append(
                self._meter_unit(meter, sets, wired.get(meter.meter.id), elsewhere.get(meter.meter.id)))
        for tap in lone_taps:
            if self.devices.fuse is None or self.devices.fuse.block not in self.catalog:
                continue
            target = meter_of.get(tap.tap.feeds) or supply_of.get(tap.tap.feeds)
            units.setdefault(tap.section_number, []).append(self._fuse_unit(tap, target))
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

    def _sheet(self, page) -> str:
        return self.settings.device_pages.sheet_format.format(page=page) if page else UNKNOWN_SHEET

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
        unit.wires += _route(load_points, targets, top_y, dp.wire_spacing, fuse.wire_layers)
        self._from_bracket(unit, tap, position)

    def _from_bracket(self, unit, tap, position):
        """The fuse's line side: stubs up to a bracket FROM the 3-line page of its tap."""
        br, dp = self.settings.bus_break, self.settings.device_pages
        page = self.section_pages.get(tap.section_number)
        label = dp.from_tap_label.format(page=br.page_reference.format(number=page) if page else UNKNOWN_SHEET)
        line_points = self._fuse_points(position, self.devices.fuse.line_markers)
        unit.wires += [Wire(self.devices.fuse.wire_layers[p], (x, y), (x, y + dp.stub_length))
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
            self._side_bracket(unit, inputs, label)
        return unit

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
        unit.blocks.append(self._fuse_block(tap, position, fuse.horizontal_state))
        load_points = self._fuse_points(position, fuse.horizontal_load_markers)
        for p in PHASES:
            if p in inputs:
                unit.wires += _across(load_points[p], inputs[p], fuse.wire_layers[p])
        page = self.section_pages.get(tap.section_number)
        br = self.settings.bus_break
        label = dp.from_tap_label.format(page=br.page_reference.format(number=page) if page else UNKNOWN_SHEET)
        self._side_bracket(unit, self._fuse_points(position, fuse.horizontal_line_markers), label)

    def _side_bracket(self, unit, points, label):
        """Wires arriving from the left: a stub left from each point, a tilde on each end
        (horizontal state), and the bracket mirrored to face them, with its label."""
        br, dp = self.settings.bus_break, self.settings.device_pages
        layers = self.devices.fuse.wire_layers
        ends = {p: (x - dp.stub_length, y) for p, (x, y) in points.items()}
        unit.wires += [Wire(layers[p], points[p], ends[p]) for p in points]
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
        unit.wires += [Wire(fuse.wire_layers[p], (x, y), (x, y - dp.stub_length)) for p, (x, y) in load_points.items()]
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


def _route(starts: dict, ends: dict, end_y: float, spacing: float, layers: dict) -> list[Wire]:
    """Wires from each phase's start (above) down to its end (the meter terminal, at
    `end_y`): down, across at its own level, down. Levels are `spacing` apart; the order is
    picked so no two wires run on top of each other (they may cross)."""
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
                wires.append(Wire(layers[p], a, b))
    return wires


def _across(start, end, layer) -> list[Wire]:
    """A wire from `start` right to `end`: straight when they are level, otherwise across,
    up or down halfway, and across again."""
    (sx, sy), (ex, ey) = start, end
    if abs(sy - ey) < TOLERANCE:
        return [Wire(layer, start, end)]
    mid_x = (sx + ex) / 2
    return [Wire(layer, start, (mid_x, sy)), Wire(layer, (mid_x, sy), (mid_x, ey)), Wire(layer, (mid_x, ey), end)]


def _moved_block(b, dx, dy) -> BlockPlacement:
    return BlockPlacement(block=b.block, layer=b.layer, position=(b.position[0] + dx, b.position[1] + dy),
                          attributes=dict(b.attributes), visibility=b.visibility, label=b.label,
                          extents=b.extents, flipped=b.flipped, flip_parameter=b.flip_parameter)


# --- Placing the units on pages ------------------------------------------------------------

def _flow(groups, settings) -> list[dict]:
    """Each section is a column running the full height of the page, its "SECTION n" label
    at the top (Sammy, 2026-10-23). Its units stack down the column, `row_gap` apart; when
    the column is full (or would reach the title block) the section carries on in another
    column beside it; when the page is full, on the next page, label again. Sections sit side
    by side, `group_gap` apart. Returns per page {"units": [(unit, dx, dy)], "notes": [...]}."""
    dp, text = settings.device_pages, settings.text
    left = settings.margin_standard
    right = settings.drawable_width - settings.margin_standard
    top = settings.main_bus.content_top_y
    bottom = settings.divider.bottom_y
    first_y = top - text.height - dp.heading_gap        # where a column's first unit starts
    pages = [{"units": [], "notes": []}]
    x = left

    def in_title_block(x_right, y_bottom):
        return x_right > settings.keepout_left_x and y_bottom < settings.keepout_height

    def label(section, at_x):
        pages[-1]["notes"].append(Note(lines=[dp.heading_format.format(number=section)], x=at_x,
                                       middle_y=top - text.height / 2, align="middle_left"))

    for section, units in groups:
        y, column_width = first_y, 0.0
        needs_label = True                  # placed with the section's first unit on a page
        for unit in units:
            l, b, r, t = unit.extents()
            width, height = r - l, t - b
            if column_width and (y - height < bottom or in_title_block(x + width, y - height)):
                x, y, column_width = x + column_width + dp.unit_gap, first_y, 0.0      # next column
            if x > left and (x + width > right or in_title_block(x + width, y - height)):
                if pages[-1]["units"]:
                    pages.append({"units": [], "notes": []})                         # next page
                x, y, column_width = left, first_y, 0.0
                needs_label = True
            if needs_label:
                label(section, x)
                needs_label = False
            pages[-1]["units"].append((unit, x - l, y - t))
            y -= height + dp.row_gap
            column_width = max(column_width, width)
        x += column_width + dp.unit_gap + dp.group_gap
    return pages
