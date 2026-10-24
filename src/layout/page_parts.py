"""Page parts: the dividers, ground bus and section labels drawn on every 3-line page.

Runs after page fitting has decided where each section goes. Pure Python, no AutoCAD.
All numbers come from config/layout_settings.json; the style is Sammy's restyled ES_01
(see docs/DECISIONS.md, 2026-10-09 entries).

Rules applied:
- One divider between adjacent sections. None at the start or end of the lineup.
- When a page ends but the lineup continues on the next page, the divider after the last
  section goes at the end of the current page. If it can't fit there (it would run down
  through the title block), it goes at the start of the next page instead.
- A divider between two sections that sits over the title block stops at the title
  block's top edge.
- The ground bus runs from a fixed start to just before the title block. On the last page
  it stops at the end of the last section, since nothing continues past it.
- The main bus runs through every section at the height planned in main_bus.py. Where a
  section makes it change height, it steps in the middle of that section's 10-wide step
  zone (just inside its left clearance). After a tie breaker it steps at the tie, which
  sits at the section's right edge.
- Each section gets a "SECTION n" label (n = position in the lineup), centred between its
  two edges, below the ground bus. If that would put it in the title block, it moves up to
  sit just above the title block.
"""
from dataclasses import dataclass, field

from src.layout.feeders import feeder_block, group_geometry
from src.layout.main_breakers import (
    BlockPlacement, Crossing, LineSideTie, Placeholder, content_left_x, main_breaker_geometry,
    main_lugs_geometry, single_breaker_geometry, terminal_spacing_problem, tie_breaker_placement,
    tie_bus_x,
)
from src.model.section_contents import (
    GroupMounted, IncomingFeed, LineSideBreaker, MainBreaker, SingleBreaker,
)

ROUNDING_TOLERANCE = 1e-9


@dataclass
class DividerLine:
    x: float
    bottom_y: float
    top_y: float


@dataclass
class GroundBusLine:
    start_x: float
    end_x: float
    y: float


@dataclass
class SectionLabel:
    text: str
    center_x: float
    bottom_y: float


@dataclass
class ContentBox:
    """Where a section's contents go: one box above the main bus, one below.
    Drawn as placeholders until the real blocks are in."""
    section_number: int
    part: str            # "above" or "below"
    left_x: float
    bottom_y: float
    right_x: float
    top_y: float


@dataclass
class PageParts:
    # Main bus centre line (B phase): one or more runs of corner points, left to right.
    # A run ends where a tie breaker block sits in the bus. A is phase_spacing above /
    # left of the centre line, C the same below / right.
    bus_paths: list[list[tuple[float, float]]] = field(default_factory=list)
    dividers: list[DividerLine] = field(default_factory=list)
    content_boxes: list[ContentBox] = field(default_factory=list)
    # Main breakers drawn for real (see main_breakers.py): extra bus runs, library blocks
    # (breakers, junction dots) and placeholders for blocks that aren't ready yet.
    bus_lines: list = field(default_factory=list)
    blocks: list = field(default_factory=list)
    placeholders: list = field(default_factory=list)
    notes: list = field(default_factory=list)          # plain text, e.g. provision notes
    # Wires the program draws itself, each on its own layer (device pages, 2026-10-23).
    wires: list = field(default_factory=list)
    bus_start_path: list | None = None
    bus_end_path: list | None = None
    ground_bus: GroundBusLine | None = None
    section_labels: list[SectionLabel] = field(default_factory=list)


def add_page_parts(pages, settings, catalog=None, warnings=None):
    """Fill in page.parts for every page. Without a block catalog, main breakers are left
    as placeholder boxes."""
    for page in pages:
        page.parts = PageParts()

    if catalog is not None:
        problem = terminal_spacing_problem(settings, catalog)
        if problem:
            if warnings is not None:
                warnings.append(problem)
            catalog = None      # can't line the bus up with this block, so don't try

    _add_dividers(pages, settings)
    for index, page in enumerate(pages):
        drawn_parts = _add_arrangements(page, settings, catalog, warnings)
        continues = index < len(pages) - 1
        _add_bus_paths(page, settings, catalog, continues)
        _add_content_boxes(page, settings, drawn_parts)
    for index, page in enumerate(pages):
        is_last_page = index == len(pages) - 1
        _add_ground_bus(page, is_last_page, settings)
        _add_section_labels(page, settings)


