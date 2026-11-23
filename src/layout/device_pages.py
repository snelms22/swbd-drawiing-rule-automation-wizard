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
for it, each 3WA's trip unit (its COM190 named inside it, Sammy 2026-11-17), each COM800, and
each other comms module (a 3VA's COM060), in its breaker's section. The comms modules get no
wires.

24 V (Sammy, 2026-11-13; plan approved 2026-11-16; control_power.py plans it): the trip units
(one shared fuse), the Ethernet switch, the COM800s and the meters with 24 V pins (a fuse each)
are fed from the power supply's fuse column, the - shared; a circuit meeting three or more
points in a section is split on a terminal block there; circuits reach other sections through
shipping splits. Each section's 24 V ladder comes first on its page (power_ladder.py, Sammy
2026-11-17): the devices in a row, + along the top, - along the bottom, the splits at the
ends. This module hands it what stands in the row (_ladder_section). Without a supply that can
feed it, the Ethernet switch is an unwired box and the trip units and COM800s aren't drawn.

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
("device_pages"). A section's 24 V ladder comes first; a ladder wider than a page carries on on
the section's next page.

Sheets: the device pages are numbered after the 3-line pages. Every cross-reference is
filled in both ways: on the 3-line, a CT set's SHEET# (its meter's page) and a tap's
TO_SHEET (its fuse's page); here, the CT inputs' and voltage inputs' sheets.

Pure Python, no AutoCAD. Coordinates are frame-relative.
"""
from dataclasses import dataclass, field
from itertools import permutations

from src.layout.control_power import (
    COM800, ETHERNET_SWITCH, MINUS, PLUS, POWER_METER, TRIP_UNIT, Load, control_power_loads,
    plan_control_power,
)
from src.layout.device_units import (
    TOLERANCE, PageText, Unit, WidePolyline, Wire, label_wires, lane_route, moved_block, wire_breaks,
)
from src.layout.main_breakers import BlockPlacement, Placeholder, _filled
from src.layout.power_ladder import GroundStrip, LadderContext, LadderSection, RowItem, Supply, build_ladder
from src.model.devices import (
    ethernet_connections, comms_modules_in, ct_sets_in, ethernet_switch_sections, meters_in, mms_in, power_supplies_in,
    voltage_taps_in,
)

PHASES = "ABC"
UNKNOWN_SHEET = "#"
# How the boxes waiting for their blocks are named in Generate's note, in this order.
BOXED_LOADS = ((TRIP_UNIT, "trip units"), (ETHERNET_SWITCH, "Ethernet switch"), (COM800, "COM800s"))


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
        page = _empty_page(first_page + page_index, title)
        for unit, dx, dy in placed["units"]:
            _add_unit(page, by_key[(unit.section_number, tuple(unit.names))], dx, dy, settings)
        result.pages.append(page)
    # The shipping splits' females (the cables between sections), on a page at the very end.
    split_units = builder.female_units()
    for placed in _flow([(0, split_units)], settings) if split_units else []:
        page = _empty_page(first_page + len(result.pages), settings.page_title.shipping_split_page)
        for unit, dx, dy in placed["units"]:
            _add_unit(page, unit, dx, dy, settings)
        result.pages.append(page)
    return result


def _empty_page(number, title) -> dict:
    return {"number": number, "blocks": [], "wires": [], "placeholders": [], "notes": [], "title": title,
            "wire_labels": [], "texts": [], "polylines": []}


def _add_unit(page, unit, dx, dy, settings):
    """Put a unit's contents on a page, moved by (dx, dy)."""
    page["blocks"] += [moved_block(b, dx, dy) for b in unit.blocks]
    moved = [Wire(w.layer, (w.start[0] + dx, w.start[1] + dy), (w.end[0] + dx, w.end[1] + dy), w.label)
             for w in unit.wires]
    page["wires"] += moved
    page["wire_labels"] += label_wires(moved, settings.wire_labels.gap)
    page["placeholders"] += [Placeholder(p.text, p.left_x + dx, p.bottom_y + dy, p.right_x + dx, p.top_y + dy)
                             for p in unit.placeholders]
    page["texts"] += [PageText(t.text, t.x + dx, t.y + dy, t.layer, t.height, t.align) for t in unit.texts]
    page["polylines"] += [WidePolyline(p.layer, [(x + dx, y + dy) for x, y in p.points], p.width)
                          for p in unit.polylines]


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
        self.switchboard = switchboard
        self.split_pairs = []           # filled by groups(): one per shipping split
        self.feeding_number = None      # n of the PS-n whose 24 V feeds the lineup
        self.plan = None                # the 24 V plan (control_power.py), when a supply feeds it
        self.split_wires = {}           # {(boundary, wire key): (layer, label)} through the splits
        self.split_inputs = {}          # {meter / supply name: {wire key: its pin}}: phases straight from the split

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
        self.switch_size = self._switch_size()
        supply_units = []               # (supply, its unit)
        for supply in self.supplies:
            unit = self._supply_unit(supply, wired.get(supply.supply.id), elsewhere.get(supply.supply.id))
            units.setdefault(supply.section_number, []).append(unit)
            supply_units.append((supply, unit))
            if feeder is None and self._can_feed(unit):
                feeder = (unit, supply)
        if len(self.supplies) > 1:
            others = [s.name for s in self.supplies if feeder is None or s is not feeder[1]]
            self.warnings.append(f"A lineup has one 24 V power supply (Sammy, 2026-11-11); "
                                 f"{', '.join(others)} {'is' if len(others) == 1 else 'are'} drawn but not wired.")
        meter_units = []                # (meter, its unit): drawn on their own unless the 24 V group takes them
        for meter in self.meters:
            sets = [s for s in self.ct_sets if s.cts.meter_id == meter.meter.id]
            meter_units.append((meter, self._meter_unit(meter, sets, wired.get(meter.meter.id),
                                                        elsewhere.get(meter.meter.id))))
        fuse_units = []                 # (tap, target): fuses on their own, drawn after the splits are known
        for tap in lone_taps:
            if self.devices.fuse is None or self.devices.fuse.block not in self.catalog:
                continue
            fuse_units.append((tap, meter_of.get(tap.tap.feeds) or supply_of.get(tap.tap.feeds)))
        # 24 V (Sammy, 2026-11-13; plan approved 2026-11-16): the trip units, the Ethernet
        # switch and the COM800s, each on its fuse beside the power supply, the - shared,
        # split on terminal blocks (control_power.py plans it). Without a supply that can
        # feed them, the Ethernet switch is an unwired box as before. The comms modules take
        # no 24 V wire: boxes after the section's other devices.
        dp = self.settings.device_pages
        self.feeding_number = feeder[1].number if feeder else None
        self.plan = None
        self.split_wires = {}           # {(boundary, wire key): (layer, label)}
        if feeder is not None and self._can_distribute():
            loads = control_power_loads(self.switchboard, self.devices.control_power, dp)
            loads += self._meter_loads(meter_units)
            layers = self.devices.power_supply.output_wire_layers
            self.plan = plan_control_power(loads, self.devices.control_power, feeder[1].section_number,
                                           lambda sign, n: self.settings.wire_labels.label(layers[sign], n),
                                           row_order=dp.row_order)
            for (boundary, key), label in self.plan.split_labels.items():
                self.split_wires[(boundary, key)] = (layers[key[0]], label)
        # What crosses the section boundaries besides the 24 V (Sammy, 2026-11-11): the three
        # phases of a fuse to the meter or power supply it feeds in another section.
        self.fa_wires = {}              # {wire key: (layer, label)} for the fuses' phases
        self.fa_ends = {}               # {wire key: (fuse, its section, what it feeds, its section)}
        fa_crossings = []
        for tap in lone_taps:
            target = meter_of.get(tap.tap.feeds) or supply_of.get(tap.tap.feeds)
            if target is None or target.section_number == tap.section_number or self.devices.fuse is None:
                continue
            labels = self._labels(tap, "load")
            keys = [f"{tap.fuse} PHASE-{p}" for p in PHASES]
            first, last = sorted((tap.section_number, target.section_number))
            for p, key in zip(PHASES, keys):
                self.fa_wires[key] = (self.devices.fuse.wire_layers[p], labels[p])
                self.fa_ends[key] = (tap.fuse, tap.section_number, target.name, target.section_number)
                for boundary in range(first, last):
                    self.split_wires[(boundary, key)] = self.fa_wires[key]
            fa_crossings.append((first, last, keys))
        males = self._shipping_splits(fa_crossings)
        # A 3WA's comms module (COM190) is part of its trip unit's block (Sammy, 2026-11-17):
        # when the trip units are drawn, it is named in its trip unit's box instead.
        in_trip_unit = {id(info.breaker) for info in mms_in(self.switchboard)} if self.plan is not None else set()
        loose_comms = [c for c in self.comms if id(c.breaker) not in in_trip_unit]
        # A fuse whose phases leave to the right through a split lies down beside that split,
        # wired straight in (Sammy, 2026-11-11 / 2026-11-17: lone fuses near the split their
        # wires leave by); the others stand on their own with a TO bracket.
        wired_in = {}
        lying = bool(self.devices.fuse and self.devices.fuse.horizontal_state)
        for tap, target in fuse_units:
            if (lying and target is not None and target.section_number > tap.section_number
                    and males.get(tap.section_number, ([], []))[1]):
                wired_in.setdefault(tap.section_number, []).append(tap)
            else:
                units.setdefault(tap.section_number, []).append(self._fuse_unit(tap, target))
        # Each section's 24 V ladder comes first on its page (power_ladder.py, Sammy
        # 2026-11-17): the supply, the devices in a row, the splits at the ends.
        ladder_sections = set(males)
        if self.plan is not None:
            ladder_sections |= {self.plan.supply_section} | {load.section_number for load in self.plan.loads}
        self.switch_items = {load.name: self._switch_item(load) for load in (self.plan.loads if self.plan else [])
                             if load.kind == ETHERNET_SWITCH}
        self.switch_items = {name: item for name, item in self.switch_items.items() if item is not None}
        self.ground = self._ground(feeder, supply_units, meter_units)
        taken = set()                   # ids of the units the ladders drew
        context = LadderContext(self.plan, self.settings, self.devices, self.catalog, self.fa_wires,
                                lambda name: self._sheet(self.sheets.get(name)), self.warnings,
                                other_ends=self.fa_ends)
        for section_number in sorted(ladder_sections):
            section = self._ladder_section(section_number, males, feeder, meter_units, loose_comms,
                                           wired_in.get(section_number, []))
            if section.supply is not None:
                taken.add(id(feeder[0]))
            taken |= {id(item.unit) for item in section.devices}
            pieces = build_ladder(section, context)
            units[section_number] = pieces + [u for u in units.get(section_number, []) if id(u) not in taken]
        # A supply whose phases were to come straight in from the split, but that no ladder
        # drew (it doesn't feed the 24 V): its FROM bracket after all.
        for supply, unit in supply_units:
            if supply.name in self.split_inputs and id(unit) not in taken:
                self._supply_from_bracket(unit, self.split_inputs.pop(supply.name), elsewhere[supply.supply.id])
        for meter, unit in meter_units:
            if id(unit) not in taken:
                units.setdefault(meter.section_number, []).append(unit)
        if self.plan is None:
            for number, section_number in enumerate(self.switch_sections[:1], start=1):
                units.setdefault(section_number, []).append(_box_unit(
                    section_number, f"ES-{number}", self._switch_text(), dp.ethernet_switch_width,
                    dp.ethernet_switch_height))
        for comms in loose_comms:           # in the row where there is a ladder, else on their own
            if not (self.plan is not None and comms.section_number in ladder_sections):
                units.setdefault(comms.section_number, []).append(self._comms_box(comms))
        boxed = []
        if self.plan is not None:
            kinds = {load.kind for load in self.plan.loads if load.name not in self.switch_items}
            boxed += [f"the {words}" for kind, words in BOXED_LOADS if kind in kinds]
        elif self.switch_sections:
            boxed.append("the Ethernet switch")
        if loose_comms:
            boxed.append("the comms modules")
        if boxed:
            listed = boxed[0] if len(boxed) == 1 else ", ".join(boxed[:-1]) + " and " + boxed[-1]
            self.warnings.append(f"{listed[0].upper()}{listed[1:]} {'is' if listed == 'the Ethernet switch' else 'are'} "
                                 f"drawn as boxes until their blocks exist.")
        return sorted(units.items())

    def _meter_loads(self, meter_units) -> list:
        """The power meters that take 24 V (their model names its 24 V pins and the block has
        them), as loads drawn whole, with their fuse and inputs, in the 24 V group (decision
        2026-11-12, option A)."""
        loads = []
        for meter, unit in meter_units:
            model = self._model(meter)
            if model is None or not model.supply_pins or not unit.blocks or unit.blocks[0].block != model.block:
                continue
            markers = self.catalog[model.block].markers or {}
            if not all(m in markers for m in model.supply_pins.values()):
                continue
            left, bottom, right, top = unit.extents()
            loads.append(Load(meter.name, POWER_METER, meter.name, meter.section_number, right - left, top - bottom,
                              unit=unit, pins={sign: markers[m] for sign, m in model.supply_pins.items()}))
        return loads

    # --- The 24 V ladder's contents (power_ladder.py, Sammy 2026-11-17) --------------------

    def _ladder_section(self, number, males, feeder, meter_units, loose_comms, wired_in) -> LadderSection:
        """What stands in a section's 24 V ladder: the power supply with its fuse column (in
        its own section), the devices in row order (meters, Ethernet switch, each COM800 with
        the section's COM060s next to it, trip units), and the lone fuses wired into the
        outgoing split."""
        left, right = males.get(number, ([], []))
        section = LadderSection(number, left_males=left, right_males=right,
                                lone_fuses=[self._lone_fuse_item(tap) for tap in wired_in])
        plan = self.plan
        order = {kind: index for index, kind in enumerate(self.settings.device_pages.row_order)}
        meter_index = {meter.name: index for index, (meter, _) in enumerate(meter_units)}
        placed = []                     # (sort key, RowItem)
        fed = set()
        if plan is not None:
            if number == plan.supply_section:
                section.supply = self._supply_item(feeder[0], feeder[1].name)
                section.ground = self.ground
            for load in plan.loads:
                if load.section_number != number:
                    continue
                within = meter_index.get(load.name, 0) if load.kind == POWER_METER else plan.rank[load.name]
                placed.append(((order.get(load.kind, len(order)), within), self._load_item(load)))
                fed.add(load.name)
        # A meter always has its place in the row, fed or not (and with or without the 24 V,
        # so its voltage can come straight in from the split, Sammy 2026-11-19).
        for meter, unit in meter_units:
            if meter.section_number == number and meter.name not in fed:
                placed.append(((order.get(POWER_METER, len(order)), meter_index[meter.name]),
                               RowItem(meter.name, unit, fed_by_split=self.split_inputs.get(meter.name, {}))))
        if plan is not None:
            for comms in loose_comms:       # next to the COM800 they connect to
                if comms.section_number == number:
                    placed.append(((order.get(COM800, len(order)) + 0.5, comms.number),
                                   RowItem(f"COMMS-{comms.number}", self._comms_box(comms))))
        section.devices = [item for _, item in sorted(placed, key=lambda p: p[0])]
        return section

    def _load_item(self, load) -> RowItem:
        """A 24 V load in the row: a meter drawn whole with its 24 V pins, or a box (until its
        block exists) with + and - on its left edge, + near the top and - near the bottom. A
        box with an Ethernet cable (a trip unit's COM190, a COM800) takes it on its right edge,
        half way down; the switch's box takes its cables down its right edge."""
        if load.unit is not None:
            return RowItem(load.name, load.unit, pins=dict(load.pins),
                           fed_by_split=self.split_inputs.get(load.name, {}))
        if load.name in self.switch_items:
            return self.switch_items[load.name]
        dp = self.settings.device_pages
        height = load.height
        if load.kind == ETHERNET_SWITCH and self.switch_size:
            height = max(height, dp.wire_spacing * (self.switch_size[0] + 1))    # room for its ports
        text = self._switch_text() if load.kind == ETHERNET_SWITCH else load.text
        unit = _box_unit(load.section_number, load.name, text, load.width, height)
        box = unit.placeholders[0]
        if load.kind == ETHERNET_SWITCH:
            self._switch_cables(unit, lambda port: (box.right_x, box.top_y - dp.wire_spacing * port), load.name)
        else:
            self._device_cable(unit, load.name, (box.right_x, (box.top_y + box.bottom_y) / 2))
        x = box.left_x + dp.feed_into_box
        return RowItem(load.name, unit, pins={PLUS: (x, box.top_y - dp.box_plus_pin_from_top),
                                              MINUS: (x, box.bottom_y + dp.box_minus_pin_from_bottom)})

    # --- The Ethernet switch and its cables (Sammy, 2026-11-19) ---------------------------

    def _switch_size(self):
        """(ports, block) of the switch: the smallest size with a port for everything that
        plugs into it (devices.ethernet_connections), the customer's connection and a spare.
        Also works out the cables: the customer's on port 1, the others on the next ports in
        lineup order, each numbered E-001, E-002 ... in port order. None without the switch
        settings or a switch ticked."""
        es = self.devices.ethernet_switch
        self.cables = []                # (port, EthernetConnection or None for the customer's, number)
        if es is None or not self.switch_sections:
            return None
        connections = ethernet_connections(self.switchboard)
        needed = len(connections) + 1
        ports, block = es.block_for(needed)
        if needed > ports:
            self.warnings.append(f"The Ethernet switch needs {needed} ports; the biggest has {ports}, so some "
                                 f"connections have no port.")
        if len(self.switch_sections) > 1:
            others = ", ".join(str(n) for n in self.switch_sections[1:])
            self.warnings.append(f"One Ethernet switch per lineup for now: ES-1 is drawn in section "
                                 f"{self.switch_sections[0]}; the switch ticked in section {others} is left out.")
        free = [port for port in range(1, ports + 1) if port != es.customer_port]
        pairs = sorted([(es.customer_port, None)] + list(zip(free, connections)), key=lambda pair: pair[0])
        self.cables = [(port, connection, es.cable_label.format(number=index))
                       for index, (port, connection) in enumerate(pairs, start=1)]
        return ports, block

    def _switch_text(self) -> str:
        """The switch's box text, with its size when known: "ETHERNET SWITCH" / "8 PORT"."""
        text = self.settings.device_pages.ethernet_switch_text
        return f"{text}\n{self.switch_size[0]} PORT" if self.switch_size else text

    def _cable_stub(self, unit, point, out, label, text):
        """One end of an Ethernet cable: a stub from `point` (out -1 to the left, 1 to the right)
        carrying the cable's number, ending in a tilde that says `text`."""
        es, dp = self.devices.ethernet_switch, self.settings.device_pages
        px, py = point
        end = (px + out * es.stub_length, py)
        unit.wires.append(Wire(es.wire_layer, (px, py), end, label))
        unit.blocks += self._wire_breaks([end], dp.wire_break_state_horizontal,
                                         flip_parameter=dp.wire_break_flip_horizontal if out < 0 else "", text=text)

    def _switch_cables(self, unit, port_point, switch_name):
        """The switch's end of every cable: on each port used, a stub and a tilde naming what it
        goes to and its section ("TO PM-1 SECTION 4"), or CUSTOMER CONNECTION. `port_point(port)`
        is where the port is in the unit."""
        es = self.devices.ethernet_switch
        for port, connection, label in self.cables:
            text = (es.customer_connection if connection is None else
                    es.to_device_label.format(device=connection.name, section=connection.section_number))
            self._cable_stub(unit, port_point(port), 1, label, text)

    def _device_cable(self, unit, device, point, out=1):
        """A device's end of its cable, if it has one: a stub and a tilde naming the switch and
        its section ("TO ES-1 SECTION 1"; one switch per lineup for now)."""
        es = self.devices.ethernet_switch
        for port, connection, label in getattr(self, "cables", []):
            if connection is not None and connection.device == device:
                text = es.to_switch_label.format(switch="ES-1", section=self.switch_sections[0])
                self._cable_stub(unit, point, out, label, text)

    def _switch_item(self, load):
        """The switch drawn with its block (the size picked for the lineup), its 24 V pins
        from its markers, its cables on its ports. None (a box instead) until the block has
        its 24 V markers."""
        es = self.devices.ethernet_switch
        if self.switch_size is None:
            return None
        ports, block_name = self.switch_size
        block = self.catalog.get(block_name)
        markers = (block.markers or {}) if block else {}
        if block is None or not all(m in markers for m in es.supply_pins.values()):
            self.warnings.append(f"The Ethernet switch is a box until {block_name} has its 24 V markers "
                                 f"({', '.join(es.supply_pins.values())}); then run Audit Blocks.")
            return None
        unit = Unit(load.section_number, names=[load.name])
        unit.blocks.append(BlockPlacement(block=block_name, layer=es.layer, position=(0.0, 0.0),
                                          attributes={es.name_attribute: load.name}, label=load.name,
                                          extents=block.extents))
        missing = [port for port, _, _ in self.cables if es.port_marker.format(port=port) not in markers]
        if missing:
            self.warnings.append(f"{block_name} has no marker for port {', '.join(str(p) for p in missing)}, "
                                 f"so those cables aren't drawn at the switch.")
        for port, connection, label in [c for c in self.cables if c[0] not in missing]:
            px, py = markers[es.port_marker.format(port=port)]
            out = -1 if px < (block.extents[0] + block.extents[2]) / 2 else 1
            text = (es.customer_connection if connection is None else
                    es.to_device_label.format(device=connection.name, section=connection.section_number))
            self._cable_stub(unit, (px, py), out, label, text)
        return RowItem(load.name, unit, pins={sign: markers[m] for sign, m in es.supply_pins.items()})

    def _ground(self, feeder, supply_units, meter_units):
        """The ground strip in the power supply's section (Sammy, 2026-11-17), and every other
        device's ground by reference: each ground pin (a marker named in ground.pin_markers)
        on a device's block gets a stub ending in a tilde TO the strip. Numbered G001 (to the
        ground bus), G002 (the supply's), then the devices in lineup order. None without a
        24 V ladder to put the strip in."""
        gs = self.devices.ground
        if gs is None or self.plan is None or feeder is None:
            return None
        strip = gs.strip_name.format(section=feeder[1].section_number)

        def label(n):
            return self.settings.wire_labels.label(gs.wire_layer, n)
        ground = GroundStrip(strip, label(2), label(1))
        others = [(info.section_number, 0, index, unit) for index, (info, unit) in enumerate(supply_units)
                  if unit is not feeder[0]]
        others += [(meter.section_number, 1, index, unit) for index, (meter, unit) in enumerate(meter_units)]
        others += [(item.unit.section_number, 2, index, item.unit)
                   for index, item in enumerate(self.switch_items.values())]
        number = 3
        for *_, unit in sorted(others, key=lambda o: o[:3]):
            for block in list(unit.blocks):
                info = self.catalog.get(block.block)
                markers = (info.markers or {}) if info else {}
                for marker in gs.pin_markers:
                    if marker in markers:
                        self._ground_stub(unit, block, markers[marker], label(number),
                                          gs.to_strip_label.format(strip=strip))
                        ground.devices.append((label(number), block.label or unit.names[0]))
                        number += 1
        return ground

    def _ground_stub(self, unit, block, marker, label, text):
        """A device's ground pin by reference: a stub out from the pin, away from the block,
        ending in a tilde that says `text` ("TO 1TBG")."""
        gs, dp = self.devices.ground, self.settings.device_pages
        px, py = block.position[0] + marker[0], block.position[1] + marker[1]
        left, _, right, _ = self.catalog[block.block].extents
        out = -1 if marker[0] < (left + right) / 2 else 1
        end = (px + out * gs.stub_length, py)
        unit.wires.append(Wire(gs.wire_layer, (px, py), end, label))
        unit.blocks += self._wire_breaks([end], dp.wire_break_state_horizontal,
                                         flip_parameter=dp.wire_break_flip_horizontal if out < 0 else "", text=text)

    def _comms_box(self, comms) -> Unit:
        """A breaker's comms module that isn't part of a trip unit (a 3VA's COM060): a small
        box, its breaker and module on two lines. No 24 V: the Siemens cable powers it."""
        dp = self.settings.device_pages
        text = "\n".join(part for part in (comms.breaker.label, comms.module) if part)
        return _box_unit(comms.section_number, f"COMMS-{comms.number}", text, dp.comms_width, dp.comms_height)

    def _supply_item(self, unit, name) -> Supply:
        """The power supply that feeds the lineup, with its fuse column beside it (and its
        phases straight in from the split when its fuse is in a section to its left)."""
        ps, dp = self.devices.power_supply, self.settings.device_pages
        supply_block = self.catalog[ps.block]
        fuses, _ = self._fuse_column(unit, supply_block)
        gs = self.devices.ground
        ground = next((supply_block.markers[m] for m in (gs.pin_markers if gs else ())
                       if m in (supply_block.markers or {})), None)
        return Supply(unit, fuses, supply_block.markers[ps.outputs[MINUS]],
                      supply_block.extents[2] + dp.fuse_column_gap / 2, ground=ground,
                      fed_by_split=self.split_inputs.get(name, {}))

    def _lone_fuse_item(self, tap) -> RowItem:
        """A fuse whose phases leave through the outgoing split: lying down, its line side FROM
        the 3-line, its load side wired straight into the split by the ladder."""
        fuse = self.devices.fuse
        block = self.catalog[fuse.block]
        load_a = block.markers[fuse.horizontal_load_markers["A"]]
        unit = Unit(tap.section_number, names=[tap.fuse])
        load = self._lying_fuse(unit, tap, (-load_a[0], -load_a[1]))
        return RowItem(tap.fuse, unit, phases={f"{tap.fuse} PHASE-{p}": load[p] for p in PHASES})

    def _can_distribute(self) -> bool:
        """Can the 24 V be planned and drawn? The control power settings and the terminal
        block, with its point markers, in the catalog. Says why not when not."""
        cp = self.devices.control_power
        if cp is None:
            return False
        block = self.catalog.get(cp.terminal_block)
        if block is None or not self._terminal_points(block)[0] or not self._terminal_points(block)[1]:
            self.warnings.append(f'The 24 V isn\'t wired: block "{cp.terminal_block}" (with its point markers) '
                                 f"isn't in catalog/blocks.json (run Audit Blocks).")
            return False
        return True

    @staticmethod
    def _terminal_points(block) -> tuple[list, list]:
        """The terminal block's points that take a wire from the left and from the right, top
        first, as marker names: read from the markers' names, <point>_LEFT / <point>_RIGHT
        (Sammy, 2026-11-13). TOP and BOTTOM aren't used: in a strip they face the next
        terminal."""
        sides = {"LEFT": [], "RIGHT": []}
        for name, (_, y) in (block.markers or {}).items():
            point, _, side = name.partition("_")
            if point.isdigit() and side in sides:
                sides[side].append((-y, int(point), name))
        return [n for *_, n in sorted(sides["LEFT"])], [n for *_, n in sorted(sides["RIGHT"])]

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
        names = {}
        if model.number_attribute:
            names[model.number_attribute] = meter.code
        if model.name_attribute:
            names[model.name_attribute] = meter.name
        unit.blocks.append(BlockPlacement(block=model.block, layer=layer, position=(0.0, 0.0),
                                          attributes=_filled(names), label=meter.name, extents=block.extents))
        # CT inputs: always FROM the shorting kit on the 3-line.
        if len(sets) > model.current_sets:
            extra = ", ".join(s.shorting_kit for s in sets[model.current_sets:])
            self.warnings.append(f"{meter.name} takes {model.current_sets} CT sets; {extra} not drawn.")
        if model.wired_by_pins:
            self._pinned_meter(unit, meter, model, block, sets, wired_tap, tap_elsewhere)
            return unit
        for ct_set, connected in zip(sets, model.current_inputs):
            unit.blocks += self._input_block(block, connected, ct_set.code,
                                             self._sheet(self.section_pages.get(ct_set.section_number)),
                                             f"FROM {ct_set.shorting_kit}")
        self._remote_display(unit, block, model, meter)
        self._meter_cable(unit, block, model, meter)
        # Voltage: wired to its fuse in the same section, or FROM a fuse elsewhere.
        if wired_tap is not None:
            self._wire_fuse(unit, block, model, wired_tap)
            unit.names.append(wired_tap.fuse)
        elif tap_elsewhere is not None and model.voltage_input is not None:
            unit.blocks += self._input_block(block, model.voltage_input, tap_elsewhere.code,
                                             self._sheet(self.sheets.get(tap_elsewhere.fuse)),
                                             f"FROM {tap_elsewhere.fuse}")
        return unit

    def _pinned_meter(self, unit, meter, model, block, sets, wired_tap, tap_elsewhere):
        """A meter block with every pin on its edge (the UMG 801 Rev2, Sammy 2026-11-17), at
        (0, 0), wired straight into its pins with horizontal wires:

                                                  FROM SHEET 4 ]~--[ FA-2 ]--+--+------>[  ] VN
            (the fuse lying to the left, A level with its pin;      |        |  +------>[  ] V3
             the other phases turn in lanes)                        +-----------------> [  ] V1
                                       FROM STB-1 SHEET 4 ]~----------------------------[  ] I1+ ...

        - each CT set FROM its shorting kit on the 3-line: a stub out from each of its pins, a
          tilde on each end and a bracket, on the side the set's pins are on;
        - its voltage from its fuse lying to its left (same section), clear of the CT inputs;
          or FROM its fuse in another section, through tildes and a bracket;
        - its remote display on the side its USB pin is on.
        Its 24 V pins are wired by the 24 V ladder (power_ladder.py) when it is fed."""
        dp = self.settings.device_pages
        middle_x = (block.extents[0] + block.extents[2]) / 2
        layers = model.current_wire_layers or {}
        reach = 0.0                     # how far left of the meter the CT inputs reach
        for ct_set, pins in zip(sets, model.current_pins):
            points = {key: block.markers[marker] for key, marker in pins.items()}
            side = "left" if min(x for x, _ in points.values()) < middle_x else "right"
            labels = {key: self.settings.wire_labels.label(layers.get(key[-1], ""),
                                                           3 * ct_set.number - 2 + PHASES.index(key[0]))
                      for key in pins}
            label = dp.from_fuse_label.format(fuse=ct_set.shorting_kit,
                                              sheet=self._sheet(self.section_pages.get(ct_set.section_number)))
            width = self._pin_bracket(unit, points, {key: layers.get(key[-1], "0") for key in pins}, labels,
                                      label, side)
            if side == "left":
                reach = max(reach, width)
        targets = {p: block.markers[m] for p, m in model.voltage_terminals().items()}
        if wired_tap is not None:
            self._fuse_left_of(unit, targets, wired_tap, block.extents[0] - reach)
            unit.names.append(wired_tap.fuse)
        elif tap_elsewhere is not None and targets and self._comes_by_split(meter, tap_elsewhere):
            # Its fuse is in a section to its left: the phases come in on the split on the left
            # and the ladder wires them straight into its pins, no tildes (Sammy, 2026-11-19).
            self.split_inputs[meter.name] = {f"{tap_elsewhere.fuse} PHASE-{p}": point
                                             for p, point in targets.items()}
        elif tap_elsewhere is not None and targets:
            label = dp.from_fuse_label.format(fuse=tap_elsewhere.fuse,
                                              sheet=self._sheet(self.sheets.get(tap_elsewhere.fuse)))
            self._pin_bracket(unit, targets, dict(self.devices.fuse.wire_layers),
                              self._labels(tap_elsewhere, "load"), label, "left")
        self._remote_display(unit, block, model, meter)
        self._meter_cable(unit, block, model, meter)

    def _comes_by_split(self, device, tap) -> bool:
        """Do a meter's or power supply's phases come straight in from the split on its left
        (Sammy, 2026-11-19 / 2026-11-20)? When its fuse is in a section to its left and the
        splits can be drawn (it then stands in its section's row). From the right they would
        have to go round it and its 24 V, so it keeps its FROM bracket."""
        ss = self.devices.shipping_split
        return (tap.section_number < device.section_number and ss is not None and self.devices.fuse is not None
                and ss.male_block in self.catalog and ss.female_block in self.catalog)

    def _pin_bracket(self, unit, points, layers, labels, label, side) -> float:
        """Wires arriving at a block's pins from elsewhere, on its `side` ("left" or "right"):
        a stub out from each pin (labelled), a tilde on each end, and the bracket with `label`
        beside them, centred on them and stretched so its grip lines up with the outer wires
        (Sammy, 2026-11-17: six CT wires outgrow the bracket as drawn). Returns how far from
        the pins they reach."""
        br, dp = self.settings.bus_break, self.settings.device_pages
        out = -1 if side == "left" else 1
        ends = {key: (x + out * dp.stub_length, y) for key, (x, y) in points.items()}
        unit.wires += [Wire(layers[key], points[key], ends[key], labels.get(key, "")) for key in points]
        unit.blocks += self._wire_breaks(list(ends.values()), dp.wire_break_state_horizontal,
                                         flip_parameter=dp.wire_break_flip_horizontal if side == "left" else "")
        bracket = self.catalog[br.bracket_block]
        state = br.bracket_state_horizontal_bus
        left, bottom, right, top = (bracket.states[state]["extents"] if bracket.states and state in bracket.states
                                    else bracket.extents)
        ys = [y for _, y in ends.values()]
        middle = (max(ys) + min(ys)) / 2
        distances = {}
        if br.bracket_stretch_horizontal_bus:
            # Each unit of stretch moves its grip and both arms one unit further out.
            grow = (max(ys) - min(ys)) / 2 - br.bracket_grip_at_rest
            if abs(grow) > TOLERANCE:
                distances = {br.bracket_stretch_horizontal_bus: br.bracket_stretch_at_rest + grow}
                bottom, top = bottom - grow, top + grow
        if side == "left":
            x = min(x for x, _ in ends.values()) - br.bracket_gap
            unit.blocks.append(BlockPlacement(block=br.bracket_block, layer=br.layer, position=(x, middle),
                                              attributes={br.label_attribute_horizontal_bus: label}, label=label,
                                              visibility=state, extents=(-right, bottom, -left, top), flipped=True,
                                              flip_parameter=br.bracket_flip_horizontal_bus, distances=distances))
        else:
            x = max(x for x, _ in ends.values()) + br.bracket_gap
            unit.blocks.append(BlockPlacement(block=br.bracket_block, layer=br.layer, position=(x, middle),
                                              attributes={br.label_attribute_horizontal_bus: label}, label=label,
                                              visibility=state, extents=(left, bottom, right, top),
                                              distances=distances))
        return dp.stub_length + br.bracket_gap + right

    def _fuse_left_of(self, unit, targets, tap, clear_x):
        """The tap's fuse lying down to the left of a block's voltage pins `targets` ({phase:
        (x, y)}), left of `clear_x`: phase A level with its pin (one straight wire); the
        others turn in lanes between the fuse and `clear_x`, the lowest start in the lane
        furthest right, so they don't cross each other."""
        fuse, dp = self.devices.fuse, self.settings.device_pages
        block = self.catalog[fuse.block]
        load = {p: block.markers[fuse.horizontal_load_markers[p]] for p in PHASES}
        y = targets["A"][1] - load["A"][1]
        turning = sorted((p for p in PHASES if abs(load[p][1] + y - targets[p][1]) > TOLERANCE),
                         key=lambda p: load[p][1])
        lanes = {p: clear_x - dp.lane_spacing * (index + 1) for index, p in enumerate(turning)}
        load_x = min(lanes.values(), default=clear_x) - dp.lane_spacing
        load_points = self._lying_fuse(unit, tap, (load_x - load["A"][0], y))
        labels = self._labels(tap, "load")
        for p in PHASES:
            if p in lanes:
                unit.wires += lane_route(load_points[p], targets[p], lanes[p], fuse.wire_layers[p], labels[p])
            else:
                unit.wires.append(Wire(fuse.wire_layers[p], load_points[p], targets[p], labels[p]))

    def _remote_display(self, unit, meter_block, model, meter):
        """The meter's remote display beside it, on the side its USB pin is on, joined meter
        USB to display USB: out `remote_display_gap`, then up `remote_display_rise` into the
        display (decision 2026-10-23; on the right for the UMG 801 Rev2)."""
        rd, dp = self.devices.remote_display, self.settings.device_pages
        if not meter.meter.remote_display or rd is None:
            return
        block = self.catalog.get(rd.block)
        if block is None or rd.usb_marker not in (block.markers or {}) or model.usb_marker not in meter_block.markers:
            self.warnings.append(f"{meter.name}: its remote display isn't drawn (block \"{rd.block}\" or the USB "
                                 f"markers aren't in catalog/blocks.json; run Audit Blocks).")
            return
        sx, sy = meter_block.markers[model.usb_marker]
        out = 1 if sx > (meter_block.extents[0] + meter_block.extents[2]) / 2 else -1
        ux, uy = sx + out * dp.remote_display_gap, sy + dp.remote_display_rise
        mx, my = block.markers[rd.usb_marker]
        unit.blocks.append(BlockPlacement(block=rd.block, layer=rd.layer, position=(ux - mx, uy - my),
                                          attributes=_filled({rd.number_attribute: meter.display_code}),
                                          label=f"RD-{meter.display_code}", extents=block.extents))
        unit.wires += [Wire(rd.usb_layer, (sx, sy), (ux, sy)), Wire(rd.usb_layer, (ux, sy), (ux, uy))]

    def _meter_cable(self, unit, block, model, meter):
        """The meter's end of its Ethernet cable (Sammy, 2026-11-19): from its Ethernet pin,
        away from the meter, ending in a tilde TO the switch."""
        if not model.ethernet_pin or model.ethernet_pin not in (block.markers or {}):
            return
        px, py = block.markers[model.ethernet_pin]
        out = 1 if px > (block.extents[0] + block.extents[2]) / 2 else -1
        self._device_cable(unit, meter.name, (px, py), out)

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
        elif tap_elsewhere is not None and self._comes_by_split(info, tap_elsewhere):
            # Its fuse is in a section to its left: the phases come in on the split on the left
            # and the ladder wires them straight into its inputs, no tildes (Sammy, 2026-11-20).
            self.split_inputs[info.name] = {f"{tap_elsewhere.fuse} PHASE-{p}": point for p, point in inputs.items()}
        elif tap_elsewhere is not None:
            self._supply_from_bracket(unit, {f"PHASE-{p}": point for p, point in inputs.items()}, tap_elsewhere)
        return unit

    def _supply_from_bracket(self, unit, inputs, tap):
        """A power supply's inputs FROM its fuse in another section: stubs, tildes and a
        bracket on its left. `inputs` is {"... PHASE-A": point, ...}."""
        dp = self.settings.device_pages
        label = dp.from_fuse_label.format(fuse=tap.fuse, sheet=self._sheet(self.sheets.get(tap.fuse)))
        points = {key.rsplit("-", 1)[1]: point for key, point in inputs.items()}
        self._side_bracket(unit, points, label, self._labels(tap, "load"))

    def _can_feed(self, unit) -> bool:
        """Is this power supply drawn with its block, which has the 24 V output markers?"""
        settings = self.devices.power_supply
        if settings is None or not unit.blocks or unit.blocks[0].block != settings.block:
            return False
        markers = self.catalog[settings.block].markers or {}
        return (set(settings.outputs) == {"+", "-"} and all(m in markers for m in settings.outputs.values())
                and set(settings.output_wire_layers) == {"+", "-"})

    def _shipping_splits(self, other_crossings) -> dict:
        """The males each section draws, {section: (left males, right males)}, each male
        (name, {wire key: pin}); and self.split_pairs, one per split, for the page of
        females at the end (Sammy, 2026-11-11).

        At each boundary the pins are, top first (Sammy, 2026-11-17): the + wires in the
        plan's order (control_power._boundary_key), then the other wires (`other_crossings`,
        [(first section, last section, wire keys)]: a fuse's phases), then the -. A boundary
        with more wires than one split has pins gets more splits. Names are numbered within
        their section, males and females separately, left boundary first. Empty without the
        split blocks."""
        self.split_pairs = []
        ss = self.devices.shipping_split
        boundaries = {b for first, last, _ in other_crossings for b in range(first, last)}
        if self.plan is not None:
            boundaries |= {b for first, last, _ in self.plan.crossings() for b in range(first, last)}
        if (not boundaries or ss is None or ss.male_block not in self.catalog
                or ss.female_block not in self.catalog):
            return {}
        per_boundary = {}
        for b in sorted(boundaries):
            power = self.plan.boundary_keys(b) if self.plan is not None else []
            others = [key for first, last, keys in other_crossings if first <= b < last for key in keys]
            per_boundary[b] = [k for k in power if k != MINUS] + others + [k for k in power if k == MINUS]
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

    def _fuse_column(self, unit, supply_block) -> tuple[dict, float]:
        """The 24 V fuses (Sammy, 2026-11-13), in a column fuse_column_gap right of the power
        supply: line side on the left, the first level with the supply's + (one straight
        wire), each next one fuse_pitch below, their line sides joined by a bridge. A fuse
        block without its markers is drawn as a box. Returns {circuit key: its fuse's load
        side} and how low the supply and its fuses reach."""
        ps, cp, dp = self.devices.power_supply, self.devices.control_power, self.settings.device_pages
        plus = supply_block.markers[ps.outputs[PLUS]]
        line_x = supply_block.extents[2] + dp.fuse_column_gap
        block = self.catalog.get(cp.fuse_block)
        markers = (block.markers or {}) if block else {}
        drawn = cp.fuse_line_marker in markers and cp.fuse_load_marker in markers
        loads, lines, lowest = {}, [], supply_block.extents[1]
        for index, (name, key) in enumerate(self.plan.fuses):
            y = plus[1] - index * dp.fuse_pitch
            if drawn:
                (lx, ly), (ox, oy) = markers[cp.fuse_line_marker], markers[cp.fuse_load_marker]
                position = (line_x - lx, y - ly)
                unit.blocks.append(BlockPlacement(block=cp.fuse_block, layer=cp.fuse_layer, position=position,
                                                  attributes={cp.fuse_name_attribute: name}, label=name,
                                                  extents=block.extents))
                loads[key] = (position[0] + ox, position[1] + oy)
                lowest = min(lowest, position[1] + block.extents[1])
            else:
                width, height = dp.fuse_box_width, dp.fuse_box_height
                unit.placeholders.append(Placeholder(name, line_x, y - height / 2, line_x + width, y + height / 2))
                loads[key] = (line_x + width, y)
                lowest = min(lowest, y - height / 2)
            unit.names.append(name)
            lines.append((line_x, y))
        if lines:
            unit.wires.append(Wire(ps.output_wire_layers[PLUS], plus, lines[0], self.plan.supply_label))
        if len(lines) > 1:
            unit.polylines.append(WidePolyline(cp.bridge_layer, [lines[0], lines[-1]], cp.bridge_width))
        if lines and not drawn:
            self.warnings.append(f"The 24 V fuses are drawn as boxes until block {cp.fuse_block} has its markers "
                                 f"{cp.fuse_line_marker} and {cp.fuse_load_marker} (then run Audit Blocks).")
        return loads, lowest

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
        for b, left_name, _, right_name, _, used in self.split_pairs:
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
                layer, label = self.split_wires[(b, key)]
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

    def _wire_breaks(self, ends, state_name="", flip_parameter="", text="") -> list:
        """Tildes on these wire ends (device_units.wire_breaks)."""
        return wire_breaks(ends, self.settings, self.catalog, state_name, flip_parameter, text)

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
            if unit.new_page and pages[-1]["units"]:        # a ladder's next page (Sammy, 2026-11-17)
                pages.append({"section": section, "units": []})
                x, row_top, row_height = left, top, 0.0
            elif x > left and not fits(x, row_top, width, height):
                x, row_top, row_height = left, row_top - row_height - dp.row_gap, 0.0       # next row
            if pages[-1]["units"] and not fits(x, row_top, width, height):
                pages.append({"section": section, "units": []})                           # next page
                x, row_top, row_height = left, top, 0.0
            pages[-1]["units"].append((unit, x - l, row_top - t))
            x += width + dp.unit_gap
            row_height = max(row_height, height)
    return pages
