"""Main breaker geometry: how the bus comes in, through the breaker, and onto the main bus.
(docs/DECISIONS.md, 2026-10-11 "Input / output bus connection".)

Above the main bus (fed from the TOP), power flows down:
    input (top) -> bus down into the breaker -> breaker -> bus down -> main bus
Below the main bus (fed from the BOTTOM), power flows up: the same, upside down.

Where the bus meets the main bus:
- Where the main bus begins (the first section that uses it) or ends (the last one), the
  riser BENDS into it (a corner, no junction dots), like the references.
- Anywhere else the main bus is already running, so each phase TEES into its own bus line
  with a junction dot.

The breaker is the library block, placed at scale 1 by its base point, so that its
terminals (from catalog/blocks.json) line up with the bus. The input block (Sammy's
input/output block) is placed so its CONN_A marker sits on the end of the A-phase bus; it
is flipped when the termination is fed from the top ("from the top"). If the input block
isn't in the catalog, a placeholder box is drawn instead.

Feed directions (decision 2026-10-13; see section_contents.py): when the termination is
fed from the other side than the breaker, the bus U-turns between them, as in NTT-013630
section 1:

    breaker (bottom-fed, below the bus)
      | | |                       ^ ^ ^   termination block (fed from the top)
      | | |                       | | |
      | | +-----------------------+ | |   A drops u_turn_depth, B and C 5 and 10 more,
      | +---------------------------+ |   then each runs u_turn_width to the right and
      +-------------------------------+   comes back to the breaker's far-terminal height.

The corners are staggered, so A crosses B and C without connecting (no dots), keeping
A on the left of both legs.

A breaker fed on the bus side (e.g. bottom-fed above the bus; approved 2026-10-13): the
bus comes up beside it on the right and U-turns over it into its top; the cables leave
its bottom, either straight down to a termination block between it and the main bus
(termination fed from the bottom) or in a U-turn to the LEFT and back up past it
(termination fed from the top). This case also gets a warning, to check it can be built.

Pure Python, no AutoCAD. Coordinates are frame-relative.
"""
from dataclasses import dataclass, field

from src.layout.main_bus import step_zone_width
from src.model.section_contents import FIXED, TOP, feed_directions, side_away_from_bus

Point = tuple[float, float]


@dataclass
class BusLine:
    """One phase's straight run of bus (not part of the main bus path)."""
    phase: str
    start: Point
    end: Point


@dataclass
class BlockPlacement:
    block: str
    layer: str
    position: Point                       # where the block's base point goes
    attributes: dict[str, str] = field(default_factory=dict)
    visibility: str = ""                  # dynamic block "Visibility1" state, "" = leave as is
    label: str = ""                       # for the preview only
    extents: tuple = (0.0, 0.0, 0.0, 0.0) # block's size around its base point (preview only)
    flipped: bool = False                 # set the block's flip parameters
    # When flipped: the one flip setting to turn on. Empty = every flip/mirror setting.
    flip_parameter: str = ""


@dataclass
class Placeholder:
    """A box kept for something whose block isn't ready yet."""
    text: str
    left_x: float
    bottom_y: float
    right_x: float
    top_y: float


@dataclass
class Note:
    """Plain text on the drawing (e.g. a provision's note), one entry per line."""
    lines: list[str]
    x: float              # the side the text starts from (see `align`)
    middle_y: float       # vertical middle of the text
    align: str            # "middle_left" (text runs right from x) or "middle_right"


@dataclass
class MainBreakerGeometry:
    # When the main bus starts here: B-phase points from the breaker to the main bus,
    # ending at the main bus height. The page's bus path continues from the last point.
    bus_start_path: list[Point] | None = None
    # When the main bus ends here: B-phase points from the main bus down/up to the breaker.
    bus_end_path: list[Point] | None = None
    bus_lines: list[BusLine] = field(default_factory=list)
    blocks: list[BlockPlacement] = field(default_factory=list)
    placeholders: list[Placeholder] = field(default_factory=list)
    notes: list[Note] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def main_breaker_geometry(main_breaker, part, placed, settings, catalog, starts_the_bus,
                          ends_the_bus=False) -> MainBreakerGeometry:
    """A main breaker: its mounting's block, fed through the input block (INPUT state)."""
    return riser_breaker_geometry(
        main_breaker.breaker, settings.main_breaker.blocks[main_breaker.mounting],
        settings.input_output.input_state, main_breaker.input_attributes,
        feed_directions(main_breaker, part),
        part, placed, settings, catalog, starts_the_bus, ends_the_bus)