def _add_dividers(pages, settings):
    divider = settings.divider
    carried_to_next_page = False

    for index, page in enumerate(pages):
        placed = page.placed_sections
        if not placed:
            continue

        # A divider that didn't fit at the end of the previous page goes here, at the start.
        if carried_to_next_page:
            page.parts.dividers.append(
                DividerLine(placed[0].left_divider_x, divider.bottom_y, divider.top_y)
            )
            carried_to_next_page = False

        # Between neighbours on this page.
        for section in placed[1:]:
            page.parts.dividers.append(_divider_clear_of_title_block(section.left_divider_x, settings))

        # After the last section, only if the lineup continues on the next page.
        lineup_continues = index < len(pages) - 1
        if lineup_continues:
            end_x = placed[-1].right_divider_x
            if _runs_into_title_block(end_x, settings):
                carried_to_next_page = True
            else:
                page.parts.dividers.append(DividerLine(end_x, divider.bottom_y, divider.top_y))


def _runs_into_title_block(x, settings) -> bool:
    """A full-height divider at this x would cut through the title block."""
    over_title_block = x > settings.keepout_left_x + ROUNDING_TOLERANCE
    reaches_down_into_it = settings.divider.bottom_y < settings.keepout_height
    return over_title_block and reaches_down_into_it


def _divider_clear_of_title_block(x, settings) -> DividerLine:
    """A divider BETWEEN two sections can't move to another page. If it sits over the title
    block, it stops at the title block's top edge (as PRIME-014032 does)."""
    divider = settings.divider
    if _runs_into_title_block(x, settings):
        return DividerLine(x, settings.keepout_height, divider.top_y)
    return DividerLine(x, divider.bottom_y, divider.top_y)


def _add_arrangements(page, settings, catalog, warnings=None) -> set:
    """Draw main breakers, single-breaker feeders and group-mounted feeders for real.
    Returns {(section number, part)} that were drawn, so their placeholder boxes are
    left out."""
    drawn = set()
    if catalog is None:
        return drawn
    feeder = feeder_block(settings, catalog)
    for placed in page.placed_sections:
        box = placed.section
        for part in box.parts_drawn_elsewhere:
            drawn.add((placed.number, part))     # drawn with the main breaker it feeds
        if box.bus is None or box.contents is None:
            continue
        parts = {}
        for part in ("above", "below"):
            arrangement = getattr(box.contents, part)
            if arrangement is None or (isinstance(arrangement, GroupMounted) and feeder is None):
                continue                  # nothing there, or feeder block not catalogued
            if (part in box.parts_drawn_elsewhere or part in box.feed_parts_not_drawn
                    or isinstance(arrangement, LineSideBreaker)):
                continue                  # drawn with a main, or can't be drawn (warned)
            extras = (_crossing(box, part, page, warnings, placed.number),
                      _line_side_tie(box, part, page, warnings, placed.number))
            parts[part] = (arrangement, extras)

        def draw(part, starts_the_bus, ends_the_bus):
            arrangement, (crossing, tie) = parts[part]
            if isinstance(arrangement, MainBreaker):
                return main_breaker_geometry(arrangement, part, placed, settings, catalog,
                                             starts_the_bus, ends_the_bus, crossing, tie)
            if isinstance(arrangement, IncomingFeed):
                return main_lugs_geometry(arrangement, part, placed, settings, catalog,
                                          starts_the_bus, ends_the_bus)
            if isinstance(arrangement, SingleBreaker):
                return single_breaker_geometry(arrangement, part, placed, settings, catalog,
                                               starts_the_bus, ends_the_bus)
            return group_geometry(arrangement, part, placed, settings, catalog,
                                  starts_the_bus, ends_the_bus)

        # The bus begins (or ends) in the first (or last) section that uses it; there it
        # bends into the leftmost (or rightmost) riser, and the other part tees into it, so
        # nothing tees into bus that isn't there (2026-10-22).
        def riser_x(part, starts):
            geometry = draw(part, starts, not starts)
            path = geometry.bus_start_path if starts else geometry.bus_end_path
            return path[0][0] if path else None

        start_part = end_part = None
        if box.bus.starts_bus and page.parts.bus_start_path is None:
            xs = {part: riser_x(part, True) for part in parts}
            xs = {part: x for part, x in xs.items() if x is not None}
            start_part = min(xs, key=xs.get) if xs else None
        if box.bus.ends_bus and page.parts.bus_end_path is None:
            xs = {part: riser_x(part, False) for part in parts if part != start_part}
            xs = {part: x for part, x in xs.items() if x is not None}
            end_part = max(xs, key=xs.get) if xs else None

        for part in parts:
            geometry = draw(part, part == start_part, part == end_part)
            if geometry.bus_start_path:
                page.parts.bus_start_path = geometry.bus_start_path
            if geometry.bus_end_path:
                page.parts.bus_end_path = geometry.bus_end_path
            page.parts.bus_lines += geometry.bus_lines
            page.parts.blocks += geometry.blocks
            page.parts.placeholders += geometry.placeholders
            page.parts.notes += geometry.notes
            if warnings is not None:
                warnings += geometry.warnings
            drawn.add((placed.number, part))
    return drawn


