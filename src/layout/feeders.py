"""Group-mounted feeder geometry: a vertical bus off the main bus, with feeder breakers on
levels to its left and right. (docs/DECISIONS.md, "Breaker arrangement vocabulary" and
"Group mounted levels"; measured from GND_Section_Devider_REFERENCE ES_12.)

    left breaker ==taps==> | | | <==taps== right breaker (same block, mirrored)
                           A B C   <- vertical bus, A on the left, phases 5 apart

- Levels are counted outward from the main bus. Above the bus, level 1's lowest tap (C) is
  `gap_to_first_level` above the main bus's top phase; below the bus, level 1's top tap (A)
  is the same gap below the main bus's bottom phase. Levels are `level_pitch` apart. Each
  breaker keeps A on top, above and below the bus alike.
- Each breaker phase has a horizontal tap to its own vertical-bus phase, ending in a
  junction dot. The tap to the nearest phase is `tap_length` long (A on the left side, C on
  the right side), so the others are 5 and 10 longer and cross the nearer phases.
- The vertical bus runs `vertical_bus_overhang` past the outermost level.
- Where it meets the main bus, each phase tees into its own main-bus phase with a dot.
  Where the main bus begins (or ends) at this section, it bends into the vertical bus
  instead, like a main breaker does.
- A Provision is tapped out just like a breaker (taps and dots, ending where the breaker
  would connect), then a note: "PROVISION FOR" and the engineer's line, starting
  `provision_text_gap` beyond the tap ends, centred on the B tap. (From IMS-REFERENCE.)
  A Space (an unused position) is drawn the same way with just the word "SPACE".
- Too tall for the page (section_builder.plan_columns decides the split): a column that
  goes on in the next column is cut at its far end, and the next column starts
  `continuation_start_gap` from the main bus, not connected to it. Both ends are marked
  with the bus-break tilde (on the A-phase end) and bracket (over B, `bracket_gap` past
  the end), as in CORRECTED_FIXED_011511 ES_11 and FIXED_011511 ES_12. The cut end's
  bracket says "BUS CONTINUES"; the next column's says "FROM BELOW" (a part below the
  main bus) or "FROM ABOVE" (config `bus_break`).

Pure Python, no AutoCAD. Coordinates are frame-relative.
"""
from src.layout.main_breakers import (
    BlockPlacement, BusLine, MainBreakerGeometry, Note, _filled, content_left_x,
)
from src.layout.section_builder import LEFT, RIGHT, column_lead, level_slots, plan_columns
from src.model.section_contents import Breaker

PHASES = "ABC"


def feeder_block(settings, catalog):
    """The catalogued feeder block, or None (then group-mounted parts stay placeholders)."""
    if catalog is None:
        return None
    block = catalog.get(settings.feeder.block)
    if block is None or not block.connections:
        return None
    return block


def group_geometry(group, part, placed, settings, catalog, starts_the_bus,
                   ends_the_bus) -> MainBreakerGeometry:
    """Geometry for the group-mounted distribution in the `part` ("above" or "below") of a
    placed section, on every column it uses. The feeder block must be catalogued (see
    feeder_block())."""
    geometry = MainBreakerGeometry()
    if not group.levels:
        return geometry          # nothing on it yet: no vertical bus either
    block = feeder_block(settings, catalog)
    plan = plan_columns(placed.section.contents, settings, block)
    left_x = content_left_x(placed, settings)
    dots = []
    for index, column in enumerate(plan.columns):
        level_indices = getattr(column, part)
        if not level_indices:
            continue
        _add_column(geometry, dots, group, part, level_indices, index,
                    left_x + plan.a_offsets[index], plan.continues_after(part, index),
                    placed, settings, catalog, block,
                    starts_the_bus and index == 0, ends_the_bus and index == 0)

    dot_block = settings.main_bus.junction_dot_block
    dot_extents = catalog[dot_block].extents if dot_block in catalog else (-0.75, -0.75, 0.75, 0.75)
    for point in dict.fromkeys(dots):          # one dot where two taps meet the same phase
        geometry.blocks.append(BlockPlacement(
            block=dot_block, layer=settings.main_bus.layer, position=point,
            extents=dot_extents))
    return geometry