def single_breaker_geometry(single, part, placed, settings, catalog, starts_the_bus,
                            ends_the_bus=False) -> MainBreakerGeometry:
    """A single-breaker feeder: the fixed-mount breaker block on a riser off the main bus,
    feeding out through the output block (OUTPUT state)."""
    return riser_breaker_geometry(
        single.breaker, settings.main_breaker.blocks[FIXED],
        settings.input_output.output_state, single.output_attributes,
        feed_directions(single, part),
        part, placed, settings, catalog, starts_the_bus, ends_the_bus)


def riser_breaker_geometry(breaker, block_name, io_state, io_attributes, feeds, part, placed,
                           settings, catalog, starts_the_bus, ends_the_bus) -> MainBreakerGeometry:
    """A breaker standing on its own riser off the main bus, with the input/output block
    at its cable end, in the `part` ("above" or "below") of a placed section. `feeds` is
    (breaker feed, termination feed), each "top" or "bottom".

    The breaker's BUS end connects to the main bus and its CABLE end to the input/output
    block. Usually the cable end faces away from the bus (a top-fed breaker above it).
    When the breaker is fed on the bus side, the ends swap: the bus reaches the far end
    with a U-turn over (or under) the breaker, coming back beside it on the right, and
    the breaker moves away from the bus to make room for the cable side."""
    geometry = MainBreakerGeometry()
    breaker_feed, termination_feed = feeds
    mb = settings.main_breaker
    block = catalog[block_name]
    half = settings.main_bus.phase_spacing
    plan = placed.section.bus
    bus_y = {"A": plan.body_y + half, "B": plan.body_y, "C": plan.body_y - half}

    fed_on_bus_side = breaker_feed != side_away_from_bus(part)
    if fed_on_bus_side:
        geometry.warnings.append(
            f"Section {placed.number}: the {breaker_feed}-fed breaker {part} the main bus "
            f"takes its cables on the bus side; check that this can be built.")
    # The cables U-turn when they must come back the other way to reach the termination.
    cables_turn = termination_feed != breaker_feed

    # `direction` is away from the bus: +1 = up (above the bus), -1 = down.
    if part == "above":
        direction = +1
        near_terminals, far_terminals = block.bottom_terminals, block.top_terminals
        bus_near_y = bus_y["A"]
    else:
        direction = -1
        near_terminals, far_terminals = block.top_terminals, block.bottom_terminals
        bus_near_y = bus_y["C"]

    # Distance from the bus to the breaker: the usual gap, plus room for the cable side
    # when it lies between the breaker and the bus.
    clearance = mb.gap_bus_to_breaker
    if fed_on_bus_side and not cables_turn:
        clearance += mb.gap_breaker_to_input + mb.input_box_height   # termination block
    elif fed_on_bus_side:
        clearance += mb.u_turn_depth + 2 * half                     # the cables' U-turn
    near_y = bus_near_y + direction * clearance
    base_y = near_y - near_terminals[0][1]
    # The block's left edge sits on the section's content edge (after any bus step zone),
    # or a U-turn's width further right when the cables U-turn to the left.
    cables_turn_left = fed_on_bus_side and cables_turn
    base_x = content_left_x(placed, settings) - block.extents[0] + (mb.u_turn_width if cables_turn_left else 0)

    near = [(base_x + x, base_y + y) for x, y in near_terminals]
    far = [(base_x + x, base_y + y) for x, y in far_terminals]
    cable_end = near if fed_on_bus_side else far

    geometry.blocks.append(BlockPlacement(
        block=block_name, layer=mb.block_layer, position=(base_x, base_y),
        attributes=_filled({**breaker.attributes, mb.label_attribute: breaker.label}),
        visibility=mb.visibility,
        label=breaker.label, extents=block.extents,
    ))

    # Cable side: from the breaker's cable end to where the input/output block sits.
    if not cables_turn:
        # Straight on, the way the cables leave the breaker.
        leaving = -direction if fed_on_bus_side else direction
        input_x = cable_end[0][0]
        input_y = cable_end[0][1] + leaving * mb.gap_breaker_to_input
        for phase, (x, y) in zip("ABC", cable_end):
            geometry.bus_lines.append(BusLine(phase, (input_x + x - cable_end[0][0], input_y), (x, y)))
    elif fed_on_bus_side:
        # Toward the bus, across to the LEFT (the bus's own U-turn is on the right), and
        # back past the breaker to the termination.
        input_x = near[0][0] - mb.u_turn_width
        input_y = far[0][1] + direction * mb.gap_breaker_to_input
        geometry.bus_lines += _u_turn(near, -direction, -mb.u_turn_width, input_y, settings)
    else:
        # On away from the bus, across to the right, and back toward it only
        # `u_turn_termination_rise`, where the termination block sits. The turn is just far
        # enough that the termination's text (facing back toward the breaker) stays
        # `u_turn_text_clearance` clear of the breaker and its text (2026-10-13).
        depth = (_reach_past_far_terminals(block, far_terminals, direction)
                 + mb.u_turn_text_clearance
                 + _termination_reach(settings, catalog, termination_feed, direction, io_attributes)
                 + mb.u_turn_termination_rise)
        input_x = far[0][0] + mb.u_turn_width
        input_y = far[0][1] + direction * (depth - mb.u_turn_termination_rise)
        geometry.bus_lines += _u_turn(far, direction, mb.u_turn_width, input_y, settings, depth)

    # Bus side: from the main bus to the breaker's bus end.
    dot_block = settings.main_bus.junction_dot_block
    dot_extents = catalog[dot_block].extents if dot_block in catalog else (-0.75, -0.75, 0.75, 0.75)
    if fed_on_bus_side:
        # Up (or down) beside the breaker on the right, over it, and into its far end.
        # As a B-phase path this is the same U-turn _u_turn() draws phase by phase.
        b_x, b_y = far[1]
        turn_b = b_y + direction * (mb.u_turn_depth + half)
        path = [(b_x, b_y), (b_x, turn_b), (b_x + mb.u_turn_width, turn_b),
                (b_x + mb.u_turn_width, plan.body_y)]
        riser_x = {phase: x + mb.u_turn_width for phase, (x, _) in zip("ABC", far)}
    else:
        b_x, b_y = near[1]
        path = [(b_x, b_y), (b_x, plan.body_y)]
        riser_x = {phase: x for phase, (x, _) in zip("ABC", near)}
    if starts_the_bus:
        geometry.bus_start_path = path                    # the main bus goes on from here
    elif ends_the_bus:
        geometry.bus_end_path = list(reversed(path))
    else:
        # The main bus is already running here: each phase tees in with a dot.
        if fed_on_bus_side:
            geometry.bus_lines += _u_turn(far, direction, mb.u_turn_width, bus_y, settings)
        else:
            for phase, (x, y) in zip("ABC", near):
                geometry.bus_lines.append(BusLine(phase, (x, y), (x, bus_y[phase])))
        for phase in "ABC":
            geometry.blocks.append(BlockPlacement(
                block=dot_block, layer=settings.main_bus.layer,
                position=(riser_x[phase], bus_y[phase]), extents=dot_extents))

    io = settings.input_output
    io_block = catalog.get(io.block)
    if io_block is not None and io_block.connections:
        # A termination fed from the top uses the flipped block ("from the top").
        flipped = termination_feed == TOP
        a_x, a_y = io_block.connection("A", flipped)
        geometry.blocks.append(BlockPlacement(
            block=io.block, layer=io.layer, position=(input_x - a_x, input_y - a_y),
            attributes=_filled(io_attributes),
            visibility=io_state, flipped=flipped,
            extents=io_block.oriented_extents(flipped),
        ))
    else:
        # Input block not catalogued: keep its room as a placeholder box, on the side
        # the termination is fed from.
        shift = input_x - near[0][0]
        box_left = base_x + block.extents[0] + shift
        box_right = base_x + block.extents[2] + shift
        box_far_y = input_y + (1 if termination_feed == TOP else -1) * mb.input_box_height
        geometry.placeholders.append(Placeholder(
            "OUTPUT" if io_state == io.output_state else "INPUT",
            box_left, min(input_y, box_far_y), box_right, max(input_y, box_far_y)))
    return geometry


