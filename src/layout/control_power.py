"""24 V control power (Sammy, 2026-11-13; plan approved 2026-11-16): what takes 24 V, its
fuses, and each 24 V circuit's wires, section by section. Pure Python, no geometry:
device_pages.py draws what this plans.

    Loads      every 3WA's trip unit (all on one shared fuse: trip units share a fuse,
               decision 2026-11-10), the Ethernet switch, each COM800 and each power meter
               whose block has 24 V pins (a fuse each). Boxes until their blocks exist, with
               + and - on their left edge. The COM190 and COM060 modules take no 24 V wire
               (Siemens' cables power them).
    Fuses      FD-1, FD-2 ..., all beside the power supply in its section, one per circuit,
               FD-1 at the top. The column is in the order the wires leave it (the 24 V
               ladder, Sammy 2026-11-17): first those going out through the left split, then
               through the right split (in the split's pin order), then those for the
               section's own devices, the device furthest right first. So no two cross.
    Order      On each shipping split the + wires whose next stop is farthest come first (top
               pin), the - always last; see _boundary_key. In a section, devices stand in a
               row in `row_order` (meters, Ethernet switch, COM800s, trip units), lineup
               order within a kind.
    Circuits   a fuse's + and everything it feeds ("+FD-1"), and the shared - ("-"), which
               starts at the supply's - output. A circuit reaches every section from the
               supply's to its farthest load, crossing each boundary on one shipping split pin.
    Terminals  in a section, a circuit is split on a terminal block when it connects to
               three or more points there: what it comes in on (the fuse, the supply's -, or
               a split), its loads there, and the splits it goes on through. With two points
               it is a single wire.
    Numbers    every wire its own number (2+001 ... / 2-001 ...), counted through the job.
               A wire keeps its number through the shipping splits it passes: the wire on
               each side and the cable between them are one wire.

A circuit's wires are Edges, each between two of its points in one section:
    ("source",)      the fuse's load side (+) or the supply's - output (-)
    ("terminal",)    the circuit's terminal block in this section
    ("load", name)   the load's + (or -, for the - circuit)
    ("split", b)     its shipping split pin at boundary b, between sections b and b+1
"""
from dataclasses import dataclass, field

from src.model.devices import com800s_in, ethernet_switch_sections, mms_in

PLUS, MINUS = "+", "-"
SOURCE = ("source",)
TERMINAL = ("terminal",)

TRIP_UNIT, ETHERNET_SWITCH, COM800, POWER_METER = "trip unit", "Ethernet switch", "COM800", "power meter"
# Loads of these kinds share one fuse; every other load gets its own (decision 2026-11-10:
# trip units and the availability lights share; the lights come with the 120 V work).
SHARED_FUSE_KINDS = (TRIP_UNIT,)
# The devices' order in each section's row, left to right (Sammy, 2026-11-17); config can
# give its own (device_pages.row_order).
ROW_ORDER = (POWER_METER, ETHERNET_SWITCH, COM800, TRIP_UNIT)


@dataclass
class Load:
    """A device that takes 24 V."""
    name: str               # unique, e.g. "TU-1", "ES-1", "COM800-1" (the key in the sheet list)
    kind: str               # TRIP_UNIT, ETHERNET_SWITCH or COM800
    text: str               # its box's text, e.g. "52-M1 TRIP UNIT"
    section_number: int
    width: float            # its box
    height: float
    circuit: str = ""       # its + circuit, e.g. "+FD-1" ("" = not fed)
    # A load drawn with its own block and what is wired to it (a power meter with its fuse,
    # CT inputs and remote display, decision 2026-11-12 option A), placed whole in the 24 V
    # group: that drawing (device_pages' Unit) and its 24 V pins in it, {"+": (x, y), "-": ...}.
    unit: object = None
    pins: dict = None


@dataclass
class Circuit:
    key: str                # "+FD-1", or "-" for the shared -
    sign: str               # PLUS or MINUS
    fuse: str               # "FD-1"; "" for the -
    loads: list = field(default_factory=list)


@dataclass
class Edge:
    """One wire of a circuit in one section, between two of its points."""
    start: tuple
    end: tuple
    label: str = ""