def _add_column(geometry, dots, group, part, level_indices, column_index, a_x, is_cut,
                placed, settings, catalog, block, starts_the_bus, ends_the_bus):
    """One column's vertical bus, its levels and taps. Column 1 (index 0) meets the main
    bus; a continuation column starts near it, marked with the break blocks. `is_cut`:
    the part goes on in a later column, so this one's far end is marked too."""
    fd, gm = settings.feeder, settings.group_mounted
    half = settings.main_bus.phase_spacing
    plan = placed.section.bus
    main_y = {"A": plan.body_y + half, "B": plan.body_y, "C": plan.body_y - half}
    bus_x = {"A": a_x, "B": a_x + half, "C": a_x + 2 * half}
    conn_x = {LEFT: bus_x["A"] - fd.tap_length, RIGHT: bus_x["C"] + fd.tap_length}
    lead = column_lead(column_index, gm)

    # Level positions: y of each level's A tap (its top); C is level_height below it.
    # `away` is the direction away from the main bus: +1 above it, -1 below it.
    if part == "above":
        away, near_bus_y = +1, main_y["A"]
        first_a = near_bus_y + lead + gm.level_height
    else:
        away, near_bus_y = -1, main_y["C"]
        first_a = near_bus_y - lead
    level_a_ys = [first_a + away * n * gm.level_pitch for n in range(len(level_indices))]
    far_end_y = level_a_ys[-1] + gm.vertical_bus_overhang if away > 0 else \
        level_a_ys[-1] - gm.level_height - gm.vertical_bus_overhang

    # The vertical bus, and how it meets the main bus (column 1) or starts near it.
    br = settings.bus_break
    if column_index > 0:
        start_y = near_bus_y + away * gm.continuation_start_gap
        for phase in PHASES:
            geometry.bus_lines.append(BusLine(phase, (bus_x[phase], start_y),
                                              (bus_x[phase], far_end_y)))
        came_from = br.continued_from_above_label if part == "above" else br.continued_from_below_label
        geometry.blocks += _vertical_break_blocks(a_x, start_y, -away, came_from, settings, catalog)
    elif starts_the_bus:
        geometry.bus_start_path = [(bus_x["B"], far_end_y), (bus_x["B"], plan.body_y)]
    elif ends_the_bus:
        geometry.bus_end_path = [(bus_x["B"], plan.body_y), (bus_x["B"], far_end_y)]
    else:
        for phase in PHASES:
            geometry.bus_lines.append(BusLine(phase, (bus_x[phase], main_y[phase]),
                                              (bus_x[phase], far_end_y)))
            dots.append((bus_x[phase], main_y[phase]))
    if is_cut:
        geometry.blocks += _vertical_break_blocks(a_x, far_end_y, away, br.column_cut_label,
                                                  settings, catalog)

    # The breakers and provisions, and their taps.
    all_slots = level_slots(group, settings)
    for level_a_y, level_index in zip(level_a_ys, level_indices):
        for side, slot in all_slots[level_index].items():
            if isinstance(slot, Breaker):
                flipped = side == RIGHT
                a_dx, a_dy = block.connection("A", flipped)
                position = (conn_x[side] - a_dx, level_a_y - a_dy)
                geometry.blocks.append(BlockPlacement(
                    block=fd.block, layer=fd.layer, position=position,
                    attributes=_filled({**slot.attributes, fd.label_attribute: slot.label}),
                    visibility=fd.visibility, label=slot.label, flipped=flipped,
                    flip_parameter=fd.mirror_parameter if flipped else "",
                    extents=block.oriented_extents(flipped),
                ))
                tap_ends = {phase: (position[0] + block.connection(phase, flipped)[0],
                                    position[1] + block.connection(phase, flipped)[1])
                            for phase in PHASES}
            else:
                # A provision or space: taps end where a breaker would connect, then the note.
                tap_ends = {phase: (conn_x[side], level_a_y - n * half)
                            for n, phase in enumerate(PHASES)}
                outward = -1 if side == LEFT else +1
                geometry.notes.append(Note(
                    lines=fd.note_lines(slot),
                    x=conn_x[side] + outward * fd.provision_text_gap,
                    middle_y=tap_ends["B"][1],
                    align="middle_right" if side == LEFT else "middle_left"))
            for phase, (end_x, tap_y) in tap_ends.items():
                geometry.bus_lines.append(BusLine(phase, (end_x, tap_y), (bus_x[phase], tap_y)))
                dots.append((bus_x[phase], tap_y))


def _vertical_break_blocks(a_x, end_y, outward, label, settings, catalog) -> list:
    """Tilde + bracket where a vertical bus is cut or starts: the tilde on the A-phase end,
    the bracket over B, `bracket_gap` past the end (`outward` +1 = up, -1 = down), with
    `label` in it. Neither is flipped (as in ES_11 and ES_12). Returns [] if the blocks
    aren't catalogued."""
    br = settings.bus_break
    tilde = catalog.get(br.tilde_block)
    bracket = catalog.get(br.bracket_block)
    if tilde is None or bracket is None or not tilde.connections:
        return []
    conn_a = tilde.connection("A", False)
    b_x = a_x + settings.main_bus.phase_spacing
    return [
        BlockPlacement(block=br.tilde_block, layer=br.layer,
                       position=(a_x - conn_a[0], end_y - conn_a[1]),
                       visibility=br.tilde_state_vertical_bus, extents=tilde.extents),
        BlockPlacement(block=br.bracket_block, layer=br.layer,
                       position=(b_x, end_y + outward * br.bracket_gap),
                       attributes={br.label_attribute_vertical_bus: label}, label=label,
                       visibility=br.bracket_state_vertical_bus, extents=bracket.extents),
    ]
