"""The 24 V ladder (Sammy, 2026-11-17; docs/DECISIONS.md "24 V ladder"): how one section's
24 V is drawn on its device page.

    + wires   ════[TB+]══════════════════════════════════   (the farther a wire goes, the higher)
               ↑      ↓               ↓             ↓
    [SS in]──┤      [PM ]           [ES ]          [SS out]   ← splits at the ends, centred
               ↓      ↑               ↑             ↑
    - wires   ════[TB-]══════════════════════════════════   (the farther a wire goes, the lower)

- The devices stand in one row, tops lined up. Each gets its + from a wire that comes down in
  the gap on its left and its - from a wire that comes up in the same gap.
- A wire runs along the top (+) or the bottom (-) at its own height. A wire that goes past
  another's ends runs outside it (higher for +, lower for -), so no two cross.
- Where a circuit splits, its terminal block sits at the top (+) or bottom (-), the wire
  coming in from below (+) or above (-), the wires out from its sides.
- Where the wires come from: in the power supply's section its fuse column (and the supply's
  -); right of the supply the incoming split on the left; left of it, the split on the right.
- A section wider than a page carries on on its next page: every wire that carries on ends
  in one bracket spanning the side ("TO SHEET 6") and picks up from one ("FROM SHEET 5").

The plan (control_power.py) says which wires there are, in which order (fuse column, split
pins); this module only places things and routes the wires. Pure Python, no AutoCAD.
"""
from dataclasses import dataclass, field, replace
from itertools import permutations

from src.layout.control_power import MINUS, PLUS, SOURCE, TERMINAL
from src.layout.device_units import (
    TOLERANCE, PageText, Unit, WidePolyline, Wire, add_unit_to, count_crossings, lane_route, path_wires,
    tilde_text_box, wire_breaks,
)
from src.layout.main_breakers import BlockPlacement


@dataclass
class RowItem:
    """Something standing in a section's row, drawn around its own (0, 0)."""
    name: str                                       # its load name ("PM-1", "TU-2"), or its own name
    unit: Unit
    pins: dict = field(default_factory=dict)        # its 24 V pins in its unit, {"+": (x, y), "-": ...}
    phases: dict = field(default_factory=dict)      # a fuse wired into the outgoing split: {wire key: point}
    fed_by_split: dict = field(default_factory=dict)    # wires from the split on its left straight into
                                                        # its pins (a meter's voltage): {wire key: pin}


@dataclass
class Supply:
    """The power supply that feeds the 24 V, with its fuse and its fuse column, around (0, 0)."""
    unit: Unit
    fuses: dict             # {circuit key: its fuse's load side}
    minus: tuple            # the supply's - output
    minus_lane_x: float     # where its - drops: between the supply and its fuses
    ground: tuple = None    # its ground pin (on its left edge), if it has one
    fed_by_split: dict = field(default_factory=dict)    # its phases straight in from the split on its
                                                        # left (its fuse is in another section): {wire key: input}


@dataclass
class GroundStrip:
    """The ground terminal strip in the power supply's section (Sammy, 2026-11-17): the
    supply's ground wired in, one wire out TO GROUND BUS, and one per other device with a
    ground pin, each a stub and a tilde naming the device (its own stub says TO the strip)."""
    name: str               # "1TBG"
    supply_label: str       # the wire from the supply's ground pin, "G002"
    bus_label: str          # the wire to the ground bus, "G001"
    devices: list = field(default_factory=list)     # [(wire number, device name)]


@dataclass
class LadderSection:
    section: int
    supply: Supply = None
    devices: list = field(default_factory=list)     # [RowItem], the row left to right
    left_males: list = field(default_factory=list)  # [(name, {wire key: pin})], the boundary on the left
    right_males: list = field(default_factory=list)
    lone_fuses: list = field(default_factory=list)  # [RowItem] whose phases go into the right males
    ground: GroundStrip = None                      # in the power supply's section


@dataclass
class LadderContext:
    """What the ladder needs from the rest of the program."""
    plan: object                # the 24 V plan, or None (then only the splits and other wires)
    settings: object            # LayoutSettings
    devices: object             # DeviceSettings
    catalog: dict
    other_wires: dict           # {wire key: (layer, label)} for the wires that aren't 24 V
    sheet_of: object            # name -> sheet text, for the page-break brackets
    warnings: list
    other_ends: dict = field(default_factory=dict)  # {wire key: (from name, its section, to name, its section)}


@dataclass
class _End:
    """One end of a wire: the point it lands on, and the upright lane its leg runs in."""
    point: tuple
    lane_x: float = None


@dataclass
class _Run:
    """A wire along the top or bottom: from one end, along its height, to the other."""
    sign: str
    label: str
    a: _End
    b: _End
    level: int = 0
    height: float = 0.0
    from_terminal: object = None    # (terminal group, its point) when it starts on a terminal block
    key: str = ""                   # its circuit

    def interval(self, terminal_x=None):
        xs = [terminal_x if terminal_x is not None else self.a.lane_x, self.b.lane_x]
        return min(xs), max(xs)


def build_ladder(section: LadderSection, ctx: LadderContext) -> list[Unit]:
    """The section's ladder, one Unit per page it takes (the first first).

    In the power supply's section it is built twice (Sammy, 2026-11-20: the supply and its
    fuses stand beside the + wires, not under them, so more fuses fit). The first time finds
    how high the + wires run and what passes over or under the supply; the second draws it
    with the supply and its fuses moved up that far."""
    if section.supply is None or ctx.plan is None:
        return _Ladder(section, ctx).build()
    trial = _Ladder(section, replace(ctx, warnings=[]))
    trial.build()
    return _Ladder(section, ctx, supply_rise=trial.supply_rise_room(),
                   wires_under_supply=trial.wires_under_supply()).build()