@dataclass
class ControlPowerPlan:
    supply_section: int
    loads: list                                     # [Load]
    fuses: list = field(default_factory=list)       # [(fuse name, circuit key)], top of the column first
    circuits: list = field(default_factory=list)    # [Circuit]: the fuses' in the same order, then the -
    edges: dict = field(default_factory=dict)       # {(section, circuit key): [Edge]}
    terminals: set = field(default_factory=set)     # {(section, circuit key)}: split on a terminal block
    split_labels: dict = field(default_factory=dict)  # {(boundary, circuit key): the wire's number}
    supply_label: str = ""                          # the supply's + to the first fuse
    rank: dict = field(default_factory=dict)        # {load name: its place in the rows, left to right}

    def crossings(self) -> list[tuple[int, int, list[str]]]:
        """[(first section, last section, [circuit key])]: each circuit crosses every boundary
        between its first and last section, in this order (the fuses' circuits, then the -)."""
        found = []
        for circuit in self.circuits:
            first, last = span(circuit, self.supply_section)
            if first < last:
                found.append((first, last, [circuit.key]))
        return found

    def boundary_keys(self, boundary) -> list[str]:
        """The 24 V wires crossing `boundary` (between sections b and b+1), top pin first: the
        + wires by _boundary_key, the - last."""
        crossing = [c for c in self.circuits
                    if span(c, self.supply_section)[0] <= boundary < span(c, self.supply_section)[1]]
        plus = sorted((c for c in crossing if c.sign == PLUS),
                      key=lambda c: _boundary_key(c, boundary, self.supply_section, self.rank))
        return [c.key for c in plus] + [c.key for c in crossing if c.sign == MINUS]


def control_power_loads(switchboard, control_power, page_settings) -> list[Load]:
    """Everything that takes 24 V: trip units, then the Ethernet switch, then the COM800s."""
    cp, dp = control_power, page_settings
    loads = []
    for info in mms_in(switchboard):                # every 3WA (decision 2026-11-09)
        text = cp.trip_unit_text.format(breaker=info.breaker.label or "BREAKER")
        # Its comms module (the COM190) is part of the trip unit's block (Sammy, 2026-11-17):
        # named on a second line in its box.
        module = getattr(info.breaker, "comms_module", "")
        if module:
            text += "\n" + module
        loads.append(Load(f"TU-{info.number}", TRIP_UNIT, text,
                          info.section_number, dp.trip_unit_width, dp.trip_unit_height))
    # One switch per lineup for now (Sammy, 2026-11-19): the first section ticked for it.
    for number, section in enumerate(ethernet_switch_sections(switchboard)[:1], start=1):
        loads.append(Load(f"ES-{number}", ETHERNET_SWITCH, dp.ethernet_switch_text, section,
                          dp.ethernet_switch_width, dp.ethernet_switch_height))
    for info in com800s_in(switchboard):
        loads.append(Load(f"COM800-{info.number}", COM800, cp.com800_text.format(number=info.number),
                          info.section_number, dp.com800_width, dp.com800_height))
    return loads


def span(circuit, supply_section) -> tuple[int, int]:
    """The first and last section a circuit reaches: the supply's and its loads'."""
    sections = [load.section_number for load in circuit.loads] + [supply_section]
    return min(sections), max(sections)


def row_ranks(loads, row_order=ROW_ORDER) -> dict:
    """{load name: its place in its section's row, left to right}: by `row_order`, lineup
    order within a kind. (Only compared between loads of one section.)"""
    order = {kind: index for index, kind in enumerate(row_order)}
    ranked = sorted(range(len(loads)), key=lambda i: (order.get(loads[i].kind, len(order)), i))
    return {loads[i].name: place for place, i in enumerate(ranked)}


