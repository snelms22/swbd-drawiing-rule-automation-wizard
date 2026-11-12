"""Tests for the AutoCAD step that don't need AutoCAD: the shapes each page turns into,
the frame check, the output file name, and the AutoCAD settings file."""
import json
from datetime import datetime
from pathlib import Path

import pytest

from src.autocad.draw_page import Line, Polyline, Text, page_shapes, phase_paths
from src.autocad.generate import GenerateError, check_frames, output_file_name
from src.autocad.settings import load_autocad_settings
from src.layout.page_fitter import fit_pages
from src.layout.settings import SettingsError
from src.model.section_contents import Breaker, GroupMounted, MainBreaker, SectionContents, SingleLevel
from src.model.switchboard import Section, Switchboard
from tests.helpers import TEST_SETTINGS

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REAL_AUTOCAD_SETTINGS = PROJECT_ROOT / "config" / "autocad_settings.json"


def autocad_settings():
    return load_autocad_settings(REAL_AUTOCAD_SETTINGS, PROJECT_ROOT)


# --- Bus phases -----------------------------------------------------------------------

def test_straight_bus_phases_are_5_apart_with_a_on_top():
    paths = phase_paths([(10, 100), (200, 100)], 5)
    assert paths["A"] == [(10, 105), (200, 105)]
    assert paths["B"] == [(10, 100), (200, 100)]
    assert paths["C"] == [(10, 95), (200, 95)]


def test_rising_step_keeps_phases_parallel_with_a_on_the_left():
    paths = phase_paths([(10, 35), (60, 35), (60, 170), (215, 170)], 5)
    assert paths["A"] == [(10, 40), (55, 40), (55, 175), (215, 175)]
    assert paths["C"] == [(10, 30), (65, 30), (65, 165), (215, 165)]


def test_repeated_points_are_ignored():
    paths = phase_paths([(10, 35), (50, 35), (50, 35), (60, 35)], 5)
    assert paths["B"] == [(10, 35), (50, 35), (60, 35)]


# --- Page shapes ----------------------------------------------------------------------

def sample_page():
    board = Switchboard("Test", [
        Section(SectionContents(above=MainBreaker(Breaker("52-M")))),
        Section(SectionContents(below=GroupMounted([SingleLevel(Breaker("52-F1"))]))),
    ])
    return fit_pages(board, TEST_SETTINGS).pages[0]


def test_page_shapes_are_on_the_right_layers():
    shapes = page_shapes(sample_page(), TEST_SETTINGS, "CFG_PLACEHOLDER")
    layers = {(type(s).__name__, s.layer) for s in shapes}
    assert ("Polyline", "BUS") in layers
    assert ("Line", "DEVIDER") in layers
    assert ("Line", "GROUND") in layers
    assert ("Text", "0") in layers
    assert ("Polyline", "CFG_PLACEHOLDER") in layers


def test_three_bus_lines_one_per_phase():
    bus = [s for s in page_shapes(sample_page(), TEST_SETTINGS, "P") if s.layer == "BUS"]
    assert len(bus) == 3


def test_section_labels_and_ground_text():
    texts = [s for s in page_shapes(sample_page(), TEST_SETTINGS, "P") if isinstance(s, Text)]
    assert [(t.text, t.align) for t in texts] == [
        ("GROUND BUS", "bottom_left"),
        ("SECTION 1", "bottom_center"),
        ("SECTION 2", "bottom_center"),
        ("{\\LTHREE-LINE DIAGRAM 01}", "middle_right"),        # the page title (2026-11-09)
    ]
    assert all(t.height == 1.25 and t.style == "Hyper_Text" for t in texts[:-1])
    title = texts[-1]
    assert (title.position, title.height, title.layer) == ((390.0, 5.0), 3.0, "0")


def test_one_placeholder_rectangle_per_content_box():
    rectangles = [s for s in page_shapes(sample_page(), TEST_SETTINGS, "P")
                  if isinstance(s, Polyline) and s.layer == "P"]
    assert len(rectangles) == 2          # section 1 above, section 2 below
    assert all(r.closed and len(r.points) == 4 for r in rectangles)


def test_ground_symbol_has_stem_and_three_bars():
    ground_lines = [s for s in page_shapes(sample_page(), TEST_SETTINGS, "P")
                    if isinstance(s, Line) and s.layer == "GROUND"]
    assert len(ground_lines) == 1 + 1 + 3     # bus line, stem, bars


# --- Frames ---------------------------------------------------------------------------

def test_pages_map_to_es_frames():
    frames = [("ES_01", -100.0, -50.0), ("ES_02", 533.57, -50.0), ("EO_01", 0.0, 0.0)]
    assert check_frames(frames, 2, autocad_settings()) == {1: (-100.0, -50.0), 2: (533.57, -50.0)}


def test_missing_frame_stops_with_clear_message():
    with pytest.raises(GenerateError, match="no frame named ES_02"):
        check_frames([("ES_01", 0.0, 0.0)], 2, autocad_settings())


def test_duplicate_frame_stops():
    with pytest.raises(GenerateError, match='more than one frame named "ES_01"'):
        check_frames([("ES_01", 0.0, 0.0), ("ES_01", 5.0, 5.0)], 1, autocad_settings())


# --- File name and settings -----------------------------------------------------------

def test_output_file_name_has_name_and_time_and_no_bad_characters():
    name = output_file_name('BC-HDP-1 "Main"', datetime(2026, 10, 11, 14, 5, 9))
    assert name == "BC-HDP-1 _Main_ 2026-10-11 140509.dwg"


def test_real_autocad_settings_load():
    settings = autocad_settings()
    assert settings.frame_name(1) == "ES_01"
    assert settings.template_file.name == "HYPER_A.dwt"


def test_autocad_electrical_is_refused(tmp_path):
    data = json.loads(REAL_AUTOCAD_SETTINGS.read_text(encoding="utf-8"))
    data["autocad_program_id"] = "AutoCADElectrical.Application"
    bad = tmp_path / "autocad_settings.json"
    bad.write_text(json.dumps(data))
    with pytest.raises(SettingsError, match="Electrical"):
        load_autocad_settings(bad, PROJECT_ROOT)


def test_pages_are_numbered_in_tab_order_toc_first():
    # The rule of the engineers' NumberByLayout.lsp (decision 2026-11-10).
    numbers = autocad_settings().page_numbers(page_count=3)
    assert numbers == {"TOC_01": "01", "LEG_01": "02", "BOM_01": "03",
                       "ES_01": "04", "ES_02": "05", "ES_03": "06"}


def test_page_numbers_agree_with_the_sheet_references():
    # ES_01 is SHEET 4 in the TO / FROM labels, so its frame must say 04.
    from src.layout.settings import load_settings
    layout_settings = load_settings(PROJECT_ROOT / "config" / "layout_settings.json")
    numbers = autocad_settings().page_numbers(page_count=5)
    for page in range(1, 6):
        assert int(numbers[f"ES_{page:02d}"]) == layout_settings.device_pages.sheet_number(page)


def test_a_kept_layout_needs_its_frame(tmp_path):
    data = json.loads(REAL_AUTOCAD_SETTINGS.read_text(encoding="utf-8"))
    del data["keep_layout_frames"]["LEG_ES"]
    bad = tmp_path / "autocad_settings.json"
    bad.write_text(json.dumps(data))
    with pytest.raises(SettingsError, match="LEG_ES"):
        load_autocad_settings(bad, PROJECT_ROOT)