def _crossing(box, part, page, warnings, number):
    """The Crossing for a main breaker fed from the next section, or None."""
    if part not in box.feed_crossings:
        return None
    feed_index, feed_part = box.feed_crossings[part]
    feed_placed = next((p for p in page.placed_sections if p.number == feed_index + 1), None)
    if feed_placed is None:
        if warnings is not None:
            warnings.append(f"Section {number}: its incoming feed (section {feed_index + 1}) is on "
                            f"another page, so it is not drawn.")
        return None
    return Crossing(feed=getattr(feed_placed.section.contents, feed_part), placed=feed_placed,
                    tap_values=feed_placed.section.tap_attributes.get(feed_part, []))


def _line_side_tie(box, part, page, warnings, number):
    """The LineSideTie for a main breaker with a line-side breaker next to it, or None."""
    if part not in box.line_side_ties:
        return None
    index, other_part = box.line_side_ties[part]
    other = next((p for p in page.placed_sections if p.number == index + 1), None)
    if other is None:
        if warnings is not None:
            warnings.append(f"Section {number}: its line-side breaker (section {index + 1}) is on "
                            f"another page, so it is not drawn.")
        return None
    return LineSideTie(breaker=getattr(other.section.contents, other_part), placed=other)


def page_break_overrun(placed, page, settings) -> float:
    """How far the bus runs past the page's last divider: as much as fits up to the
    maximum (leaving room for the break label), never less than the minimum."""
    bus = settings.main_bus
    limit = settings.drawable_width - page.side_margin
    plan = placed.section.bus
    if plan.exit_y - bus.phase_spacing < settings.keepout_height - ROUNDING_TOLERANCE:
        limit = min(limit, settings.keepout_left_x)        # bus is beside the title block
    room = limit - placed.right_divider_x - bus.page_break_label_space
    return max(bus.page_break_overrun_min, min(bus.page_break_overrun_max, room))


def _add_bus_paths(page, settings, catalog, continues_on_next_page=False):
    """The main bus on this page. It only runs through sections that have a bus plan (from
    the first section that uses the bus to the last). It is cut where a tie breaker block
    sits in it, so the result can be several runs."""
    paths = page.parts.bus_paths
    current = list(page.parts.bus_start_path or [])   # bends up/down out of a main breaker
    for placed in page.placed_sections:
        box = placed.section
        plan = box.bus
        if plan is None:          # no bus in this section (empty at the ends, or tests)
            continue
        if not current and not paths:
            # Start of the bus on this page: where the lineup's bus begins, or (carried over
            # from the previous page) right away at the left, marked with the break blocks.
            if plan.starts_bus:
                start_x = content_left_x(placed, settings)
            else:
                breaks = _break_blocks(placed.component_left_x, plan.entry_y, "from",
                                       page.number - 1, settings, catalog)
                start_x = placed.component_left_x if breaks else placed.left_divider_x
                page.parts.blocks += breaks
            current.append((start_x, plan.entry_y))
        if plan.steps_at_entry:
            step_x = placed.left_divider_x + settings.divider_clearance + settings.main_bus.step_width / 2
            current.append((step_x, plan.entry_y))
            current.append((step_x, plan.body_y))
        if box.has_tie and abs(plan.exit_y - plan.body_y) > ROUNDING_TOLERANCE:
            tie_x = tie_bus_x(placed, settings, catalog)
            tie = box.contents.tie if box.contents is not None else None
            placed_tie = (tie_breaker_placement(tie, tie_x, plan.body_y, plan.exit_y, settings, catalog,
                                                box.ct_attributes.get("tie"))
                          if catalog is not None and tie is not None else None)
            if placed_tie is None:
                current.append((tie_x, plan.body_y))      # no block: bus runs straight on
                current.append((tie_x, plan.exit_y))
            else:
                blocks, lower_y, upper_y = placed_tie
                page.parts.blocks += blocks
                going_up = plan.exit_y > plan.body_y
                near_y, far_y = (lower_y, upper_y) if going_up else (upper_y, lower_y)
                current.append((tie_x, plan.body_y))
                current.append((tie_x, near_y))           # into the breaker
                paths.append(current)
                current = [(tie_x, far_y), (tie_x, plan.exit_y)]   # out of the breaker
        if plan.ends_bus and page.parts.bus_end_path:
            current.extend(page.parts.bus_end_path)        # bends into the last main breaker
        elif plan.ends_bus:
            current.append((placed.component_right_x, plan.exit_y))
        elif continues_on_next_page and placed is page.placed_sections[-1]:
            # The bus goes on to the next page: run it past the divider, and keep room for
            # the break block's to/from label (a placeholder until that block exists).
            end_x = placed.right_divider_x + page_break_overrun(placed, page, settings)
            current.append((end_x, plan.exit_y))
            breaks = _break_blocks(end_x, plan.exit_y, "to", page.number + 1, settings, catalog)
            if breaks:
                page.parts.blocks += breaks
            else:   # break blocks not catalogued: keep their room as a placeholder
                half = settings.main_bus.phase_spacing
                page.parts.placeholders.append(Placeholder(
                    "TO NEXT PAGE", end_x, plan.exit_y - half,
                    end_x + settings.main_bus.page_break_label_space, plan.exit_y + half))
        else:
            current.append((placed.right_divider_x, plan.exit_y))
    if current:
        paths.append(current)


