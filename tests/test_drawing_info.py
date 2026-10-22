"""Tests for General Drawing Information (src/model/drawing_info.py, decisions 2026-10-19/20)."""
from pathlib import Path

from src.model.drawing_info import (
    DrawingInfo, drawing_file_stem, drawing_number, drawing_properties, fgd_number,
    item_name_lines, job_number_problem, load_drawing_info_settings,
)
from src.model.project_file import open_project, save_project
from src.model.section_contents import Breaker, MainBreaker, SectionContents
from src.model.switchboard import Section, Switchboard

SETTINGS = load_drawing_info_settings(Path("config/drawing_info.json"))
LONG_NAME = "SWBD, 5000A, 480V, 100KAIC, TYPE 3R, MA-HDP-E, 3X5000A, 1X2500A, 2X800A"


def board(job="011484", name=LONG_NAME) -> Switchboard:
    return Switchboard("Job", [Section(SectionContents(above=MainBreaker(Breaker("52-M1"))))],
                       drawing_info=DrawingInfo(job_number=job, item_name=name))


def test_a_drawing_needs_a_job_number():
    assert job_number_problem(board(job="")).startswith("Enter the job number")
    assert job_number_problem(board(job="   ")).startswith("Enter the job number")
    assert job_number_problem(board()) == ""


def test_a_short_item_name_stays_on_one_line():
    assert item_name_lines("PNLB, 250A, 480VAC", 44) == ("PNLB, 250A, 480VAC", "")


def test_a_long_item_name_is_split_at_the_comma_nearest_the_middle():
    line_1, line_2 = item_name_lines(LONG_NAME, 44)
    assert line_1 == "SWBD, 5000A, 480V, 100KAIC, TYPE 3R,"
    assert line_2 == "MA-HDP-E, 3X5000A, 1X2500A, 2X800A"


def test_drawing_properties_for_the_template():
    assert drawing_properties(board(), SETTINGS, schematic_pages=2) == {
        "FG NUMBER": "011484",
        "FG DESCRIPTION": "SWBD, 5000A, 480V, 100KAIC, TYPE 3R,",
        "NUMBER OF BREAKERS": "MA-HDP-E, 3X5000A, 1X2500A, 2X800A",
        "TOTAL PAGES ES": "02",
    }


def test_preview_numbers_match_the_template_fields():
    # The drawing builds these itself from FG NUMBER; the app shows the same in its preview.
    assert fgd_number(board(), SETTINGS) == "900-011484"
    numbers = [drawing_number(board(), SETTINGS, kind) for kind in ("EO", "ES", "EW", "TOC")]
    assert numbers == ["EO-011484", "ES-011484", "EW-011484", "ES-011484"]


def test_drawing_is_named_after_the_job_number():
    assert drawing_file_stem(board(), SETTINGS) == "011484"
    assert drawing_file_stem(board(job=""), SETTINGS) is None


def test_drawing_info_and_comms_module_are_saved_with_the_project(tmp_path):
    original = board()
    original.sections[0].contents.above.breaker.comms_module = "Siemens COM190"
    path = save_project(original, tmp_path / "job.swbd")
    assert open_project(path) == original


def test_older_project_files_get_empty_drawing_info(tmp_path):
    path = tmp_path / "old.swbd"
    path.write_text('{"format_version": 1, "name": "Old", "sections": [{"above": null, '
                    '"below": null, "tie": null}], "drawing_info": {"job_number": "1", '
                    '"designation": "from the first version"}}', encoding="utf-8")
    assert open_project(path).drawing_info == DrawingInfo(job_number="1")
