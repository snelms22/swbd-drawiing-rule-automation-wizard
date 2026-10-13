"""Tests for splitting group-mounted feeders that are too tall for the page
(docs/DECISIONS.md, 2026-10-13 "Too tall: split the part below the main bus first").

Test numbers (tests/helpers.py): content between y 30 and 280, bus 10 thick, so the room
for above + below is 240. Group spacing: gap 15, pitch 25, level 10, overhang 10, so a
column of n levels on the main bus is 35 + 25(n - 1) tall. A continuation column starts
15 from the bus and its bus runs 10 before the first level: 45 + 25(n - 1).
Columns 100 apart (A to A), at least 10 between neighbouring breakers. Feeder block
reaches 23 out from its connections; taps 10. Bracket 2 past the tilde.
"""
from dataclasses import replace

from src.layout.page_fitter import fit_pages
from src.layout.section_builder import plan_columns
from src.model.section_contents import Breaker, GroupMounted, SectionContents, TwinLevel
from src.model.switchboard import Section, Switchboard
from tests.helpers import TEST_CATALOG, TEST_SETTINGS

FEEDER = TEST_CATALOG["TEST_FEEDER"]


def twins(count):
    return GroupMounted([TwinLevel(Breaker(f"52-L{n}"), Breaker(f"52-R{n}")) for n in range(count)])


def columns(plan):
    return [(column.above, column.below) for column in plan.columns]


def test_no_split_when_both_parts_fit():
    # 7 above (185) + 1 below (35) = 220 <= 240.
    plan = plan_columns(SectionContents(above=twins(7), below=twins(1)), TEST_SETTINGS, FEEDER)
    assert columns(plan) == [([0, 1, 2, 3, 4, 5, 6], [0])]


def test_part_below_is_split_and_continues_in_a_column_beside_it():
    # 7 above (185) + 2 below (60) = 245 > 240. The above part keeps its room; below gets
    # 240 - 185 = 55: one level on column 1 (35), the other on column 2 (45).
    plan = plan_columns(SectionContents(above=twins(7), below=twins(2)), TEST_SETTINGS, FEEDER)
    assert columns(plan) == [([0, 1, 2, 3, 4, 5, 6], [0]), ([], [1])]
    assert (plan.above_height, plan.below_height) == (185, 45)


def test_part_above_is_split_only_when_it_alone_is_too_tall():
    # 10 above (260) can't fit even with only the below part's one level (35) left:
    # above gets 205, so 7 levels (185) on column 1 and the other 3 on column 2.
    plan = plan_columns(SectionContents(above=twins(10), below=twins(1)), TEST_SETTINGS, FEEDER)
    assert columns(plan) == [([0, 1, 2, 3, 4, 5, 6], [0]), ([7, 8, 9], [])]


def test_columns_are_one_pitch_apart_when_the_breakers_clear():
    # Column 1: breakers reach 23 + tap 10 on the left, so A is 33 from the content edge.
    # Column 2 is 100 further. Needed: 10 (bus) + 33 + 10 + 33 = 86 < 100.
    plan = plan_columns(SectionContents(above=twins(7), below=twins(2)), TEST_SETTINGS, FEEDER)
    assert plan.a_offsets == [33, 133]
    assert plan.width == 133 + 10 + 33


def test_columns_move_apart_when_the_pitch_is_too_small_for_the_breakers():
    settings = replace(TEST_SETTINGS,
                       group_mounted=replace(TEST_SETTINGS.group_mounted, column_pitch=50.0))
    plan = plan_columns(SectionContents(above=twins(7), below=twins(2)), settings, FEEDER)
    assert plan.a_offsets == [33, 33 + 86]


def test_split_column_is_cut_and_continued_with_break_blocks():
    board = Switchboard("Test", [Section(SectionContents(above=twins(7), below=twins(2)))])
    result = fit_pages(board, TEST_SETTINGS, TEST_CATALOG)
    page = result.pages[0]
    assert any(w.startswith("NOTICE: Section 1 is too tall") for w in result.warnings)
    # Bus B at 80 (as low as the 45 below allows), C at 75. Content starts at x 15, so
    # column 1's A is at x 48 and column 2's at x 148.
    blocks = [(b.block, b.position, b.visibility) for b in page.parts.blocks
              if b.block in ("TEST_TILDE", "TEST_BRACKET")]
    assert blocks == [
        # Column 1 below: level A 15 below C (y 60), C at 50, cut 10 further down at 40.
        ("TEST_TILDE", (48, 40), "VERTICAL"), ("TEST_BRACKET", (53, 38), "HORIZONTAL BRACKET"),
        # Column 2 starts 15 below the main bus (y 60), bracket on the bus side.
        ("TEST_TILDE", (148, 60), "VERTICAL"), ("TEST_BRACKET", (153, 62), "HORIZONTAL BRACKET"),
    ]
    labels = [b.attributes for b in page.parts.blocks if b.block == "TEST_BRACKET"]
    assert labels == [{"HORIZONTAL_LABLE": "BUS CONTINUES"}, {"HORIZONTAL_LABLE": "FROM BELOW"}]
    # Column 2's bus runs from its start (60) to 10 past its level (A 50, C 40): y 30.
    column_2 = [(l.start, l.end) for l in page.parts.bus_lines if l.start[0] == l.end[0] == 148]
    assert column_2 == [((148, 60), (148, 30))]
    # Its breakers hang off it, not off the main bus: no dot on the main bus at x 148.
    dots = {b.position for b in page.parts.blocks if b.block == "BUS_NODE"}
    assert (148, 85) not in dots and (148, 50) in dots