def _u_turn(ends, direction, width, back_to_y, settings, depth=None) -> list[BusLine]:
    """Bus lines for a U-turn from the A, B, C `ends` (all at one height): on in
    `direction` (+1 up, -1 down) until the nearest phase is `depth` away (default
    `u_turn_depth`), across by `width` (+ right, - left), and back to `back_to_y` (one
    height, or {phase: height}).
    Phases follow the references' rule, as the main bus does: A left of B on vertical
    runs and above it on horizontal runs, so the corners are staggered and some phases
    cross without connecting (NTT-013630 section 1)."""
    half = settings.main_bus.phase_spacing
    if depth is None:
        depth = settings.main_breaker.u_turn_depth
    start_y = ends[0][1]
    turn_b = start_y + direction * (depth + half)
    lines = []
    for phase, (x, _) in zip("ABC", ends):
        turn_y = turn_b + {"A": half, "B": 0.0, "C": -half}[phase]
        back_x = x + width
        end_y = back_to_y[phase] if isinstance(back_to_y, dict) else back_to_y
        lines += [BusLine(phase, (x, start_y), (x, turn_y)),
                  BusLine(phase, (x, turn_y), (back_x, turn_y)),
                  BusLine(phase, (back_x, turn_y), (back_x, end_y))]
    return lines