class _Ladder:
    def __init__(self, section, ctx, supply_rise=0.0, wires_under_supply=False):
        self.s, self.ctx = section, ctx
        # The power supply and its fuses: how far above the row's top they stand (worked out
        # by a first build), and whether - wires pass under them (on their way to the split
        # on the left), so the - wires must run below them.
        self.supply_rise = supply_rise
        self.wires_under = wires_under_supply
        self.minus_from_below = False   # does the supply's - come into its terminal group from below
        self.dp, self.br = ctx.settings.device_pages, ctx.settings.bus_break
        self.ss, self.cp, self.ps = ctx.devices.shipping_split, ctx.devices.control_power, ctx.devices.power_supply
        self.unit = Unit(section.section)
        self.number = section.section
        plan = ctx.plan
        self.circuits = {c.key: c for c in plan.circuits} if plan else {}
        self.keys = [key for key in self.circuits if (self.number, key) in plan.edges] if plan else []
        self.male = ctx.catalog[self.ss.male_block] if (section.left_males or section.right_males) else None
        self.terminal = ctx.catalog.get(self.cp.terminal_block) if (plan and self.cp) else None
        self.pins = {}              # {("left" / "right", wire key): (x, y)} on the males
        self.pin_male = {}          # {("left" / "right", wire key): the male's name}
        self.device_at = {}         # {load name: (its RowItem, dx, dy)}
        self.cuts = []              # x where the row may break onto the next page

    # --- 1. Building ---------------------------------------------------------------------

    def build(self) -> list[Unit]:
        flows = self._flow_sides()
        self._place_row(flows)
        self._wire_24v(flows)
        self._ground()
        self._other_wires()
        return self._pages()

    def _flow_sides(self) -> dict:
        """Where this section's 24 V comes from: "supply" (its fuse column), "left" (the
        incoming split on the left, right of the supply) or "right" (left of the supply)."""
        if self.ctx.plan is None:
            return {"from": None}
        supply_section = self.ctx.plan.supply_section
        if self.number == supply_section:
            return {"from": "supply"}
        return {"from": "left" if self.number > supply_section else "right"}

    # --- 2. The row, left to right ---------------------------------------------------------

    def _place_row(self, flows):
        """Place the males, the supply, the source lanes, the devices and the lone fuses
        across, and everything up and down (tops of the row at y 0)."""
        dp, s = self.dp, self.s
        lane = dp.lane_spacing
        wires = self._section_wires()
        self.wires = wires
        # Heights first: the row is as tall as its tallest thing; the males are centred on it.
        # The supply and its fuses hang from above the row (moved up by supply_rise), beside
        # the - wires: they only count when - wires must pass under them.
        heights = [self._height(item.unit) for item in s.devices + s.lone_fuses]
        if s.supply and (self.wires_under or self.ctx.plan is None):
            heights.append(self._supply_depth() + dp.lane_spacing)
        heights += [self._males_height(s.left_males), self._males_height(s.right_males)]
        self.row_height = max(heights + [0.0])
        x = 0.0
        # Left males, their pins facing right, flush left (moved up or down so the first wire
        # that goes straight into something in the row runs level into it).
        if s.left_males:
            x = self._place_males(s.left_males, "left", x, self._straight_in_shift())
            x += self._target_lanes_width("left", wires)
        # The supply and its fuse column (a lane on its left for each of its phases that come
        # straight in from the split).
        if s.supply:
            x += lane * len(self._straight_in_keys(s.supply))
            left, bottom, right, top = s.supply.unit.extents()
            dx, dy = x + (dp.device_gap if s.left_males else 0.0) - left, -top + self.supply_rise
            add_unit_to(self.unit, s.supply.unit, dx, dy)
            self.supply_shift = (dx, dy)
            x = dx + right
        # Where the 24 V comes in from the left: the source lanes and terminal blocks.
        self.source_x = x
        if flows["from"] in ("supply", "left"):
            x += self._source_width(wires) + lane
        # The devices, each with its two lanes on its left (and left of them a lane for each
        # wire that comes straight in from the split on the left: a meter's voltage).
        for item in s.devices:
            self.cuts.append(x)
            x += lane * len(self._straight_in_keys(item))
            left, bottom, right, top = item.unit.extents()
            dx, dy = x + dp.device_gap - left, -top
            add_unit_to(self.unit, item.unit, dx, dy)
            self.device_at[item.name] = (item, dx, dy)
            x = dx + right
        # What stands at the right end: the lone fuses whose phases go into the right males
        # (placed level with them later), the source lanes when the 24 V comes in from the
        # right, the right males' lanes and the right males. The males go to the page's right
        # edge when the ladder fits on one page (Sammy, 2026-11-11: wires passing through run
        # along the whole page).
        if s.lone_fuses or s.right_males:
            self.cuts.append(x)
        tail = sum(dp.device_gap + item.unit.extents()[2] - item.unit.extents()[0] for item in s.lone_fuses)
        if flows["from"] == "right":
            tail += lane + self._source_width(wires)
        if s.right_males:
            m_left, _, m_right, _ = self.male.extents
            tail += self._target_lanes_width("right", wires) + lane + (m_right - m_left)
            x = max(x, self._room() - tail)
        self.lone_x = x
        for item in s.lone_fuses:
            left, _, right, _ = item.unit.extents()
            x += dp.device_gap + (right - left)
        # Where the 24 V comes in from the right: its source lanes and terminal blocks.
        if flows["from"] == "right":
            x += lane
            self.source_x = x
            x += self._source_width(wires)
        if s.right_males:
            x += self._target_lanes_width("right", wires) + lane
            self._place_males(s.right_males, "right", x)
        self._place_lone_fuses()

    def _room(self) -> float:
        """How wide a page's ladder can be: the page less its margins, less the title block
        when the ladder reaches down to it (its height estimated: every wire its own height)."""
        settings, dp = self.ctx.settings, self.dp
        count = {PLUS: 0, MINUS: 0}
        for sign, *_ in self.wires:
            count[sign] += 1
        height = (self.row_height + 2 * dp.ladder_zone_gap + dp.wire_spacing * (count[PLUS] + count[MINUS])
                  + 2 * dp.wire_spacing)
        if self.s.supply:               # the supply and its fuses may reach lower than the - wires
            plus_top = dp.ladder_zone_gap + dp.wire_spacing * count[PLUS]
            height = max(height, plus_top + self._supply_depth() + 2 * dp.lane_spacing)
        reach_bottom = settings.main_bus.content_top_y - height
        page_right = settings.keepout_left_x if reach_bottom < settings.keepout_height else settings.drawable_width
        return page_right - 2 * settings.margin_standard

    def _height(self, unit):
        left, bottom, right, top = unit.extents()
        return top - bottom

    def _supply_depth(self) -> float:
        """How far below the row's top the supply, its fuses and the ground strip under it
        reach (the supply's top stands supply_rise above the row's top)."""
        left, bottom, right, top = self.s.supply.unit.extents()
        with_ground = (top - self._body_bottom()) + self._ground_depth()
        return max(top - bottom, with_ground) - self.supply_rise

    def _body_bottom(self) -> float:
        """The lowest point of the supply and what stands left of its - lane (its own 3-phase
        fuse, brackets), not its 24 V fuses: in its unit, before it is placed."""
        unit, lane_x = self.s.supply.unit, self.s.supply.minus_lane_x
        ys = [b.position[1] + b.extents[1] for b in unit.blocks if b.position[0] + b.extents[2] < lane_x]
        ys += [min(w.start[1], w.end[1]) for w in unit.wires if max(w.start[0], w.end[0]) < lane_x]
        ys += [p.bottom_y for p in unit.placeholders if p.right_x < lane_x]
        return min(ys) if ys else unit.extents()[1]

    def _under_fuses_y(self) -> float:
        """The height the supply's - runs at under its fuses: a lane below the lowest of them."""
        return self.s.supply.unit.extents()[1] + self.supply_shift[1] - self.dp.lane_spacing

    def _supply_minus_path(self, to_x, y) -> list:
        """The supply's - from its output: across into its lane between the supply and its
        fuses, down to `y` (under the fuses) and across to `to_x`."""
        dx, dy = self.supply_shift
        mx, my = self.s.supply.minus
        lane_x = self.s.supply.minus_lane_x + dx
        return [(mx + dx, my + dy), (lane_x, my + dy), (lane_x, y), (to_x, y)]

    def supply_rise_room(self) -> float:
        """After a build: how far the supply and its fuses can move up (Sammy, 2026-11-20:
        beside the + wires, not under them). As far as no fuse's wire has to turn down (the
        first one then runs straight across), and staying ladder_zone_gap under any + wire
        that passes over them (on its way to the split on the left)."""
        if not getattr(self, "runs", None) and not getattr(self, "entries", None):
            return 0.0
        dx, dy = self.supply_shift
        room = []
        for run in self.runs:                   # a fuse's wire straight to its far end
            if run.sign == PLUS and run.from_terminal is None and run.key in self.s.supply.fuses:
                room.append(run.height - (self.s.supply.fuses[run.key][1] + dy))
        for sign, label, end, key in self.entries:      # a fuse's wire into its terminal group
            if sign == PLUS and key in self.s.supply.fuses:
                room.append(self.groups[key]["entry"][1] - (self.s.supply.fuses[key][1] + dy))
        left, bottom, right, top = self.s.supply.unit.extents()
        span = (left + dx, right + dx)
        for run in self.runs:
            lo, hi = run.interval(run.from_terminal[0]["x"]) if run.from_terminal else run.interval()
            if run.sign == PLUS and lo < span[1] - TOLERANCE and span[0] < hi - TOLERANCE:
                room.append(run.height - self.dp.ladder_zone_gap - (top + dy))
        return max(min(room), 0.0) if room else 0.0

    def wires_under_supply(self) -> bool:
        """After a build: does a - wire pass under the supply and its fuses (on its way to the
        split on the left)?"""
        if not getattr(self, "runs", None):
            return False
        dx, dy = self.supply_shift
        left, bottom, right, top = self.s.supply.unit.extents()
        for run in self.runs:
            lo, hi = run.interval(run.from_terminal[0]["x"]) if run.from_terminal else run.interval()
            if run.sign == MINUS and lo < right + dx - TOLERANCE and left + dx < hi - TOLERANCE:
                return True
        return False

    def _males_height(self, males):
        if not males:
            return 0.0
        m_left, m_bottom, m_right, m_top = self.male.extents
        return len(males) * (m_top - m_bottom) + (len(males) - 1) * self.dp.wire_spacing

    def _male_bases(self, males, shift=0.0) -> list:
        """[(name, pins used, base y)] for the males on one side: stacked, centred on the row,
        then moved up by `shift`."""
        m_left, m_bottom, m_right, m_top = self.male.extents
        top = -self.row_height / 2 + self._males_height(males) / 2 + shift
        found = []
        for name, used in males:
            base_y = top - m_top
            found.append((name, used, base_y))
            top = base_y + m_bottom - self.dp.wire_spacing
        return found

    def _straight_in_shift(self) -> float:
        """How far to move the left males up (down if less than 0) so the first wire that goes
        straight into something in the row (the supply, else the first device that takes
        any) runs level into its pin: phase A, as when a fuse lies beside its meter (Sammy,
        2026-11-20: no step in it). Never so far that the males reach the 24 V wires above or
        below the row (they may stand out of the row into the gap, ladder_zone_gap)."""
        things = ([self.s.supply] if self.s.supply else []) + list(self.s.devices)
        thing = next((t for t in things if self._straight_in_keys(t)), None)
        if thing is None:
            return 0.0
        key = sorted(self._straight_in_keys(thing))[0]
        target_y = thing.fed_by_split[key][1] - thing.unit.extents()[3]      # its top stands at 0 ...
        if thing is self.s.supply:
            target_y += self.supply_rise                                    # ... the supply's higher
        bases = self._male_bases(self.s.left_males)
        pin_y = next(base_y + self.male.markers[self.ss.pin_marker.format(pin=used[key])][1]
                     for _, used, base_y in bases if key in used)
        m_left, m_bottom, m_right, m_top = self.male.extents
        highest, lowest = bases[0][2] + m_top, bases[-1][2] + m_bottom
        gap = self.dp.ladder_zone_gap
        return max(min(target_y - pin_y, gap - highest), -self.row_height - gap - lowest)

    def _place_males(self, males, side, x, shift=0.0) -> float:
        """The males on one side, stacked and centred on the row (then moved up by `shift`).
        Left ones face right (pins on their right side), right ones are flipped (pins on their
        left side)."""
        ss, male = self.ss, self.male
        m_left, m_bottom, m_right, m_top = male.extents
        for name, used, base_y in self._male_bases(males, shift):
            if side == "left":
                position = (x - m_left, base_y)
                extents, flipped = male.extents, False
            else:
                position = (x + m_right, base_y)
                extents, flipped = (-m_right, m_bottom, -m_left, m_top), True
            self.unit.blocks.append(BlockPlacement(block=ss.male_block, layer=ss.layer, position=position,
                                                   attributes={ss.name_attribute: name}, label=name,
                                                   extents=extents, flipped=flipped))
            self.unit.names.append(name)
            for key, n in used.items():
                px, py = male.markers[ss.pin_marker.format(pin=n)]
                point = (position[0] + px, base_y + py) if side == "left" else (position[0] - px, base_y + py)
                self.pins[(side, key)] = point
                self.pin_male[(side, key)] = name
        return x + (m_right - m_left)

    def _place_lone_fuses(self):
        """Each lone fuse with its first phase level with its pin on the right males."""
        x = self.lone_x
        for item in self.s.lone_fuses:
            left, _, right, _ = item.unit.extents()
            key, (px, py) = next(iter(item.phases.items()))
            pin = self.pins.get(("right", key))
            dy = (pin[1] - py) if pin else -self.row_height / 2
            dx = x + self.dp.device_gap - left
            add_unit_to(self.unit, item.unit, dx, dy)
            for key, (px, py) in item.phases.items():
                if ("right", key) in self.pins:
                    end = self.pins[("right", key)]
                    layer, label = self.ctx.other_wires.get(key, ("0", ""))
                    self.unit.wires.append(Wire(layer, (px + dx, py + dy), end, label))
            x = dx + right

    # --- 3. The 24 V wires -----------------------------------------------------------------

    def _section_wires(self) -> list:
        """[(sign, label, start ref, end ref, circuit key)] for this section's 24 V wires."""
        plan = self.ctx.plan
        if plan is None:
            return []
        found = []
        for key in self.keys:
            for edge in plan.edges[(self.number, key)]:
                found.append((self.circuits[key].sign, edge.label, edge.start, edge.end, key))
        return found

    def _source_refs(self, sign):
        """The circuits that come in at this section's source, in the order their wires leave
        it (top fuse / top pin first)."""
        plan, s = self.ctx.plan, self.s
        keys = [key for key in self.keys if self.circuits[key].sign == sign]
        if s.supply:
            order = [key for _, key in plan.fuses] + [MINUS]
            return [k for k in order if k in keys]
        side_boundary = self.number - 1 if self.number > plan.supply_section else self.number
        order = plan.boundary_keys(side_boundary)
        return [k for k in order if k in keys]

    def _has_terminal(self, key):
        return (self.number, key) in self.ctx.plan.terminals

    def _terminal_size(self, key) -> tuple:
        """How a circuit's terminal group is built: (blocks, its exits to the left and right)."""
        lefts, rights = self._exits(key)
        entry = self._entry_marker(key)
        need = {"LEFT": len(lefts), "RIGHT": len(rights)}
        count = 1
        while any(len(self._side_points(count, side, entry)) < n for side, n in need.items()):
            count += 1
        return count, lefts, rights

    def _exits(self, key) -> tuple:
        """A terminal group's wires out, split by the side their far end is on."""
        lefts, rights = [], []
        for sign, label, a, b, k in self.wires:
            if k != key or TERMINAL not in (a, b):
                continue
            far = b if a == TERMINAL else a
            if far == SOURCE or (far[0] == "split" and self._is_source_split(far)):
                continue                                # that's the wire in
            (lefts if self._side_of(far) == "left" else rights).append((label, far))
        return lefts, rights

    def _side_of(self, ref) -> str:
        """Is a wire's far end left or right of where the 24 V comes in?"""
        if ref[0] == "split":
            return "left" if ref[1] == self.number - 1 else "right"
        flows = self._flow_sides()["from"]
        return "left" if flows == "right" else "right"

    def _is_source_split(self, ref) -> bool:
        flows = self._flow_sides()["from"]
        return ((flows == "left" and ref[1] == self.number - 1) or (flows == "right" and ref[1] == self.number))

    def _entry_marker(self, key) -> str:
        """The terminal point a circuit's wire comes in on: + from below (its BOTTOM marker),
        - from above (TOP), on the side away from where its wires go out. The supply's - comes
        in from below when it runs under fuses that reach lower than the group."""
        sign = self.circuits[key].sign
        lefts, rights = self._exits(key)
        from_below = sign == PLUS or (key == MINUS and self.s.supply and self.minus_from_below)
        direction = "BOTTOM" if from_below else "TOP"
        found = [(x, y, name) for name, (x, y) in (self.terminal.markers or {}).items()
                 if name.endswith("_" + direction) and name.split("_")[0].isdigit()]
        # The points on the block's edge the wire comes from (the lowest from below, the
        # highest from above).
        edge = min(y for _, y, _ in found) if from_below else max(y for _, y, _ in found)
        found = [(x, name) for x, y, name in found if abs(y - edge) < TOLERANCE]
        if rights and not lefts:
            return min(found)[1]
        if lefts and not rights:
            return max(found)[1]
        return min(found, key=lambda f: (abs(f[0]), f[0]))[1]

    def _side_points(self, count, side, entry) -> list:
        """[(block index, marker)] a group of `count` blocks offers on `side`, top first. The
        point the wire comes in on is taken (on the bottom block for +, the top one for -)."""
        markers = self.terminal.markers or {}
        entry_point = entry.split("_")[0]
        entry_block = count - 1 if entry.endswith("_BOTTOM") else 0
        found = []
        for index in range(count):
            for name, (_, y) in markers.items():
                point, _, direction = name.partition("_")
                if direction != side or not point.isdigit():
                    continue
                if index == entry_block and point == entry_point:
                    continue
                found.append((-(y - index * self.dp.terminal_pitch), index, name))
        return [(index, name) for _, index, name in sorted(found)]

    def _source_width(self, wires) -> float:
        """How wide the source lanes and terminal groups are: the wider of + and -, which
        share the room (+ at the top, - at the bottom). Beside the power supply the - has a
        slot of its own right of the + (Sammy, 2026-11-20): the fuses' + wires rise from as
        low as the - wires run."""
        plus = sum(self._slot_width(key) for key in self._source_refs(PLUS))
        minus = sum(self._slot_width(key) for key in self._source_refs(MINUS))
        return plus + minus if self.s.supply else max(plus, minus, 0.0)

    def _slot_width(self, key) -> float:
        lane = self.dp.lane_spacing
        if not self._has_terminal(key):
            return lane
        count, lefts, rights = self._terminal_size(key)
        left, _, right, _ = self.terminal.extents
        return (right - left) + lane * (max(len(lefts) - 1, 0) + max(len(rights) - 1, 0)) + 2 * lane

    def _target_lanes_width(self, side, wires) -> float:
        count = sum(1 for _, _, a, b, _ in wires for ref in (a, b)
                    if ref[0] == "split" and self._side_of(ref) == side and not self._is_source_split(ref))
        return (count + 1) * self.dp.lane_spacing

    def _wire_24v(self, flows):
        """Every 24 V wire: lanes, heights, terminal groups, then the wires themselves."""
        if self.ctx.plan is None or not self.wires:
            return
        dp = self.dp
        self.groups = {}            # {circuit key: terminal group}
        self.lanes = {}             # {circuit key: the lane its wire leaves the source in}
        runs = []
        entries = []                # (sign, label, source end, circuit key): wires into a terminal group
        going_left = flows["from"] == "right"
        for sign in (PLUS, MINUS):
            if sign == MINUS and self.s.supply:
                # The supply's - (Sammy, 2026-11-20): it drops between the supply and its
                # fuses, runs under the fuses, and comes to its terminal group (or its lane) in
                # a slot of its own right of the + slots. Into the group from above, or from
                # below when the fuses reach down past the top of the - wires.
                if MINUS in self.keys:
                    start = self.source_x + sum(self._slot_width(k) for k in self._source_refs(PLUS))
                    width = self._slot_width(MINUS)
                    self.minus_from_below = self._under_fuses_y() < (
                        -self.row_height - dp.ladder_zone_gap + dp.lane_spacing)
                    if self._has_terminal(MINUS):
                        self.groups[MINUS] = self._terminal_group(MINUS, start, width)
                    else:
                        self.lanes[MINUS] = start + width
                continue
            # The slots, from the side nearest the source outwards, top source first.
            x = self.source_x + (self._source_width(self.wires) if going_left else 0.0)
            for key in self._source_refs(sign):
                width = self._slot_width(key)
                start = x - width if going_left else x
                if self._has_terminal(key):
                    self.groups[key] = self._terminal_group(key, start, width)
                else:
                    self.lanes[key] = start if going_left else start + width
                x = start if going_left else start + width
        # Each wire: its ends, with the lanes their legs run in.
        target_lanes = {"left": [], "right": []}
        for sign, label, a, b, key in self.wires:
            if TERMINAL in (a, b):
                far = b if a == TERMINAL else a
                if far == SOURCE or (far[0] == "split" and self._is_source_split(far)):
                    entries.append((sign, label, self._source_end(sign, key, far), key))
                    continue
                group = self.groups[key]
                run = _Run(sign, label, None, self._target_end(sign, far, key, target_lanes))
                run.from_terminal = (group, far)
                runs.append(run)
                continue
            source = a if (a == SOURCE or (a[0] == "split" and self._is_source_split(a))) else b
            target = b if source is a else a
            start = self._source_end(sign, key, source)
            if sign == MINUS and source == SOURCE and self.s.supply:
                # The supply's - under its fuses to its lane, then on as any wire.
                lane_x, under = self.lanes[MINUS], self._under_fuses_y()
                self.unit.wires += path_wires(self._supply_minus_path(lane_x, under), self._layer(sign), label)
                start = _End((lane_x, under), lane_x)
            runs.append(_Run(sign, label, start, self._target_end(sign, target, key, target_lanes), key=key))
        self._target_lane_positions(target_lanes)
        # Heights: a wire whose span holds another's runs outside it.
        for sign in (PLUS, MINUS):
            mine = [r for r in runs if r.sign == sign]
            spans = {id(r): (r.interval(r.from_terminal[0]["x"]) if r.from_terminal else r.interval()) for r in mine}
            done = []
            for run in sorted(mine, key=lambda r: spans[id(r)][1] - spans[id(r)][0]):
                lo, hi = spans[id(run)]
                below = [d.level for d in done if spans[id(d)][0] < hi - TOLERANCE and lo < spans[id(d)][1] - TOLERANCE]
                run.level = max(below) + 1 if below else 0
                done.append(run)
            for run in mine:
                if sign == PLUS:
                    run.height = dp.ladder_zone_gap + run.level * dp.wire_spacing
                else:
                    run.height = -self.row_height - dp.ladder_zone_gap - run.level * dp.wire_spacing
        # Terminal groups at the heights of their wires out; then every wire.
        for key, group in self.groups.items():
            self._place_terminal_group(key, group, [r for r in runs if r.from_terminal and r.from_terminal[0] is group])
        for sign, label, end, key in entries:
            group = self.groups[key]
            if sign == MINUS and self.s.supply:
                # The supply's - under its fuses, then down (or up) into its group.
                ex, ey = group["entry"]
                under = self._under_fuses_y()
                if self.minus_from_below:
                    under = min(under, ey - dp.lane_spacing)
                points = self._supply_minus_path(ex, under) + [group["entry"]]
            else:
                points = [end.point, (group["entry"][0], end.point[1]), group["entry"]]
            self.unit.wires += path_wires(points, self._layer(sign), label)
        self.runs, self.entries = runs, entries     # for supply_rise_room / wires_under_supply
        for run in runs:
            self.unit.wires += self._route(run)

    def _layer(self, sign):
        return self.ps.output_wire_layers[sign]

    def _source_end(self, sign, key, ref) -> _End:
        """Where a wire starts at the source: a fuse, the supply's -, or a pin on the incoming split."""
        s = self.s
        if ref == SOURCE:
            dx, dy = self.supply_shift
            if sign == MINUS:
                mx, my = s.supply.minus
                return _End((mx + dx, my + dy), self.lanes.get(MINUS))
            fx, fy = s.supply.fuses[key]
            return _End((fx + dx, fy + dy), self.lanes.get(key))
        return _End(self.pins[(self._side_of(ref), key)], self.lanes.get(key))

    def _target_end(self, sign, ref, key, target_lanes) -> _End:
        """Where a wire ends: a device's pin (its lane on the device's left) or a pin on a
        split it leaves by (its lane beside that split, set later)."""
        lane = self.dp.lane_spacing
        if ref[0] == "load":
            item, dx, dy = self.device_at[ref[1]]
            px, py = item.pins[sign]
            left = item.unit.extents()[0] + dx
            return _End((px + dx, py + dy), left - (lane if sign == PLUS else 2 * lane))
        side = self._side_of(ref)
        end = _End(self.pins[(side, key)], None)
        target_lanes[side].append((sign, end))
        return end

    def _target_lane_positions(self, target_lanes):
        """The lanes beside a split the wires leave by: the - closest to it, then the + with
        the top pin's closest."""
        lane = self.dp.lane_spacing
        for side, ends in target_lanes.items():
            if not ends:
                continue
            ordered = [e for s, e in ends if s == MINUS] + sorted((e for s, e in ends if s == PLUS),
                                                                  key=lambda e: -e.point[1])
            pin_x = ends[0][1].point[0]
            for index, end in enumerate(ordered, start=1):
                end.lane_x = pin_x - index * lane if side == "right" else pin_x + index * lane

    def _terminal_group(self, key, start, width, entry_x=None) -> dict:
        """A circuit's terminal group in its slot (from `start`, `width` wide), or standing
        with the point its wire comes in on at `entry_x`: where its blocks stand across."""
        lane = self.dp.lane_spacing
        count, lefts, rights = self._terminal_size(key)
        left, _, right, _ = self.terminal.extents
        entry = self._entry_marker(key)
        if entry_x is not None:
            x = entry_x - self.terminal.markers[entry][0]
        else:
            x = start + lane + lane * max(len(lefts) - 1, 0) - left
        return {"x": x, "count": count, "entry_marker": entry, "lefts": lefts, "rights": rights,
                "base": None, "entry": None}

    def _place_terminal_group(self, key, group, runs):
        """Stand the group at the heights of its wires out: each wire on the next free side
        point (top first, the highest wire first), every point at or above its wire's height
        (the wires step down to theirs in lanes beside the group)."""
        sign = self.circuits[key].sign
        pitch, markers = self.dp.terminal_pitch, self.terminal.markers
        entry = group["entry_marker"]
        assigned = []
        for side in ("LEFT", "RIGHT"):
            mine = sorted((r for r in runs if (self._side_of(r.from_terminal[1]) == side.lower())),
                          key=lambda r: -r.height)
            for run, (index, marker) in zip(mine, self._side_points(group["count"], side, entry)):
                mx, my = markers[marker]
                assigned.append((run, index, marker, mx, my - index * pitch))
        base = max((run.height - y for run, _, _, _, y in assigned), default=0.0)
        group["base"] = base
        x = group["x"]
        for run, index, marker, mx, y in assigned:
            run.a = _End((x + mx, base + y), None)
        # Lanes for the wires that step down, the higher outermost.
        left, _, right, _ = self.terminal.extents
        for side, edge, step in (("LEFT", x + left, -1), ("RIGHT", x + right, 1)):
            stepping = [a for a in assigned if a[0].a.point[1] - a[0].height > TOLERANCE
                        and self._side_of(a[0].from_terminal[1]) == side.lower()]
            stepping.sort(key=lambda a: -a[0].a.point[1])
            for i, a in enumerate(stepping):
                a[0].a.lane_x = edge + step * self.dp.lane_spacing * (len(stepping) - i)
        ex, ey = markers[entry]
        entry_block = group["count"] - 1 if entry.endswith("_BOTTOM") else 0
        group["entry"] = (x + ex, base + ey - entry_block * pitch)
        self._draw_terminal_group(key, group)

    def _draw_terminal_group(self, key, group):
        cp, pitch = self.cp, self.dp.terminal_pitch
        sign = self.circuits[key].sign
        strip = cp.strip_name.format(section=self.number, sign=sign)
        self._strip_numbers = getattr(self, "_strip_numbers", {PLUS: 0, MINUS: 0})
        x, base, count = group["x"], group["base"], group["count"]
        for index in range(count):
            self._strip_numbers[sign] += 1
            number = self._strip_numbers[sign]
            self.unit.blocks.append(BlockPlacement(
                block=cp.terminal_block, layer=cp.terminal_layer, position=(x, base - index * pitch),
                attributes={cp.terminal_number_attribute: str(number)}, label=f"{strip}({number})",
                extents=self.terminal.extents))
        left, bottom, right, top = self.terminal.extents
        middle = x + (left + right) / 2
        if group["entry_marker"].endswith("_BOTTOM"):   # its wire comes in from below: the name above
            y = base + top + cp.strip_name_gap
        else:                                           # from above: the name below
            y = base - (count - 1) * pitch + bottom - cp.strip_name_gap - cp.strip_name_height
        self.unit.texts.append(PageText(strip, middle, y, cp.strip_name_layer, cp.strip_name_height))
        top_mark, bottom_mark = self.terminal.markers.get(cp.bridge_top_marker), self.terminal.markers.get(cp.bridge_bottom_marker)
        if count > 1 and top_mark and bottom_mark:
            self.unit.polylines.append(WidePolyline(cp.bridge_layer, [
                (x + top_mark[0], base + top_mark[1]),
                (x + bottom_mark[0], base - (count - 1) * pitch + bottom_mark[1])], cp.bridge_width))

    def _route(self, run) -> list:
        """One wire: from its start across to its lane, up or down to its height, along, down
        or up its far lane and across into its pin."""
        a, b = run.a, run.b
        points = [a.point]
        if a.lane_x is not None:
            points += [(a.lane_x, a.point[1]), (a.lane_x, run.height)]
        else:
            points += [(a.point[0], run.height)]
        points += [(b.lane_x, run.height), (b.lane_x, b.point[1]), b.point]
        return path_wires(points, self._layer(run.sign), run.label)

    # --- Ground (Sammy, 2026-11-17; under the supply 2026-11-20) ------------------------------

    def _ground_points(self):
        """The ground strip's terminal points: (the one the supply's ground comes in on, how
        many blocks, [(block index, marker)] for the devices' stubs, top first). The wire in
        on the top block's rightmost TOP point, the bus out on the LEFT side, the devices'
        stubs on the RIGHT side."""
        strip, markers = self.s.ground, self.terminal.markers or {}
        tops = [(y, x, name) for name, (x, y) in markers.items() if name.endswith("_TOP") and name.split("_")[0].isdigit()]
        entry = max(tops)[2] if tops else ""    # on the block's top edge, the right one of those
        count = 1
        while (len(self._side_points(count, "RIGHT", entry)) < len(strip.devices)
               or not self._side_points(count, "LEFT", entry)):
            count += 1
        return entry, count, self._side_points(count, "RIGHT", entry)[:len(strip.devices)]

    def _ground_depth(self) -> float:
        """How far the ground strip reaches below the supply (and what stands left of its -
        lane): the gap, the strip, its stubs and their text (estimated)."""
        strip, gs = self.s.ground, self.ctx.devices.ground
        if strip is None or gs is None or self.s.supply is None or self.terminal is None:
            return 0.0
        dp, markers = self.dp, self.terminal.markers or {}
        t_left, t_bottom, t_right, t_top = self.terminal.extents
        entry, count, rights = self._ground_points()
        strip_low = (count - 1) * dp.terminal_pitch - t_bottom + dp.ladder_zone_gap     # its name under it
        if not rights:
            return dp.ladder_zone_gap + t_top + strip_low
        lowest = min(markers[name][1] - index * dp.terminal_pitch for index, name in rights)
        text = max((tilde_text_box(gs.from_device_label.format(device=device), dp, True, vertical=True)[1]
                    for _, device in strip.devices), key=abs)
        return dp.ladder_zone_gap + t_top + max(strip_low, -lowest + gs.stub_length - text)

    def _ground(self):
        """The ground strip under the power supply, in the room left of its fuses (Sammy,
        2026-11-20; it stood at the bottom, under the fuses, and kept them from reaching lower):

                   [PS ]
              G002 +--+G                   (the supply's ground drops in from above)
                   |
            ]~--[ 1TBG ]--------+          (each other device's ground: out on the right,
           TO GROUND BUS [  ]---+|          down in a lane of its own, the top one outermost,
                                ||          so none cross)
                                ~~          (upright tildes, their text under them reading
                                FF          up: FROM PM-1, FROM PS-2)

        G001 leaves on the left through a tilde to a bracket TO GROUND BUS. The stubs' lanes
        stay a lane short of the lane the supply's - drops in."""
        strip, gs = self.s.ground, self.ctx.devices.ground
        if strip is None or gs is None or self.s.supply is None or self.terminal is None:
            return
        dp, br, cp = self.dp, self.br, self.cp
        markers, pitch, lane = self.terminal.markers or {}, dp.terminal_pitch, dp.lane_spacing
        t_left, t_bottom, t_right, t_top = self.terminal.extents
        dx, dy = self.supply_shift
        ground = self.s.supply.ground
        pin = (ground[0] + dx, ground[1] + dy) if ground else None
        entry, count, rights = self._ground_points()
        # Across: the stubs' lanes right of the strip, the outermost a lane short of the
        # supply's - lane; the supply's ground drops in a lane left of its pin.
        x = self.s.supply.minus_lane_x + dx - lane * (len(rights) + 1) - t_right
        if pin and entry:
            x = min(x, pin[0] - lane - markers[entry][0])
        # Down: ladder_zone_gap under the supply and what stands left of its - lane.
        base = self._body_bottom() + dy - dp.ladder_zone_gap - t_top
        layer = gs.wire_layer
        for index in range(count):
            self.unit.blocks.append(BlockPlacement(
                block=cp.terminal_block, layer=cp.terminal_layer, position=(x, base - index * pitch),
                attributes={cp.terminal_number_attribute: str(index + 1)}, label=f"{strip.name}({index + 1})",
                extents=self.terminal.extents))
        name_y = base - (count - 1) * pitch + t_bottom - cp.strip_name_gap - cp.strip_name_height
        self.unit.texts.append(PageText(strip.name, x + (t_left + t_right) / 2, name_y,
                                        cp.strip_name_layer, cp.strip_name_height))
        top_mark, bottom_mark = markers.get(cp.bridge_top_marker), markers.get(cp.bridge_bottom_marker)
        if count > 1 and top_mark and bottom_mark:
            self.unit.polylines.append(WidePolyline(cp.bridge_layer, [
                (x + top_mark[0], base + top_mark[1]),
                (x + bottom_mark[0], base - (count - 1) * pitch + bottom_mark[1])], cp.bridge_width))
        # The supply's ground: out of its pin to the left, down into the strip.
        if pin and entry:
            ex, ey = markers[entry]
            entry_point = (x + ex, base + ey)
            self.unit.wires += path_wires([pin, (entry_point[0], pin[1]), entry_point], layer, strip.supply_label)
        # To the ground bus: out on the left, a tilde and the bracket.
        index, name = self._side_points(count, "LEFT", entry)[0]
        mx, my = markers[name]
        start = (x + mx, base + my - index * pitch)
        end = (start[0] - dp.stub_length, start[1])
        self.unit.wires.append(Wire(layer, start, end, strip.bus_label))
        self.unit.blocks += wire_breaks([end], self.ctx.settings, self.ctx.catalog, dp.wire_break_state_horizontal,
                                        flip_parameter=dp.wire_break_flip_horizontal)
        self.unit.blocks.append(self._single_bracket(end[0] - br.bracket_gap, end[1], gs.bus_label))
        # Each other device's ground: out on the right to its lane, down to a tilde naming it.
        if not rights:
            return
        lowest = min(base + markers[name][1] - index * pitch for index, name in rights)
        end_y = lowest - gs.stub_length
        for k, ((label, device), (index, name)) in enumerate(zip(strip.devices, rights)):
            mx, my = markers[name]
            start = (x + mx, base + my - index * pitch)
            lane_x = x + t_right + lane * (len(rights) - k)
            self.unit.wires += path_wires([start, (lane_x, start[1]), (lane_x, end_y)], layer, label)
            self.unit.blocks += wire_breaks([(lane_x, end_y)], self.ctx.settings, self.ctx.catalog,
                                            dp.wire_break_state, flip_parameter=dp.wire_break_flip_vertical,
                                            text=gs.from_device_label.format(device=device), spacing=lane)

    def _single_bracket(self, x, y, label) -> BlockPlacement:
        """The bracket as drawn (one wire), facing a wire that arrives from the right, its
        label on the left."""
        br = self.br
        bracket = self.ctx.catalog[br.bracket_block]
        state = br.bracket_state_horizontal_bus
        left, bottom, right, top = (bracket.states[state]["extents"] if bracket.states and state in bracket.states
                                    else bracket.extents)
        return BlockPlacement(block=br.bracket_block, layer=br.layer, position=(x, y),
                              attributes={br.label_attribute_horizontal_bus: label}, label=label,
                              visibility=state, extents=(-right, bottom, -left, top), flipped=True,
                              flip_parameter=br.bracket_flip_horizontal_bus)

    # --- 4. Wires that aren't 24 V -----------------------------------------------------------

    def _straight_in_keys(self, thing) -> list:
        """The wires that come in on the split on the left and go straight into `thing`'s pins
        (a device in the row, or the supply)."""
        return [key for key in thing.fed_by_split
                if any(key in used for _, used in self.s.left_males)]

    def _other_wires(self):
        """A fuse's phases (and later, signals) on the splits (Sammy, 2026-11-17 / 2026-11-19):
        - wired straight into the split by a lone fuse beside it (done with the fuses);
        - wired straight into what they feed when it stands in the row and they come in on its
          left (a meter's voltage, the supply's inputs: no tildes);
        - straight across a section with nothing in its row;
        - otherwise a labelled stub on each pin, ending in a tilde that says where the wire
          goes on. Passing a section with devices: TO the split it leaves by at one end, FROM
          the split it came in by at the other (a wire drawn through would have to cross the
          24 V, which comes in above and below it). In the fuse's own section the stub says
          FROM the fuse; in its device's section, TO the device."""
        stub = self.dp.split_stub_length
        wired = {key for item in self.s.lone_fuses for key in item.phases}
        wired |= self._wire_straight_in()
        keys = {key for (_, key) in self.pins if key not in self.circuits}
        empty_row = not self.s.devices and not self.s.supply
        for key in sorted(keys):
            if key in wired:
                continue
            layer, label = self.ctx.other_wires.get(key, ("0", ""))
            left, right = self.pins.get(("left", key)), self.pins.get(("right", key))
            if left and right and empty_row:
                if abs(left[1] - right[1]) < TOLERANCE:
                    self.unit.wires.append(Wire(layer, left, right, label))
                else:
                    mid = (left[0] + right[0]) / 2
                    self.unit.wires += path_wires([left, (mid, left[1]), (mid, right[1]), right], layer, label)
                continue
            for side, point, out in (("left", left, 1), ("right", right, -1)):
                if point is None:
                    continue
                end = (point[0] + out * stub, point[1])
                self.unit.wires.append(Wire(layer, point, end, label))
                self.unit.blocks += wire_breaks(
                    [end], self.ctx.settings, self.ctx.catalog, self.dp.wire_break_state_horizontal,
                    flip_parameter=self.dp.wire_break_flip_horizontal if out < 0 else "",
                    text=self._stub_text(key, side))

    def _wire_straight_in(self) -> set:
        """The wires that come in on the left split and go straight into the pins of the supply
        or a device: each across from its pin, up or down in a lane of its own left of the
        device's lanes, and across into it. The lanes are shared out so the wires cross each
        other as little as they can (a meter's A goes to its lowest pin, so it crosses B and
        C). Returns the wires drawn."""
        lane = self.dp.lane_spacing
        drawn = set()
        placed = [(self.s.supply, *self.supply_shift)] if self.s.supply else []
        for item, dx, dy in placed + list(self.device_at.values()):
            keys = self._straight_in_keys(item)
            if not keys:
                continue
            device_left = item.unit.extents()[0] + dx
            lanes = [device_left - 2 * lane - lane * n for n in range(1, len(keys) + 1)]

            def routes(order, item=item, dx=dx, dy=dy, lanes=lanes):
                wires = []
                for key, lane_x in zip(order, lanes):
                    px, py = item.fed_by_split[key]
                    layer, label = self.ctx.other_wires.get(key, ("0", ""))
                    wires += lane_route(self.pins[("left", key)], (px + dx, py + dy), lane_x, layer, label)
                return wires
            best = min(permutations(sorted(keys)), key=lambda order: count_crossings(routes(order)))
            self.unit.wires += routes(best)
            drawn |= set(keys)
        return drawn

    def _stub_text(self, key, side) -> str:
        """What the tilde on a split's stub says (Sammy, 2026-11-19: every tilde says where its
        wire goes, and the other end says so too)."""
        dp = self.dp
        from_name, from_section, to_name, to_section = self.ctx.other_ends.get(key, ("", 0, "", 0))
        other = "right" if side == "left" else "left"
        if (other, key) in self.pin_male:           # passing through: to / from the other split
            upstream = "left" if from_section < self.number else "right"
            label = dp.split_stub_to_label if side == upstream else dp.split_stub_from_label
            return label.format(name=self.pin_male[(other, key)])
        if self.number == from_section:
            return dp.split_stub_from_label.format(name=from_name)
        return dp.split_stub_to_label.format(name=to_name)

    # --- 5. Pages -------------------------------------------------------------------------

    def _pages(self) -> list[Unit]:
        """The ladder on as many pages as it needs: it breaks between two devices, every wire
        that carries on ending in one bracket spanning the side (Sammy, 2026-11-17)."""
        unit = self.unit
        if unit.is_empty():
            return []
        settings = self.ctx.settings
        left, bottom, right, top = unit.extents()
        reach_bottom = settings.main_bus.content_top_y - (top - bottom)
        page_right = settings.keepout_left_x if reach_bottom < settings.keepout_height else settings.drawable_width
        room = page_right - 2 * settings.margin_standard
        if top - bottom > settings.main_bus.content_top_y - settings.divider.bottom_y:
            self.ctx.warnings.append(f"Section {self.number}'s 24 V group is taller than a page.")
        if right - left <= room:
            unit.names.append(self._page_name(1))
            return [unit]
        bracket_room = self._bracket_reach()
        pages, start = [], left
        cuts = [c for c in self.cuts if c > left + TOLERANCE]
        while True:
            from_room = bracket_room if pages else 0.0
            if right - start + from_room <= room:
                pages.append((start, right + TOLERANCE))
                break
            fitting = [c for c in cuts if c > start + TOLERANCE and c - start + from_room + bracket_room <= room]
            if not fitting:
                self.ctx.warnings.append(f"Section {self.number}'s 24 V group has a part wider than a page.")
                pages.append((start, right + TOLERANCE))
                break
            pages.append((start, fitting[-1]))
            start = fitting[-1]
        return [self._piece(index, lo, hi, len(pages)) for index, (lo, hi) in enumerate(pages)]

    def _page_name(self, number) -> str:
        return f"24V {self.number}.{number}"

    def _bracket_reach(self) -> float:
        bracket = self.ctx.catalog[self.br.bracket_block]
        state = self.br.bracket_state_horizontal_bus
        left, bottom, right, top = (bracket.states[state]["extents"] if bracket.states and state in bracket.states
                                    else bracket.extents)
        return self.br.bracket_gap + right

    def _piece(self, index, lo, hi, count) -> Unit:
        """One page of the ladder: what stands between `lo` and `hi`, the wires cut there."""
        piece = Unit(self.number, new_page=index > 0)
        source = self.unit
        piece.names.append(self._page_name(index + 1))
        inside = lambda x: lo - TOLERANCE <= x < hi - TOLERANCE

        def middle(b):
            l, _, r, _ = b.extents
            return b.position[0] + (l + r) / 2
        piece.blocks = [b for b in source.blocks if inside(middle(b))]
        piece.placeholders = [p for p in source.placeholders if inside((p.left_x + p.right_x) / 2)]
        piece.texts = [t for t in source.texts if inside(t.x)]
        piece.polylines = [p for p in source.polylines if inside(p.points[0][0])]
        piece.names += [n for n in source.names if n in {b.label for b in piece.blocks}]
        for item, dx, dy in self.device_at.values():
            if inside(item.unit.extents()[0] + dx):
                piece.names += item.unit.names
        cut_low, cut_high = [], []
        for w in source.wires:
            (x1, y1), (x2, y2) = w.start, w.end
            if abs(y1 - y2) < TOLERANCE and min(x1, x2) < hi - TOLERANCE < max(x1, x2) and index < count - 1:
                cut_high.append(y1)
            if abs(y1 - y2) < TOLERANCE and min(x1, x2) < lo + TOLERANCE < max(x1, x2) and index > 0:
                cut_low.append(y1)
            if abs(y1 - y2) < TOLERANCE:
                a, b = max(min(x1, x2), lo), min(max(x1, x2), hi)
                if b - a > TOLERANCE:
                    piece.wires.append(Wire(w.layer, (a, y1), (b, y1), w.label))
            elif inside(x1):
                piece.wires.append(w)
        if cut_high:
            piece.blocks.append(self._break_bracket(hi, cut_high, self.ctx.sheet_of(self._page_name(index + 2)),
                                                    "to", flipped=False))
        if cut_low:
            piece.blocks.append(self._break_bracket(lo, cut_low, self.ctx.sheet_of(self._page_name(index)),
                                                    "from", flipped=True))
        return piece

    def _break_bracket(self, x, ys, sheet, direction, flipped) -> BlockPlacement:
        """One bracket spanning every wire cut at `x`, stretched so its grip is on the outer
        ones (never smaller than as drawn)."""
        br = self.br
        grow = max((max(ys) - min(ys)) / 2 - br.bracket_grip_at_rest, 0.0)
        bracket = self.ctx.catalog[br.bracket_block]
        state = br.bracket_state_horizontal_bus
        left, bottom, right, top = (bracket.states[state]["extents"] if bracket.states and state in bracket.states
                                    else bracket.extents)
        bottom, top = bottom - grow, top + grow
        label = (br.to_label if direction == "to" else br.from_label).format(page=br.page_reference.format(sheet=sheet))
        distances = {br.bracket_stretch_horizontal_bus: br.bracket_stretch_at_rest + grow} \
            if br.bracket_stretch_horizontal_bus and grow > TOLERANCE else {}
        position = (x - br.bracket_gap if flipped else x + br.bracket_gap, (max(ys) + min(ys)) / 2)
        return BlockPlacement(block=br.bracket_block, layer=br.layer, position=position,
                              attributes={br.label_attribute_horizontal_bus: label}, label=label,
                              visibility=state, extents=(-right, bottom, -left, top) if flipped else (left, bottom, right, top),
                              flipped=flipped, flip_parameter=br.bracket_flip_horizontal_bus if flipped else "",
                              distances=distances)
