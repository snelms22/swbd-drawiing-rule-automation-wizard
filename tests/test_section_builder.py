"""Tests for section contents and their sizes (docs/DECISIONS.md, 2026-10-09).

Test numbers (tests/helpers.py): group mounted gap 15, pitch 25, level 10, overhang 10,
first single level on the left. Placeholders: main 30 x 75, single 30 x 45,
group mounted 145 wide, tie 30 wide.
"""
from src.layout.page_fitter import fit_pages
from src.layout.section_builder import section_size, single_level_sides
from src.model.switchboard import Section, Switchboard
from src.model.section_contents import (
    Breaker, GroupMounted, MainBreaker, SectionContents, SingleBreaker, SingleLevel, Provision,
    TieBreaker, TwinLevel,
)
from tests.helpers import TEST_SETTINGS


def bkr(label):
    return Breaker(label)


# --- Sizes ----------------------------------------------------------------------------

def test_empty_section_has_no_size():
    size = section_size(SectionContents(), TEST_SETTINGS)
    assert (size.width, size.above_height, size.below_height) == (0, 0, 0)


def test_main_above_nothing_below():
    size = section_size(SectionContents(above=MainBreaker(bkr("52-M1"))), TEST_SETTINGS)
    assert (size.width, size.above_height, size.below_height) == (30, 75, 0)


def test_main_on_one_side_feeders_on_the_other():
    contents = SectionContents(
        above=MainBreaker(bkr("52-M1")),
        below=GroupMounted([TwinLevel(bkr("52-F1"), bkr("52-F2"))]),
    )
    size = section_size(contents, TEST_SETTINGS)
    assert size.width == 145                 # the wider of the two
    assert size.above_height == 75
    assert size.below_height == 15 + 10 + 10  # gap + one level + overhang


def test_group_height_grows_by_one_pitch_per_level():
    group = GroupMounted([SingleLevel(bkr(f"52-F{n}")) for n in range(1, 6)])
    size = section_size(SectionContents(above=group), TEST_SETTINGS)
    assert size.above_height == 15 + 4 * 25 + 10 + 10   # = 135


def test_single_breaker_below():
    size = section_size(SectionContents(below=SingleBreaker(bkr("52-F1"))), TEST_SETTINGS)
    assert (size.above_height, size.below_height) == (0, 45)


def test_tie_breaker_can_join_any_section():
    contents = SectionContents(above=SingleBreaker(bkr("52-F1")), tie=TieBreaker(bkr("52-T1")))
    size = section_size(contents, TEST_SETTINGS)
    assert size.width == 30 + 30             # placeholder: tie sits beside the feeder


def test_page_fitting_uses_sizes_worked_out_from_contents():
    # Main above (30 wide, 75 tall) and a single breaker below (45 tall).
    board = Switchboard("Test", [Section(SectionContents(
        above=MainBreaker(bkr("52-M1")), below=SingleBreaker(bkr("52-F1")),
    ))])
    placed = fit_pages(board, TEST_SETTINGS).pages[0].placed_sections[0]
    assert placed.component_right_x - placed.component_left_x == 30
    # Bus as low as possible: the bottom sits on the lowest allowed y (30); the top is
    # 45 below + 10 for the bus (A to C) + 75 above higher.
    assert placed.component_bottom_y == 30
    assert placed.component_top_y == 30 + 45 + 10 + 75


def test_empty_section_gets_no_warning():
    board = Switchboard("Test", [Section()])
    assert fit_pages(board, TEST_SETTINGS).warnings == []


# --- Single-mount sides ---------------------------------------------------------------

def test_single_levels_alternate_starting_left():
    group = GroupMounted([SingleLevel(bkr("A")), SingleLevel(bkr("B")), SingleLevel(bkr("C"))])
    assert single_level_sides(group, TEST_SETTINGS) == ["left", "right", "left"]


def test_twin_levels_have_no_side_and_do_not_break_the_alternation():
    # Like ES_12 above the bus: twin, twin (SPACE | F4), then singles F3, F2, F1.
    group = GroupMounted([
        TwinLevel(bkr("F5"), bkr("F6")),
        TwinLevel(Provision("3VA41"), bkr("F4")),
        SingleLevel(bkr("F3")),
        SingleLevel(bkr("F2")),
        SingleLevel(bkr("F1")),
    ])
    assert single_level_sides(group, TEST_SETTINGS) == [None, None, "left", "right", "left"]


def test_flipping_one_level_only_changes_that_level():
    group = GroupMounted([
        SingleLevel(bkr("A")),
        SingleLevel(bkr("B"), flipped=True),
        SingleLevel(bkr("C")),
    ])
    assert single_level_sides(group, TEST_SETTINGS) == ["left", "left", "left"]