def _reach_past_far_terminals(block, far_terminals, direction) -> float:
    """How far the breaker block (with its text) reaches past its far terminals, away
    from the bus. From the block's size in the catalog."""
    far_y = far_terminals[0][1]
    return block.extents[3] - far_y if direction > 0 else far_y - block.extents[1]


def _termination_reach(settings, catalog, termination_feed, direction, io_attributes) -> float:
    """How far the termination block (with its text) reaches from its connection point
    back toward the breaker, at the end of a U-turn that went in `direction`. Without the
    block in the catalog, its placeholder box's height.

    The catalog's size holds one line of text. The termination's text grows away from the
    block (toward the breaker) with each line break the engineer typed, so the most lines
    in any of its attributes are added on."""
    extra = max((settings.text.extra_height_for_lines(value) for value in io_attributes.values()),
                default=0.0)
    io_block = catalog.get(settings.input_output.block)
    if io_block is None or not io_block.connections:
        return settings.main_breaker.input_box_height + extra
    flipped = termination_feed == TOP
    _, conn_y = io_block.connection("A", flipped)
    _, bottom, _, top = io_block.oriented_extents(flipped)
    # The U came back toward the bus: against `direction`.
    return (top - conn_y if direction < 0 else conn_y - bottom) + extra


def content_left_x(placed, settings) -> float:
    """Where a section's contents start: after the bus step zone if the bus changes height
    here, so the vertical run of bus stays clear of them."""
    plan = placed.section.bus
    step = step_zone_width(settings) if plan is not None and plan.steps_at_entry else 0.0
    return placed.component_left_x + step


def tie_breaker_placement(tie, tie_x, body_y, exit_y, settings, catalog):
    """The tie's breaker block, centred on the bus's vertical run at x `tie_x`.
    Returns (BlockPlacement, lower terminal y, upper terminal y), or None if the block
    isn't catalogued. The bus runs up to the lower terminals and on from the upper ones."""
    name = settings.main_breaker.blocks[tie.mounting]
    block = catalog.get(name)
    if block is None or not block.top_terminals:
        return None
    half = settings.main_bus.phase_spacing
    top_a = block.top_terminals[0]
    pole_length = top_a[1] - block.bottom_terminals[0][1]
    middle = (body_y + exit_y) / 2
    upper_y, lower_y = middle + pole_length / 2, middle - pole_length / 2
    # The vertical run has A on the left: A is at tie_x - half.
    position = (tie_x - half - top_a[0], upper_y - top_a[1])
    placement = BlockPlacement(
        block=name, layer=settings.main_breaker.block_layer, position=position,
        attributes=_filled({**tie.breaker.attributes,
                            settings.main_breaker.label_attribute: tie.breaker.label}),
        visibility=settings.main_breaker.visibility, label=tie.breaker.label,
        extents=block.extents,
    )
    return placement, lower_y, upper_y


def _filled(values: dict) -> dict:
    """Only attributes with a value; empty ones keep the block's own default."""
    return {tag: value for tag, value in values.items() if value}


def terminal_spacing_problem(settings, catalog) -> str:
    """The bus phases must line up with each main breaker block's poles.
    Returns a problem, or ""."""
    spacing = settings.main_bus.phase_spacing
    io_block = catalog.get(settings.input_output.block)
    if io_block is not None and io_block.connections:
        for flip, points in io_block.connections.items():
            xs = [points[phase][0] for phase in "ABC"]
            if any(abs((xs[i + 1] - xs[i]) - spacing) > 0.05 for i in range(2)):
                return (f'Block "{io_block.name}" ({flip}) has connections {xs} but the bus '
                        f"phases are {spacing} apart, so they can't line up.")
    for mounting, name in settings.main_breaker.blocks.items():
        block = catalog.get(name)
        if block is None:
            return f'Block "{name}" ({mounting} main breaker) is not in catalog/blocks.json.'
        for terminals in (block.top_terminals, block.bottom_terminals):
            if len(terminals) != 3:
                return f'Block "{name}" needs 3 top and 3 bottom terminals in the catalog.'
            gaps = [terminals[i + 1][0] - terminals[i][0] for i in range(2)]
            if any(abs(g - spacing) > 0.05 for g in gaps):
                return (f'Block "{name}" poles are {gaps} apart but the bus phases are '
                        f"{spacing} apart, so they can't line up.")
    return ""
