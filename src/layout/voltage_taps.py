"""Voltage taps on the 3-line (decision 2026-10-22).

A voltage tap is Sammy's block (config "voltage_taps", e.g. 3P_Voltage_Tap), placed at
scale 1, never exploded. On a vertical run the block's FROM_LEFT state is used: its markers
LA / LB / LC sit on the A, B and C phases and the wires leave to the right, ending in
"TO FA-n SHEET #". A tap on a main breaker is on one of its two sides:
- LINE side (on its feed): the straight run between the breaker's line-side terminals and
  the termination. The run (`gap_breaker_to_input`) becomes a minimum: it grows so each tap
  gets `clearance` from the breaker (and its text), from the next tap, and from the
  termination.
- LOAD side (decision 2026-10-23): the riser between the breaker and the main bus. Nearest
  the breaker come the taps, then the CTs (if any), then the main bus; the riser grows to
  fit them (`bus_side_gap`).
Taps stack outward from the breaker in the order they were entered.

Numbering (src/model/devices.py): fuses FA-n through the lineup (the fuse lives in the tap's section).

Pure Python, no AutoCAD. Coordinates are frame-relative.
"""
from dataclasses import dataclass

from src.model.devices import voltage_taps_in


@dataclass(frozen=True)
class TapRoom:
    """How much room a tap block takes on a vertical run, read from the catalog."""
    up: float                # how far it reaches above its A marker
    down: float              # ... below it
    left: float              # ... left of it
    right: float             # ... right of it (the wires and "TO FA-n")
    breaker_overhang: float  # main breaker blocks reach this far past their terminals

    @property
    def height(self) -> float:
        return self.up + self.down

    def line_side_run(self, settings, tap_count: int, overhang=None) -> float:
        """Breaker's line-side terminals to the termination, with `tap_count` taps.
        `overhang`: what the run starts from reaches this far along it (default: a breaker
        block's overhang; 0 for a bare bus)."""
        usual = settings.main_breaker.gap_breaker_to_input
        if tap_count == 0:
            return usual
        clearance = settings.voltage_taps.clearance
        start = self.breaker_overhang if overhang is None else overhang
        needed = start + tap_count * (clearance + self.height) + clearance
        return max(usual, needed)


def load_side_reach(settings, taps: TapRoom, tap_count: int) -> float:
    """From a breaker's near (bus-side) terminals to the far edge of its last load-side tap."""
    return taps.breaker_overhang + tap_count * (settings.voltage_taps.clearance + taps.height)


def bus_side_gap(settings, taps: TapRoom | None, tap_count: int, cts=None) -> float:
    """Main bus (nearest phase) to a breaker's near terminals, with `tap_count` load-side
    taps (`taps` = their TapRoom) and CTs (`cts` = their CtRoom, or None) between. At least
    `gap_bus_to_breaker`."""
    gap = cts.riser_gap(settings) if cts is not None else settings.main_breaker.gap_bus_to_breaker
    if taps is None or tap_count == 0:
        return gap
    # After the last tap: the CTs' run (which has its own clearance at both ends), or
    # one clearance to the main bus.
    after = cts.run if cts is not None else settings.voltage_taps.clearance
    return max(gap, load_side_reach(settings, taps, tap_count) + after)


def tap_room(settings, catalog) -> TapRoom | None:
    """The tap block's room, or None if it isn't catalogued with its vertical state and
    markers (then taps are not drawn and no room is kept)."""
    config = settings.voltage_taps
    block = catalog.get(config.block) if catalog else None
    if block is None or not block.states or config.vertical_state not in block.states:
        return None
    markers = block.states[config.vertical_state]["markers"]
    if any(name not in markers for name in config.vertical_markers):
        return None
    a_x, a_y = markers[config.vertical_markers[0]]
    left, bottom, right, top = block.states[config.vertical_state]["extents"]
    overhangs = [0.0]
    for name in settings.main_breaker.blocks.values():
        breaker = catalog.get(name)
        if breaker is None or not breaker.top_terminals or not breaker.bottom_terminals:
            continue
        overhangs += [breaker.extents[3] - breaker.top_terminals[0][1],
                      breaker.bottom_terminals[0][1] - breaker.extents[1]]
    return TapRoom(up=top - a_y, down=a_y - bottom, left=a_x - left, right=right - a_x,
                   breaker_overhang=max(overhangs))


def place_taps(settings, catalog, room: TapRoom, a_x: float, line_side_y: float,
               direction: int, count: int, overhang=None):
    """Where `count` taps go on a vertical run whose A phase is at x `a_x`, starting at the
    breaker's line-side terminals (`line_side_y`) and going `direction` (+1 up, -1 down).
    `overhang` as in TapRoom.line_side_run. Returns [(base point, extents)] in order,
    nearest the start first."""
    config = settings.voltage_taps
    block = catalog[config.block]
    marker_x, marker_y = block.states[config.vertical_state]["markers"][config.vertical_markers[0]]
    extents = tuple(block.states[config.vertical_state]["extents"])
    start = room.breaker_overhang if overhang is None else overhang
    edge = line_side_y + direction * start                      # past the breaker and its text
    placements = []
    for _ in range(count):
        edge += direction * config.clearance
        # The tap's near edge sits on `edge`; its A marker is its reach beyond that.
        a_y = edge + room.down if direction > 0 else edge - room.up
        placements.append(((a_x - marker_x, a_y - marker_y), extents))
        edge += direction * room.height
    return placements


def tap_attributes(settings, code: str) -> dict[str, str]:
    """The tap block's attribute values: its fuse number after "FA-" ("n"). The sheet
    keeps its default until the device pages exist."""
    return {settings.voltage_taps.fuse_number_attribute: code}


def lineup_tap_attributes(switchboard, settings) -> list[dict[str, list]]:
    """For each section: {"above" / "below": [attribute values per tap]}: the feed's taps,
    then a main's load-side taps (the order of voltage_taps_in)."""
    per_section = [{} for _ in switchboard.sections]
    for tap in voltage_taps_in(switchboard):
        per_section[tap.section_number - 1].setdefault(tap.part, []).append(
            tap_attributes(settings, tap.code))
    return per_section
