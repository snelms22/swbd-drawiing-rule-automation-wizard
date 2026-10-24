"""Current transformers (CTs) on the 3-line (decision 2026-10-21).

A CT set is Sammy's block (config "current_transformers", e.g. 3_CTS_3L_R1), placed at
scale 1 on a vertical run of bus, never exploded. The engineer only says what it measures;
the program puts it wherever it fits:
- a main or single breaker: on its riser, between the main bus and the breaker;
- a group-mounted part: at the base of its vertical bus, between the main bus and level 1;
- a tie breaker: on the tie's vertical run, between the bus it enters on and the breaker.
On a vertical run the block's "CT LEFT" states are used: markers CONN_A_L / B_L / C_L sit
on the A, B and C phases. Polarity points toward the source:
    main breaker above the bus       -> source above     main breaker below -> source below
    single breaker, group-mounted    -> source is the main bus
    tie breaker                      -> source is the side the bus enters on
The run is made long enough for the block plus `clearance` at each end (and the breaker
block's own overhang), and the block is centred in it. Where the block reaches further
sideways than what is already there, the section widens to make room.

Numbering (src/model/devices.py): CT set k in section s gets CT numbers s-(3k-2)..s-3k and
shorting kit s-k; LOCATION is the power meter it feeds (PM-s-n).

Pure Python, no AutoCAD. Coordinates are frame-relative.
"""
from dataclasses import dataclass

from src.model.devices import ct_sets_in, meter_name


@dataclass(frozen=True)
class CtRoom:
    """How much room a CT set takes on a vertical run, read from the catalog."""
    run: float               # length of bus the block needs, with clearance at both ends
    left: float              # how far the block reaches left of the A phase
    right: float             # how far it reaches right of the A phase
    breaker_overhang: float  # main / tie breaker blocks reach this far past their terminals
    breaker_pole: float      # main / tie breaker blocks: top terminals to bottom terminals
    feeder_overhang: dict    # {"above": .., "below": ..}: feeder blocks toward the main bus

    def riser_gap(self, settings) -> float:
        """Main bus (nearest phase) to the near terminals of a breaker with CTs."""
        return max(settings.main_breaker.gap_bus_to_breaker, self.run + self.breaker_overhang)

    def group_lead(self, part: str, settings) -> float:
        """Main bus (nearest phase) to level 1's nearest tap, with CTs at the base."""
        return max(settings.group_mounted.gap_to_first_level, self.run + self.feeder_overhang[part])

    def tie_body_gap(self, settings) -> float:
        """Where the bus enters a tie with CTs (B phase) to the tie breaker's near terminals."""
        return settings.main_bus.phase_spacing + self.run + self.breaker_overhang


def ct_room(settings, catalog) -> CtRoom | None:
    """The CT block's room, or None if it isn't catalogued with both vertical states
    (then CTs are not drawn and no room is kept)."""
    cts = settings.current_transformers
    block = catalog.get(cts.block) if catalog else None
    states = (cts.vertical_state_source_above, cts.vertical_state_source_below)
    if block is None or not block.states or any(state not in block.states for state in states):
        return None
    marker = "A" + cts.vertical_marker_suffix
    if any(marker not in block.states[state]["markers"] for state in states):
        return None
    reaches = [_reach(block, state, marker) for state in states]

    overhangs, poles = [0.0], [0.0]
    for name in settings.main_breaker.blocks.values():
        breaker = catalog.get(name)
        if breaker is None or not breaker.top_terminals or not breaker.bottom_terminals:
            continue
        top_y, bottom_y = breaker.top_terminals[0][1], breaker.bottom_terminals[0][1]
        overhangs += [breaker.extents[3] - top_y, bottom_y - breaker.extents[1]]
        poles.append(top_y - bottom_y)

    feeder_overhang = {"above": 0.0, "below": 0.0}
    feeder = catalog.get(settings.feeder.block)
    if feeder is not None and feeder.connections:
        for flipped in (False, True):
            _, bottom, _, top = feeder.oriented_extents(flipped)
            # Above the bus a level's C tap is nearest the bus; below it, the A tap.
            feeder_overhang["above"] = max(feeder_overhang["above"],
                                           feeder.connection("C", flipped)[1] - bottom)
            feeder_overhang["below"] = max(feeder_overhang["below"],
                                           top - feeder.connection("A", flipped)[1])

    return CtRoom(
        run=max(up + down for _, _, up, down in reaches) + 2 * cts.clearance,
        left=max(left for left, _, _, _ in reaches),
        right=max(right for _, right, _, _ in reaches),
        breaker_overhang=max(overhangs),
        breaker_pole=max(poles),
        feeder_overhang=feeder_overhang,
    )


