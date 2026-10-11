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
class PageParts:
    # Main bus centre line (B phase) as a list of corner points, left to right.
    # A is phase_spacing above / left of it, C the same below / right.
    bus_path: list[tuple[float, float]] = field(default_factory=list)
    dividers: list[DividerLine] = field(default_factory=list)
    ground_bus: GroundBusLine | None = None
    section_labels: list[SectionLabel] = field(default_factory=list)


def add_page_parts(pages, settings):
    """Fill in page.parts for every page."""
    for page in pages:
        page.parts = PageParts()

    _add_dividers(pages, settings)
    for page in pages:
        _add_bus_path(page, settings)
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


def _add_bus_path(page, settings):
    points = page.parts.bus_path
    for placed in page.placed_sections:
        box = placed.section
        plan = box.bus
        if plan is None:          # plain boxes (some tests) have no bus
            continue
        if not points:
            points.append((placed.left_divider_x, plan.entry_y))
        if plan.steps_at_entry:
            step_x = placed.left_divider_x + settings.divider_clearance + settings.main_bus.step_width / 2
            points.append((step_x, plan.entry_y))
            points.append((step_x, plan.body_y))
        if box.has_tie and abs(plan.exit_y - plan.body_y) > ROUNDING_TOLERANCE:
            tie_x = placed.component_right_x - settings.placeholder_sizes.tie_breaker_width / 2
            points.append((tie_x, plan.body_y))
            points.append((tie_x, plan.exit_y))
        points.append((placed.right_divider_x, plan.exit_y))


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
