"""Main breaker geometry: how the bus comes in, through the breaker, and onto the main bus.
(docs/DECISIONS.md, 2026-10-11 "Input / output bus connection".)

Above the main bus (fed from the TOP), power flows down:
    input (top) -> bus down into the breaker -> breaker -> bus down -> main bus
Below the main bus (fed from the BOTTOM), power flows up: the same, upside down.

Where the bus meets the main bus:
- At the very start of the lineup the main bus begins here, so the riser BENDS into it
  (a corner, no junction dots), like the references.
- Anywhere else the main bus is already running, so each phase TEES into its own bus line
  with a junction dot.

The breaker is the library block, placed at scale 1 by its base point, so that its
terminals (from catalog/blocks.json) line up with the bus. The input block is not ready
yet, so its place is kept as a placeholder box.

Pure Python, no AutoCAD. Coordinates are frame-relative.
"""
from dataclasses import dataclass, field

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


@dataclass
class Placeholder:
    """A box kept for something whose block isn't ready yet."""
    text: str
    left_x: float
    bottom_y: float
    right_x: float
    top_y: float


@dataclass
class MainBreakerGeometry:
    # When the main bus starts here: B-phase points from the breaker to the main bus,
    # ending at the main bus height. The page's bus path continues from the last point.
    bus_start_path: list[Point] | None = None
    bus_lines: list[BusLine] = field(default_factory=list)
    blocks: list[BlockPlacement] = field(default_factory=list)
    placeholders: list[Placeholder] = field(default_factory=list)


def main_breaker_geometry(main_breaker, part, placed, settings, catalog, starts_the_bus) -> MainBreakerGeometry:
    """Geometry for the main breaker in the `part` ("above" or "below") of a placed section."""
    mb = settings.main_breaker
    block = catalog[mb.block]
    half = settings.main_bus.phase_spacing
    plan = placed.section.bus
    bus_y = {"A": plan.body_y + half, "B": plan.body_y, "C": plan.body_y - half}

    # The block's left edge sits on the section's content edge (after any bus step zone).
    step = settings.main_bus.step_width if plan.steps_at_entry else 0.0
    base_x = placed.component_left_x + step - block.extents[0]

    if part == "above":
        # Breaker's bottom terminals face the bus, `gap` above the A (top) bus line.
        near_terminals, far_terminals = block.bottom_terminals, block.top_terminals
        near_y = bus_y["A"] + mb.gap_bus_to_breaker
        base_y = near_y - near_terminals[0][1]
        direction = +1          # the input is further up
    else:
        near_terminals, far_terminals = block.top_terminals, block.bottom_terminals
        near_y = bus_y["C"] - mb.gap_bus_to_breaker
        base_y = near_y - near_terminals[0][1]
        direction = -1          # the input is further down

    near = [(base_x + x, base_y + y) for x, y in near_terminals]
    far = [(base_x + x, base_y + y) for x, y in far_terminals]
    input_y = far[0][1] + direction * mb.gap_breaker_to_input

    geometry = MainBreakerGeometry()
    geometry.blocks.append(BlockPlacement(
        block=mb.block, layer=mb.block_layer, position=(base_x, base_y),
        attributes={"BREAKER_NAME": main_breaker.breaker.label}, visibility=mb.visibility,
        label=main_breaker.breaker.label, extents=block.extents,
    ))

    # Input side: each phase from the input end to the breaker's far terminal.
    for phase, (x, y) in zip("ABC", far):
        geometry.bus_lines.append(BusLine(phase, (x, input_y), (x, y)))

    # Main bus side.
    if starts_the_bus:
        b_x = near[1][0]
        geometry.bus_start_path = [(b_x, near[1][1]), (b_x, plan.body_y)]
    else:
        dot_block = settings.main_bus.junction_dot_block
        dot_extents = catalog[dot_block].extents if dot_block in catalog else (-0.75, -0.75, 0.75, 0.75)
        for phase, (x, y) in zip("ABC", near):
            geometry.bus_lines.append(BusLine(phase, (x, y), (x, bus_y[phase])))
            geometry.blocks.append(BlockPlacement(
                block=dot_block, layer=settings.main_bus.layer, position=(x, bus_y[phase]),
                extents=dot_extents))

    # Room kept for the input block (coming soon).
    box_left = base_x + block.extents[0]
    box_right = base_x + block.extents[2]
    box_far_y = input_y + direction * mb.input_box_height
    geometry.placeholders.append(Placeholder(
        "INPUT", box_left, min(input_y, box_far_y), box_right, max(input_y, box_far_y)))
    return geometry


def terminal_spacing_problem(settings, catalog) -> str:
    """The bus phases must line up with the breaker's poles. Returns a problem, or ""."""
    block = catalog.get(settings.main_breaker.block)
    if block is None:
        return f'Block "{settings.main_breaker.block}" is not in catalog/blocks.json.'
    spacing = settings.main_bus.phase_spacing
    for terminals in (block.top_terminals, block.bottom_terminals):
        if len(terminals) != 3:
            return f'Block "{block.name}" needs 3 top and 3 bottom terminals in the catalog.'
        gaps = [terminals[i + 1][0] - terminals[i][0] for i in range(2)]
        if any(abs(g - spacing) > 0.05 for g in gaps):
            return (f'Block "{block.name}" poles are {gaps} apart but the bus phases are '
                    f"{spacing} apart, so they can't line up.")
    return ""
