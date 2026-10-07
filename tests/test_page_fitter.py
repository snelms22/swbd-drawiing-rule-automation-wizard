"""One test (or more) per page-fitting rule in docs/DECISIONS.md.

These tests use their own fixed settings (TEST_SETTINGS), not config/layout_settings.json,
so editing the config file can never break them. The numbers match today's placeholders
to keep the arithmetic easy to follow:

    page 500 wide x 300 tall, margins 10 standard / 5 relaxed, divider clearance 5,
    title block keep-out 100 x 100 in the bottom-right corner.

Useful facts for reading the tests:
- A section's footprint on the page = width + 10 (5 clearance each side).
- Room between standard margins = 480. Between relaxed margins = 490.
- Sections hang from y = 290 (top margin). The keep-out covers x 400-500, y 0-100.
"""
from pathlib import Path

import pytest

from src.layout.page_fitter import fit_pages
from src.layout.settings import LayoutSettings, SettingsError, load_settings
from src.model.switchboard import Section, Switchboard

TEST_SETTINGS = LayoutSettings(
    drawable_width=500.0,
    drawable_height=300.0,
    margin_standard=10.0,
    margin_relaxed=5.0,
    divider_clearance=5.0,
    keepout_width=100.0,
    keepout_height=100.0,
)

SHORT = 50.0  # tall enough to see, short enough to never reach the title block


def make_board(*sections):
    return Switchboard(name="Test", sections=list(sections))


def names_per_page(result):
    return [[p.section.name for p in page.placed_sections] for page in result.pages]


# --- Dividing lines -------------------------------------------------------------------

def test_dividers_sit_5_outside_components_and_are_shared():
    board = make_board(Section("A", 50, SHORT), Section("B", 50, SHORT))
    page = fit_pages(board, TEST_SETTINGS).pages[0]
    a, b = page.placed_sections

    assert a.left_divider_x == 10            # standard margin
    assert a.component_left_x == 15          # 5 inside the divider
    assert a.component_right_x == 65
    assert a.right_divider_x == 70
    assert b.left_divider_x == 70            # shared with A
    assert b.component_left_x - a.component_right_x == 10  # 10 between components
    assert page.divider_xs == [10, 70, 130]  # three lines for two sections


# --- Fill left to right, order preserved ----------------------------------------------

def test_pages_fill_left_to_right_in_entered_order():
    # Footprint 100 each: 4 fit in 480, a 5th would need 500 (more than even 490).
    board = make_board(*[Section(f"S{i}", 90, SHORT) for i in range(1, 7)])
    result = fit_pages(board, TEST_SETTINGS)
    assert names_per_page(result) == [["S1", "S2", "S3", "S4"], ["S5", "S6"]]
    assert result.warnings == []


def test_sections_are_never_reordered_to_fill_gaps():
    # Big, big, small: the small one would fit on page 1 if moved ahead, but order wins.
    board = make_board(
        Section("Big1", 290, SHORT), Section("Big2", 290, SHORT), Section("Small", 50, SHORT)
    )
    result = fit_pages(board, TEST_SETTINGS)
    assert names_per_page(result) == [["Big1"], ["Big2", "Small"]]


# --- Margin relaxation ----------------------------------------------------------------

def test_relaxed_margin_used_when_it_fits_one_more_section():
    # Footprint 98 each: 5 x 98 = 490. Too wide for 480, exactly fits 490.
    board = make_board(*[Section(f"S{i}", 88, SHORT) for i in range(1, 6)])
    result = fit_pages(board, TEST_SETTINGS)
    assert names_per_page(result) == [["S1", "S2", "S3", "S4", "S5"]]
    assert result.pages[0].side_margin == 5


def test_standard_margin_kept_when_relaxing_would_not_help():
    # Footprint 99 each: 5 x 99 = 495, too wide even for 490, so the 5th moves on.
    board = make_board(*[Section(f"S{i}", 89, SHORT) for i in range(1, 6)])
    result = fit_pages(board, TEST_SETTINGS)
    assert names_per_page(result) == [["S1", "S2", "S3", "S4"], ["S5"]]
    assert result.pages[0].side_margin == 10
    assert result.pages[1].side_margin == 10


# --- Push to next page ----------------------------------------------------------------

def test_push_to_next_page_starts_a_new_page():
    board = make_board(
        Section("A", 50, SHORT), Section("B", 50, SHORT, push_to_next_page=True)
    )
    assert names_per_page(fit_pages(board, TEST_SETTINGS)) == [["A"], ["B"]]


def test_push_on_first_section_does_not_create_an_empty_page():
    board = make_board(Section("A", 50, SHORT, push_to_next_page=True))
    assert names_per_page(fit_pages(board, TEST_SETTINGS)) == [["A"]]


# --- Linked sections ------------------------------------------------------------------