def _reach(block, state, marker):
    """(left, right, up, down): how far the block reaches from its A marker in `state`."""
    marker_x, marker_y = block.state_marker(state, marker)
    left, bottom, right, top = block.state_extents(state)
    return marker_x - left, right - marker_x, top - marker_y, marker_y - bottom


def place_on_vertical_run(settings, catalog, source_above: bool, a_x: float,
                          low_y: float, high_y: float):
    """Where the CT block goes on a vertical run whose A phase is at x `a_x`, centred
    between `low_y` and `high_y` (the things above and below it, e.g. the main bus and the
    breaker). Returns (visibility state, base point, extents)."""
    cts = settings.current_transformers
    block = catalog[cts.block]
    state = cts.vertical_state_source_above if source_above else cts.vertical_state_source_below
    marker_x, marker_y = block.state_marker(state, "A" + cts.vertical_marker_suffix)
    left, bottom, right, top = block.state_extents(state)
    # Centre the block's height in the run: its middle sits at the run's middle.
    block_middle = (top + bottom) / 2 - marker_y            # from the A marker
    a_y = (low_y + high_y) / 2 - block_middle
    return state, (a_x - marker_x, a_y - marker_y), (left, bottom, right, top)


def tie_step_height(tie, settings, room: CtRoom | None) -> float:
    """How far a tie moves the bus: `tie_step_height`, or more when the tie has CTs (room
    for them between where the bus enters and the breaker; the other side stays as usual)."""
    step = settings.main_bus.tie_step_height
    if tie is None or tie.cts is None or room is None:
        return step
    usual_exit_gap = (step - room.breaker_pole) / 2
    return max(step, room.tie_body_gap(settings) + room.breaker_pole + usual_exit_gap)


def tie_column_width(tie, settings, room: CtRoom | None) -> float:
    """Width kept for a tie at the section's right edge."""
    width = settings.placeholder_sizes.tie_breaker_width
    if tie.cts is not None and room is not None:
        width = max(width, room.left + room.right)
    return width


def tie_b_inset(tie, settings, room: CtRoom | None) -> float:
    """From the section's right edge (components) back to the tie's B phase."""
    if tie is not None and tie.cts is not None and room is not None:
        # The CT block reaches `right` past the A phase, which is half a spacing left of B.
        return max(settings.placeholder_sizes.tie_breaker_width / 2,
                   room.right - settings.main_bus.phase_spacing)
    return settings.placeholder_sizes.tie_breaker_width / 2


def ct_attributes(settings, ct_set, meter: str, cts) -> dict[str, str]:
    """The CT block's attribute values: what the engineer entered, then what the program
    fills in (CT numbers, shorting kit number, the meter, the ratio). `ct_set` is the
    set's CtSetInfo (its numbers hold its section, decision 2026-10-23)."""
    config = settings.current_transformers
    values = dict(cts.attributes)
    for tag, ct_number in zip(config.ct_number_attributes, ct_set.ct_numbers):
        values[tag] = ct_number
    values[config.shorting_kit_attribute] = ct_set.code
    if meter:
        values[config.meter_attribute] = meter
    if cts.ratio:
        values[config.ratio_attribute] = cts.ratio
    return values


def lineup_ct_attributes(switchboard, settings) -> list[dict[str, dict]]:
    """For each section: {"above" / "below" / "tie": the CT block's attribute values}."""
    per_section = [{} for _ in switchboard.sections]
    for ct_set in ct_sets_in(switchboard):
        meter = meter_name(switchboard, ct_set.cts.meter_id)
        per_section[ct_set.section_number - 1][ct_set.part] = ct_attributes(
            settings, ct_set, meter, ct_set.cts)
    return per_section


def program_filled_tags(settings) -> set[str]:
    """CT block attributes the program fills in (the editor doesn't offer them). The sheet
    is the meter's device page (filled when the device pages are laid out)."""
    config = settings.current_transformers
    return {*config.ct_number_attributes, config.shorting_kit_attribute, config.meter_attribute,
            config.ratio_attribute, config.sheet_attribute}