def plan_control_power(loads, control_power, supply_section, label, row_order=ROW_ORDER) -> ControlPowerPlan:
    """The fuses, circuits and wires for `loads`, fed by the power supply in `supply_section`.
    `label(sign, number)` writes a wire's number, e.g. label("+", 3) -> "2+003"."""
    plan = ControlPowerPlan(supply_section, loads, rank=row_ranks(loads, row_order))
    if not loads:
        return plan
    # Which loads share a fuse: the trip units; every other load has its own.
    fed_together = [[load for load in loads if load.kind == kind] for kind in SHARED_FUSE_KINDS]
    fed_together = [group for group in fed_together if group]
    fed_together += [[load] for load in loads if load.kind not in SHARED_FUSE_KINDS]
    circuits = [Circuit("", PLUS, "", group) for group in fed_together]
    # The fuse column top down, named FD-1, FD-2 ... in that order.
    circuits.sort(key=lambda c: _fuse_key(c, supply_section, plan.rank))
    for circuit in circuits:
        name = control_power.fuse_name.format(number=len(plan.fuses) + 1)
        circuit.key, circuit.fuse = f"{PLUS}{name}", name
        for load in circuit.loads:
            load.circuit = circuit.key
        plan.circuits.append(circuit)
        plan.fuses.append((name, circuit.key))
    plan.circuits.append(Circuit(MINUS, MINUS, "", list(loads)))

    numbers = {PLUS: 0, MINUS: 0}

    def next_label(sign):
        numbers[sign] += 1
        return label(sign, numbers[sign])

    plan.supply_label = next_label(PLUS)            # the supply's + to the fuses
    for circuit in plan.circuits:
        first, last = span(circuit, supply_section)
        through = {}                                # {("split", b): label}: a wire passing a split
        for section in range(first, last + 1):
            edges, split_here = _section_edges(circuit, section, supply_section, first, last)
            if split_here:
                plan.terminals.add((section, circuit.key))
            for edge in edges:
                splits = [p for p in (edge.start, edge.end) if p[0] == "split"]
                # The wire carries on from the section before it through a split (sections are
                # walked left to right), or it is a new wire.
                edge.label = next((through[p] for p in splits if p in through), "") or next_label(circuit.sign)
                for p in splits:
                    through[p] = edge.label
                    plan.split_labels[(p[1], circuit.key)] = edge.label
            plan.edges[(section, circuit.key)] = edges
    return plan


def _boundary_key(circuit, boundary, supply_section, rank) -> tuple:
    """Sort key for a + wire on the shipping split at `boundary` (between sections b and
    b+1), smallest first = top pin (Sammy, 2026-11-17). Looking the way the wire flows (right
    of the supply: rightwards):
      1. the wire whose next stop (the next section where it feeds a device) is farthest;
      2. then one that goes on past its next stop before one that ends there;
      3. then the one going farther (if it goes on), or feeding the device farthest along the
         row there (if it ends there).
    So in the next section the wires that only pass through run highest, wires that branch
    there come next, and wires that end there come last, and none crosses another."""
    sections = [load.section_number for load in circuit.loads]
    if boundary >= supply_section:                  # flowing right, into section b+1
        ahead = [s for s in sections if s > boundary]
        next_stop = min(ahead)
        goes_on = max(ahead) > next_stop
        there = [rank.get(load.name, 0) for load in circuit.loads if load.section_number == next_stop]
        return (-next_stop, 0 if goes_on else 1, -max(ahead) if goes_on else -max(there))
    ahead = [s for s in sections if s <= boundary]  # flowing left, into section b
    next_stop = max(ahead)
    goes_on = min(ahead) < next_stop
    there = [rank.get(load.name, 0) for load in circuit.loads if load.section_number == next_stop]
    return (next_stop, 0 if goes_on else 1, min(ahead) if goes_on else min(there))


def _fuse_key(circuit, supply_section, rank) -> tuple:
    """Sort key for a + circuit's fuse in the column, smallest first = top (Sammy,
    2026-11-17): the wires leaving through the left split, then any going both ways (the
    trip units' when the supply is in the middle), then those leaving through the right
    split, then those staying in the section, the device furthest right first. The fuse
    column's order is the order the wires run along the top, so none crosses another; the
    left-going ones are the reverse of their split's pin order (the lowest fuse runs
    highest and goes farthest left)."""
    sections = [load.section_number for load in circuit.loads]
    goes_left, goes_right = min(sections) < supply_section, max(sections) > supply_section
    if goes_left and goes_right:
        return (1,)
    if goes_left:
        return (0, *(-k for k in _boundary_key(circuit, supply_section - 1, supply_section, rank)))
    if goes_right:
        return (2, *_boundary_key(circuit, supply_section, supply_section, rank))
    return (3, -max(rank.get(load.name, 0) for load in circuit.loads))


def _section_edges(circuit, section, supply_section, first, last):
    """A circuit's wires in one section, and whether it is split on a terminal block there."""
    if section == supply_section:
        entry = SOURCE
    elif section > supply_section:
        entry = ("split", section - 1)              # it comes in from the left
    else:
        entry = ("split", section)                  # from the right
    exits = [("load", load.name) for load in circuit.loads if load.section_number == section]
    if section <= supply_section and first < section:
        exits.append(("split", section - 1))        # on to the sections on the left
    if section >= supply_section and last > section:
        exits.append(("split", section))            # on to the right
    if len(exits) >= 2:
        return [Edge(entry, TERMINAL)] + [Edge(TERMINAL, point) for point in exits], True
    return ([Edge(entry, exits[0])] if exits else []), False