def test_linked_group_moves_to_fresh_page_together():
    # Page 1 holds 300 of footprint. Unlinked, C would join page 1 (400 <= 480) and D
    # would go to page 2. Linked, C + D (200 more = 500) can't fit, so both move.
    board = make_board(
        Section("A", 90, SHORT),
        Section("B", 190, SHORT),
        Section("C", 90, SHORT, link_with_next=True),
        Section("D", 90, SHORT),
    )
    result = fit_pages(board, TEST_SETTINGS)
    assert names_per_page(result) == [["A", "B"], ["C", "D"]]
    assert result.warnings == []


def test_linked_group_too_wide_for_any_page_is_placed_alone_with_warning():
    # Three linked sections of footprint 200 = 600, more than any page allows.
    board = make_board(
        Section("A", 50, SHORT),
        Section("L1", 190, SHORT, link_with_next=True),
        Section("L2", 190, SHORT, link_with_next=True),
        Section("L3", 190, SHORT),
        Section("Z", 50, SHORT),
    )
    result = fit_pages(board, TEST_SETTINGS)
    assert names_per_page(result) == [["A"], ["L1", "L2", "L3"], ["Z"]]
    assert len(result.warnings) == 1
    assert "do not fit together" in result.warnings[0]


def test_push_inside_a_linked_group_is_ignored_with_warning():
    board = make_board(
        Section("A", 50, SHORT, link_with_next=True),
        Section("B", 50, SHORT, push_to_next_page=True),
    )
    result = fit_pages(board, TEST_SETTINGS)
    assert names_per_page(result) == [["A", "B"]]
    assert "ignored" in result.warnings[0]


# --- Oversized sections ---------------------------------------------------------------

def test_section_wider_than_page_warns_and_gets_its_own_page():
    board = make_board(
        Section("A", 50, SHORT), Section("Huge", 600, SHORT), Section("B", 50, SHORT)
    )
    result = fit_pages(board, TEST_SETTINGS)
    assert names_per_page(result) == [["A"], ["Huge"], ["B"]]
    assert len(result.warnings) == 1
    assert "wider than a page" in result.warnings[0]


def test_section_taller_than_page_warns():
    # Room between standard top and bottom margins = 300 - 20 = 280.
    board = make_board(Section("Tall", 50, 281))
    result = fit_pages(board, TEST_SETTINGS)
    assert any("taller than a page" in w for w in result.warnings)


def test_section_exactly_page_height_is_fine():
    board = make_board(Section("JustFits", 50, 280))
    assert fit_pages(board, TEST_SETTINGS).warnings == []


# --- Title block keep-out -------------------------------------------------------------

def test_section_reaching_into_title_block_moves_to_next_page():
    # Height 250 hangs from y 290 down to y 40, below the keep-out top (100).
    # S1-S3 end at x 310. S4 would span x 310-410, which crosses x 400 -> next page.
    board = make_board(*[Section(f"S{i}", 90, 250) for i in range(1, 5)])
    result = fit_pages(board, TEST_SETTINGS)
    assert names_per_page(result) == [["S1", "S2", "S3"], ["S4"]]
    assert result.warnings == []


def test_short_section_over_title_block_x_range_is_fine():
    # Height 190 hangs from y 290 to y 100: exactly touching the keep-out top is allowed.
    board = make_board(*[Section(f"S{i}", 90, 190) for i in range(1, 5)])
    assert names_per_page(fit_pages(board, TEST_SETTINGS)) == [["S1", "S2", "S3", "S4"]]


def test_section_that_hits_title_block_even_alone_warns():
    # Footprint 450 from x 10 to 460 crosses x 400; height 250 reaches below y 100.
    board = make_board(Section("Wide", 440, 250))
    result = fit_pages(board, TEST_SETTINGS)
    assert names_per_page(result) == [["Wide"]]
    assert any("title block" in w for w in result.warnings)


# --- Settings file --------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_real_settings_file_loads():
    settings = load_settings(PROJECT_ROOT / "config" / "layout_settings.json")
    assert settings.drawable_width > 0


def test_missing_setting_gives_clear_error(tmp_path):
    bad_file = tmp_path / "layout_settings.json"
    bad_file.write_text('{"page": {}, "section": {}, "title_block_keepout": {"corner": "bottom_right"}}')
    with pytest.raises(SettingsError, match="page.drawable_width"):
        load_settings(bad_file)


def test_non_number_setting_gives_clear_error(tmp_path):
    bad_file = tmp_path / "layout_settings.json"
    bad_file.write_text(
        '{"page": {"drawable_width": "wide", "drawable_height": 300, "margin_standard": 10,'
        ' "margin_relaxed": 5}, "section": {"divider_clearance": 5},'
        ' "title_block_keepout": {"corner": "bottom_right", "width": 100, "height": 100}}'
    )
    with pytest.raises(SettingsError, match="must be a number"):
        load_settings(bad_file)
