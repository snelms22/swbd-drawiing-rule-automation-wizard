"""Tests for the page parts: dividers, ground bus, section labels (docs/DECISIONS.md,
2026-10-09). Settings and helpers are in tests/helpers.py.

Reminder: sections of width 90 have footprint 100. Four of them fill x 10-410 on one page
(a fifth needs 500, more than the 490 a page allows). The title block starts at x 400.
"""
from src.layout.page_fitter import SectionBox, fit_boxes
from tests.helpers import SHORT, TEST_SETTINGS, make_lineup, numbers_per_page


def divider_xs(page):
    return [line.x for line in page.parts.dividers]


# --- Dividers -------------------------------------------------------------------------

def test_one_section_has_no_dividers():
    page = fit_boxes(make_lineup(SectionBox(50, SHORT)), TEST_SETTINGS).pages[0]
    assert divider_xs(page) == []


def test_divider_only_between_sections_not_at_start_or_end():
    board = make_lineup(SectionBox(50, SHORT), SectionBox(50, SHORT), SectionBox(50, SHORT))
    page = fit_boxes(board, TEST_SETTINGS).pages[0]
    # Edges are at 10, 70, 130, 190. Only the two inner ones get a line.
    assert divider_xs(page) == [70, 130]


def test_dividers_use_configured_height():
    board = make_lineup(SectionBox(50, SHORT), SectionBox(50, SHORT))
    line = fit_boxes(board, TEST_SETTINGS).pages[0].parts.dividers[0]
    assert (line.bottom_y, line.top_y) == (10, 290)


def test_divider_at_end_of_page_when_lineup_continues():
    # Section 1 (footprint 300), then section 2 (footprint 300) goes to page 2. Section 1's
    # right edge (310) is left of the title block (400), so its divider stays on page 1.
    board = make_lineup(SectionBox(290, SHORT), SectionBox(290, SHORT))
    page1, page2 = fit_boxes(board, TEST_SETTINGS).pages
    assert divider_xs(page1) == [310]
    assert divider_xs(page2) == []


def test_end_of_page_divider_moves_to_next_page_if_it_would_hit_title_block():
    # Four width-90 sections end at x 410, over the title block (starts at 400), so the
    # divider after section 4 can't run down the page there. It goes at the start of page 2.
    board = make_lineup(*[SectionBox(90, SHORT) for _ in range(5)])
    result = fit_boxes(board, TEST_SETTINGS)
    page1, page2 = result.pages
    assert numbers_per_page(result) == [[1, 2, 3, 4], [5]]
    assert divider_xs(page1) == [110, 210, 310]
    assert divider_xs(page2) == [10]


def test_no_divider_after_the_last_section_of_the_lineup():
    board = make_lineup(SectionBox(290, SHORT), SectionBox(290, SHORT))
    last_page = fit_boxes(board, TEST_SETTINGS).pages[-1]
    assert divider_xs(last_page) == []


def test_divider_between_sections_over_title_block_stops_at_its_top():
    # Section 1 spans 10-310, section 2 (footprint 105) spans 310-415, section 3 spans
    # 415-455. The divider between 2 and 3 (x 415) is over the title block (starts at 400).
    board = make_lineup(SectionBox(290, SHORT), SectionBox(95, SHORT), SectionBox(30, SHORT))
    result = fit_boxes(board, TEST_SETTINGS)
    over = [line for line in result.pages[0].parts.dividers if line.x > 400]
    assert len(over) == 1
    assert over[0].bottom_y == 100          # title block top
    assert result.warnings == []            # no warning: this is the agreed rule


# --- Ground bus -----------------------------------------------------------------------

def test_ground_bus_runs_to_just_before_title_block_when_lineup_continues():
    board = make_lineup(SectionBox(290, SHORT), SectionBox(290, SHORT))
    ground = fit_boxes(board, TEST_SETTINGS).pages[0].parts.ground_bus
    assert (ground.start_x, ground.end_x, ground.y) == (7.5, 391, 20)


def test_ground_bus_stops_at_last_section_on_last_page():
    board = make_lineup(SectionBox(50, SHORT))
    ground = fit_boxes(board, TEST_SETTINGS).pages[0].parts.ground_bus
    assert ground.end_x == 70           # section 1's right edge


# --- Section labels -------------------------------------------------------------------

def test_section_labels_are_centred_under_each_section():
    board = make_lineup(SectionBox(50, SHORT), SectionBox(110, SHORT))
    labels = fit_boxes(board, TEST_SETTINGS).pages[0].parts.section_labels
    # Section 1 spans 10-70, section 2 spans 70-190.
    assert [(l.text, l.center_x, l.bottom_y) for l in labels] == [
        ("SECTION 1", 40, 15),
        ("SECTION 2", 130, 15),
    ]


def test_section_numbers_continue_across_pages():
    board = make_lineup(SectionBox(290, SHORT), SectionBox(290, SHORT))
    page1, page2 = fit_boxes(board, TEST_SETTINGS).pages
    assert [l.text for l in page1.parts.section_labels] == ["SECTION 1"]
    assert [l.text for l in page2.parts.section_labels] == ["SECTION 2"]


def test_label_over_title_block_moves_up_to_just_above_it():
    # Section 1 (footprint 310) spans 10-320; section 2 (footprint 170) spans 320-490,
    # centre 405, which is past the title block's left edge (400).
    board = make_lineup(SectionBox(300, SHORT), SectionBox(160, SHORT))
    labels = fit_boxes(board, TEST_SETTINGS).pages[0].parts.section_labels
    assert labels[0].bottom_y == 15          # stays below the ground bus
    assert labels[1].bottom_y == 102         # title block top (100) + gap (2)
    assert labels[1].center_x == 405         # still centred under its section


def test_label_moves_up_if_its_right_half_would_reach_the_title_block():
    # Estimated label width is 9, so a label centred at 396 reaches x 400.5 (moves up);
    # one centred at 395 reaches 399.5 (stays). Section 1 spans 10-310; section 2 spans
    # 310-482 (centre 396) or 310-480 (centre 395).
    reaches = fit_boxes(make_lineup(SectionBox(290, SHORT), SectionBox(162, SHORT)), TEST_SETTINGS)
    clear = fit_boxes(make_lineup(SectionBox(290, SHORT), SectionBox(160, SHORT)), TEST_SETTINGS)
    assert reaches.pages[0].parts.section_labels[1].bottom_y == 102
    assert clear.pages[0].parts.section_labels[1].bottom_y == 15
