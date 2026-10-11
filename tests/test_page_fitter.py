"""One test (or more) per page-fitting rule in docs/DECISIONS.md.

Settings and helpers are in tests/helpers.py (fixed round numbers, explained there).
"""
import json
from pathlib import Path

import pytest

from src.layout.page_fitter import SectionBox, fit_boxes
from src.layout.settings import SettingsError, load_settings
from tests.helpers import SHORT, TEST_SETTINGS, make_lineup, numbers_per_page


# --- Section edges --------------------------------------------------------------------

def test_section_edges_sit_5_outside_components_and_are_shared():
    board = make_lineup(SectionBox(50, SHORT), SectionBox(50, SHORT))
    page = fit_boxes(board, TEST_SETTINGS).pages[0]
    a, b = page.placed_sections

    assert a.left_divider_x == 10            # standard margin
    assert a.component_left_x == 15          # 5 inside the divider
    assert a.component_right_x == 65
    assert a.right_divider_x == 70
    assert b.left_divider_x == 70            # shared with A
    assert b.component_left_x - a.component_right_x == 10  # 10 between components
    assert page.edge_xs == [10, 70, 130]     # three edges for two sections


# --- Fill left to right, order preserved ----------------------------------------------

def test_pages_fill_left_to_right_in_entered_order():
    # Footprint 100 each: 4 fit in 480, a 5th would need 500 (more than even 490).
    board = make_lineup(*[SectionBox(90, SHORT) for _ in range(6)])
    result = fit_boxes(board, TEST_SETTINGS)
    assert numbers_per_page(result) == [[1, 2, 3, 4], [5, 6]]
    assert result.warnings == []


def test_sections_are_never_reordered_to_fill_gaps():
    # Big (1), big (2), small (3): the small one would fit on page 1 if moved ahead, but order wins.
    board = make_lineup(
        SectionBox(290, SHORT), SectionBox(290, SHORT), SectionBox(50, SHORT)
    )
    result = fit_boxes(board, TEST_SETTINGS)
    assert numbers_per_page(result) == [[1], [2, 3]]


# --- Margin relaxation ----------------------------------------------------------------

def test_relaxed_margin_used_when_it_fits_one_more_section():
    # Footprint 98 each: 5 x 98 = 490. Too wide for 480, exactly fits 490.
    board = make_lineup(*[SectionBox(88, SHORT) for _ in range(5)])
    result = fit_boxes(board, TEST_SETTINGS)
    assert numbers_per_page(result) == [[1, 2, 3, 4, 5]]
    assert result.pages[0].side_margin == 5


def test_standard_margin_kept_when_relaxing_would_not_help():
    # Footprint 99 each: 5 x 99 = 495, too wide even for 490, so the 5th moves on.
    board = make_lineup(*[SectionBox(89, SHORT) for _ in range(5)])
    result = fit_boxes(board, TEST_SETTINGS)
    assert numbers_per_page(result) == [[1, 2, 3, 4], [5]]
    assert result.pages[0].side_margin == 10
    assert result.pages[1].side_margin == 10


# --- Push to next page ----------------------------------------------------------------

def test_push_to_next_page_starts_a_new_page():
    board = make_lineup(
        SectionBox(50, SHORT), SectionBox(50, SHORT, push_to_next_page=True)
    )
    assert numbers_per_page(fit_boxes(board, TEST_SETTINGS)) == [[1], [2]]


def test_push_on_first_section_does_not_create_an_empty_page():
    board = make_lineup(SectionBox(50, SHORT, push_to_next_page=True))
    assert numbers_per_page(fit_boxes(board, TEST_SETTINGS)) == [[1]]


# --- Linked sections ------------------------------------------------------------------

def test_linked_group_moves_to_fresh_page_together():
    # Page 1 holds 300 of footprint. Unlinked, section 3 would join page 1 (400 <= 480) and
    # 4 would go to page 2. Linked, 3 + 4 (200 more = 500) can't fit, so both move.
    board = make_lineup(
        SectionBox(90, SHORT),
        SectionBox(190, SHORT),
        SectionBox(90, SHORT, link_with_next=True),
        SectionBox(90, SHORT),
    )
    result = fit_boxes(board, TEST_SETTINGS)
    assert numbers_per_page(result) == [[1, 2], [3, 4]]
    assert result.warnings == []


