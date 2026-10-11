"""Tests for the main bus height rule (docs/DECISIONS.md, "Main bus height").

Test numbers (tests/helpers.py): content between y 30 and 280, phases 5 apart (so the bus
B phase is 5 above the lowest content when nothing is below it), step adds 10 width,
a tie moves the bus 70. Placeholders: main 75 tall, single breaker 45 tall.
"""
from src.layout.page_fitter import fit_pages
from src.model.section_contents import (
    Breaker, GroupMounted, MainBreaker, SectionContents, SingleBreaker, SingleLevel, TieBreaker,
)
from src.model.switchboard import Section, Switchboard
from tests.helpers import TEST_SETTINGS


def section(above=None, below=None, tie=None):
    return Section(SectionContents(above=above, below=below, tie=tie))


def main():
    return MainBreaker(Breaker("52-M"))


def single():
    return SingleBreaker(Breaker("52-F"))


def group(levels):
    # gap 15 + (levels - 1) x 25 + level 10 + overhang 10
    return GroupMounted([SingleLevel(Breaker(f"52-F{n}")) for n in range(levels)])


def bus_plans(*sections):
    result = fit_pages(Switchboard("Test", list(sections)), TEST_SETTINGS)
    boxes = [p.section for page in result.pages for p in page.placed_sections]
    return [box.bus for box in boxes], boxes, result.warnings


def test_bus_starts_as_low_as_possible():
    plans, _, _ = bus_plans(section(above=main()))
    assert plans[0].body_y == 30 + 5           # nothing below: C phase sits on y 30


def test_part_below_pushes_the_bus_up():
    plans, _, _ = bus_plans(section(above=main(), below=single()))
    assert plans[0].body_y == 30 + 45 + 5


def test_bus_stays_level_when_it_can():
    # Section 2 has nothing below; the bus does not drop back down for it.
    plans, boxes, _ = bus_plans(section(below=single()), section(above=main()))
    assert plans[0].body_y == plans[1].body_y == 80
    assert not plans[1].steps_at_entry
    assert boxes[1].width == 30                 # no step, no extra width


def test_bigger_part_below_moves_the_bus_up_and_that_section_takes_the_step():
    # Section 2's group (5 levels: 15 + 4x25 + 10 + 10 = 135 tall) needs the bus higher.
    plans, boxes, _ = bus_plans(section(above=main()), section(below=group(5)))
    assert plans[0].body_y == 35
    assert plans[1].body_y == 30 + 135 + 5
    assert plans[1].steps_at_entry
    assert boxes[1].width == 145 + 10           # group width + step


def test_tall_part_above_pushes_the_bus_down_only_as_far_as_needed():
    # Section 1 lifts the bus to 170 (group of 5 below). Section 2 has a group of 8 above
    # (15 + 7x25 + 10 + 10 = 210), so the bus can be at most 280 - 5 - 210 = 65.
    plans, _, _ = bus_plans(section(below=group(5)), section(above=group(8)))
    assert plans[0].body_y == 170
    assert plans[1].body_y == 65
    assert plans[1].steps_at_entry


def test_tie_breaker_moves_the_bus_as_it_leaves_its_section():
    plans, _, _ = bus_plans(
        section(above=main(), tie=TieBreaker(Breaker("52-T"), bus_steps="up")),
        section(above=single()),
    )
    assert (plans[0].body_y, plans[0].exit_y) == (35, 105)
    assert plans[1].entry_y == plans[1].body_y == 105   # next section just carries on


def test_section_too_tall_for_the_page_warns():
    # Groups of 8 above and 3 below: 210 + 10 + (15 + 2x25 + 20 = 85) = 305 > 250.
    _, _, warnings = bus_plans(section(above=group(8), below=group(3)))
    assert any("Section 1 is too tall" in w for w in warnings)


def test_bus_path_steps_inside_the_section_that_needs_it():
    # Section 1 (main above, 30 wide) spans 10-50. Section 2 (group of 5 below, 145 + 10
    # step wide) spans 50-215; its step zone is 55-65, so the bus rises at x 60.
    result = fit_pages(Switchboard("Test", [section(above=main()), section(below=group(5))]),
                       TEST_SETTINGS)
    assert result.pages[0].parts.bus_path == [
        (10, 35), (50, 35),     # through section 1, level
        (60, 35), (60, 170),    # rises in section 2's step zone
        (215, 170),             # on through section 2
    ]


def test_tie_stepping_the_bus_off_the_usable_height_warns():
    # Bus starts at 35 (lowest); stepping down 70 would put it at -35.
    _, _, warnings = bus_plans(
        section(above=main(), tie=TieBreaker(Breaker("52-T"), bus_steps="down")),
    )
    assert any("Section 1: the tie breaker steps the bus down" in w for w in warnings)