def _break_blocks(end_x, bus_y, direction, other_page, settings, catalog) -> list:
    """Tilde + labelled bracket where the horizontal main bus is cut at a page break.
    `end_x` is the bus end; `direction` "to" (bus leaves to the right) or "from" (bus
    arrives from the left). Where the bus arrives, both blocks are mirrored to face it:
    the tilde with only its left-right flip setting, so its A/B/C letters sit on the
    incoming side, away from the bus. Returns [] if the blocks aren't catalogued."""
    br = settings.bus_break
    tilde = catalog.get(br.tilde_block) if catalog else None
    bracket = catalog.get(br.bracket_block) if catalog else None
    if tilde is None or bracket is None or not tilde.connections:
        return []
    a_y = bus_y + settings.main_bus.phase_spacing          # A is the top phase
    conn_a = tilde.connection("A", False)
    label = br.label(direction, other_page)
    leaving = direction == "to"
    bracket_x = end_x + br.bracket_gap if leaving else end_x - br.bracket_gap
    return [
        BlockPlacement(block=br.tilde_block, layer=br.layer,
                       position=(end_x - conn_a[0], a_y - conn_a[1]),
                       visibility=br.tilde_state_horizontal_bus,
                       flipped=not leaving, flip_parameter=br.tilde_flip_horizontal_bus,
                       extents=tilde.oriented_extents(not leaving)),
        BlockPlacement(block=br.bracket_block, layer=br.layer, position=(bracket_x, bus_y),
                       attributes={br.label_attribute_horizontal_bus: label}, label=label,
                       visibility=br.bracket_state_horizontal_bus,
                       # Mirrored left-right to face the arriving bus (only that flip).
                       flipped=not leaving, flip_parameter=br.bracket_flip_horizontal_bus,
                       extents=bracket.oriented_extents(not leaving)),
    ]


def _add_content_boxes(page, settings, drawn_parts=frozenset()):
    """Plain test boxes (no bus plan) get one box; real sections get above / below boxes,
    except for parts already drawn for real (main breakers)."""
    half_bundle = settings.main_bus.phase_spacing
    for placed in page.placed_sections:
        box = placed.section
        left, right = content_left_x(placed, settings), placed.component_right_x
        if box.bus is None:
            drawn_here = any((placed.number, part) in drawn_parts for part in ("above", "below"))
            if box.width > 0 and box.height > 0 and not drawn_here:   # empty: nothing to show
                page.parts.content_boxes.append(ContentBox(
                    placed.number, "above", left, placed.component_bottom_y, right,
                    placed.component_top_y))
            continue
        bus_y = box.bus.body_y
        if box.above_height > 0 and (placed.number, "above") not in drawn_parts:
            page.parts.content_boxes.append(ContentBox(
                placed.number, "above", left, bus_y + half_bundle, right,
                bus_y + half_bundle + box.above_height))
        if box.below_height > 0 and (placed.number, "below") not in drawn_parts:
            page.parts.content_boxes.append(ContentBox(
                placed.number, "below", left, bus_y - half_bundle - box.below_height, right,
                bus_y - half_bundle))


def _add_ground_bus(page, is_last_page, settings):
    ground = settings.ground_bus
    if not page.placed_sections:
        return
    end_x = settings.keepout_left_x - ground.gap_before_title_block
    if is_last_page:
        # Nothing continues past the last section, so the ground bus stops there.
        end_x = min(end_x, page.placed_sections[-1].right_divider_x)
    page.parts.ground_bus = GroundBusLine(start_x=ground.start_x, end_x=end_x, y=ground.y)


def _add_section_labels(page, settings):
    label = settings.section_label
    for placed in page.placed_sections:
        center_x = (placed.left_divider_x + placed.right_divider_x) / 2
        text = label.text_format.format(number=placed.number)
        bottom_y = label.bottom_y
        # Width is estimated (no AutoCAD here), so a label is moved up if its estimated
        # right half reaches over the title block.
        right_end_x = center_x + settings.text.estimated_width(text) / 2
        if right_end_x > settings.keepout_left_x and bottom_y < settings.keepout_height:
            bottom_y = settings.keepout_height + label.gap_above_title_block
        page.parts.section_labels.append(SectionLabel(text, center_x, bottom_y))