def test_linked_group_too_wide_for_any_page_is_placed_alone_with_warning():
    # Three linked sections of footprint 200 = 600, more than any page allows.
    board = make_lineup(
        SectionBox(50, SHORT),
        SectionBox(190, SHORT, link_with_next=True),
        SectionBox(190, SHORT, link_with_next=True),
        SectionBox(190, SHORT),
        SectionBox(50, SHORT),
    )
    result = fit_boxes(board, TEST_SETTINGS)
    assert numbers_per_page(result) == [[1], [2, 3, 4], [5]]
    # (The overflow page also gets page-part warnings; only the fitting warning matters here.)
    assert sum("do not fit together" in w for w in result.warnings) == 1


def test_push_inside_a_linked_group_is_ignored_with_warning():
    board = make_lineup(
        SectionBox(50, SHORT, link_with_next=True),
        SectionBox(50, SHORT, push_to_next_page=True),
    )
    result = fit_boxes(board, TEST_SETTINGS)
    assert numbers_per_page(result) == [[1, 2]]
    assert "ignored" in result.warnings[0]


# --- Oversized sections ---------------------------------------------------------------

def test_section_wider_than_page_warns_and_gets_its_own_page():
    board = make_lineup(
        SectionBox(50, SHORT), SectionBox(600, SHORT), SectionBox(50, SHORT)
    )
    result = fit_boxes(board, TEST_SETTINGS)
    assert numbers_per_page(result) == [[1], [2], [3]]
    assert len(result.warnings) == 1
    assert "wider than a page" in result.warnings[0]


def test_section_taller_than_page_warns():
    # Room between standard top and bottom margins = 300 - 20 = 280.
    board = make_lineup(SectionBox(50, 281))
    result = fit_boxes(board, TEST_SETTINGS)
    assert any("taller than a page" in w for w in result.warnings)


def test_section_exactly_page_height_is_fine():
    board = make_lineup(SectionBox(50, 280))
    assert fit_boxes(board, TEST_SETTINGS).warnings == []


# --- Title block keep-out -------------------------------------------------------------

def test_section_reaching_into_title_block_moves_to_next_page():
    # Height 250 hangs from y 290 down to y 40, below the keep-out top (100).
    # Sections 1-3 end at x 310. Section 4 would span x 310-410, which crosses x 400 -> next page.
    board = make_lineup(*[SectionBox(90, 250) for _ in range(4)])
    result = fit_boxes(board, TEST_SETTINGS)
    assert numbers_per_page(result) == [[1, 2, 3], [4]]
    assert result.warnings == []


def test_short_section_over_title_block_x_range_is_fine():
    # Height 190 hangs from y 290 to y 100: exactly touching the keep-out top is allowed.
    board = make_lineup(*[SectionBox(90, 190) for _ in range(4)])
    assert numbers_per_page(fit_boxes(board, TEST_SETTINGS)) == [[1, 2, 3, 4]]


def test_section_that_hits_title_block_even_alone_warns():
    # Footprint 450 from x 10 to 460 crosses x 400; height 250 reaches below y 100.
    board = make_lineup(SectionBox(440, 250))
    result = fit_boxes(board, TEST_SETTINGS)
    assert numbers_per_page(result) == [[1]]
    assert any("title block" in w for w in result.warnings)


# --- Settings file --------------------------------------------------------------------

REAL_SETTINGS_FILE = Path(__file__).resolve().parent.parent / "config" / "layout_settings.json"


def write_broken_copy(tmp_path, group, key, new_value=None, remove=False):
    """Copy the real settings file with one value changed or removed."""
    data = json.loads(REAL_SETTINGS_FILE.read_text(encoding="utf-8"))
    if remove:
        del data[group][key]
    else:
        data[group][key] = new_value
    bad_file = tmp_path / "layout_settings.json"
    bad_file.write_text(json.dumps(data))
    return bad_file


def test_real_settings_file_loads():
    settings = load_settings(REAL_SETTINGS_FILE)
    assert settings.drawable_width > 0


def test_missing_setting_gives_clear_error(tmp_path):
    bad_file = write_broken_copy(tmp_path, "page", "drawable_width", remove=True)
    with pytest.raises(SettingsError, match="page.drawable_width"):
        load_settings(bad_file)


def test_non_number_setting_gives_clear_error(tmp_path):
    bad_file = write_broken_copy(tmp_path, "ground_bus", "y", new_value="low")
    with pytest.raises(SettingsError, match="ground_bus.y.*must be a number"):
        load_settings(bad_file)


def test_section_label_format_needs_number_placeholder(tmp_path):
    bad_file = write_broken_copy(tmp_path, "section_label", "text_format", new_value="SECTION")
    with pytest.raises(SettingsError, match="{number}"):
        load_settings(bad_file)
