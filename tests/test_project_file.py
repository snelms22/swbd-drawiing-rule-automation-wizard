"""Tests for saving and opening projects (src/model/project_file.py, decisions 2026-10-15)."""
import json
from dataclasses import replace

import pytest

from src.layout.block_catalog import AttributeInfo
from src.model.project_file import (
    FORMAT_VERSION, ProjectFileError, attributes_no_longer_on_blocks, open_project, save_project,
)
from src.model.section_contents import (
    Breaker, GroupMounted, MainBreaker, Provision, SectionContents, SingleBreaker, SingleLevel, Space,
    TieBreaker, TwinLevel,
)
from src.model.switchboard import Section, Switchboard
from tests.helpers import TEST_CATALOG, TEST_SETTINGS


def everything_board() -> Switchboard:
    """One of every kind of thing a project can hold."""
    return Switchboard("Job 1234 MSB", [
        Section(SectionContents(
            above=MainBreaker(Breaker("52-M1", attributes={"SIZE/POLLS": "4000AF/\n4000AT"}),
                              mounting="draw-out", input_attributes={"TERMINATION": "LUGS\n(14) 750"}),
            below=MainBreaker(Breaker("52-M2"), breaker_feed="bottom", termination_feed="top"),
        ), push_to_next_page=True),
        Section(SectionContents(
            above=GroupMounted([
                TwinLevel(Breaker("52-F1", attributes={"BKR_RATINGS": "125AF"}), Provision("3VA62 250AF")),
                SingleLevel(Breaker("52-F2"), flipped=True),
                SingleLevel(Provision("")),
                TwinLevel(Space(), Breaker("52-F9")),
                SingleLevel(Space()),
            ]),
            below=SingleBreaker(Breaker("52-F3"), output_attributes={"LOCATION": "TO/FROM"},
                                breaker_feed="bottom", termination_feed="bottom"),
            tie=TieBreaker(Breaker("52-T1", attributes={"ETU/DAS": "LSI"}), bus_steps="up",
                           mounting="draw-out"),
        ), link_with_next=True),
        Section(),
    ])


def test_save_then_open_gives_the_same_switchboard(tmp_path):
    board = everything_board()
    path = save_project(board, tmp_path / "job.swbd")
    assert open_project(path) == board


def test_the_swbd_extension_is_added_when_missing(tmp_path):
    path = save_project(everything_board(), tmp_path / "Job 1234")
    assert path.name == "Job 1234.swbd" and path.exists()


def test_saving_again_overwrites_the_same_file(tmp_path):
    board = everything_board()
    path = save_project(board, tmp_path / "job.swbd")
    board.name = "Renamed"
    save_project(board, path)
    assert open_project(path).name == "Renamed"
    assert [p.name for p in tmp_path.iterdir()] == ["job.swbd"]


def test_file_is_readable_json_with_version(tmp_path):
    path = save_project(everything_board(), tmp_path / "job.swbd")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["format_version"] == FORMAT_VERSION and data["saved_with"]
    assert data["sections"][0]["above"]["kind"] == "main breaker"
    assert data["sections"][1]["above"]["levels"][0]["right"] == {"provision": "3VA62 250AF"}


def test_missing_feed_directions_mean_the_defaults(tmp_path):
    path = save_project(everything_board(), tmp_path / "job.swbd")
    data = json.loads(path.read_text(encoding="utf-8"))
    del data["sections"][0]["above"]["breaker_feed"]
    path.write_text(json.dumps(data), encoding="utf-8")
    assert open_project(path).sections[0].contents.above.breaker_feed == ""


def test_a_file_from_a_newer_configurator_is_refused_with_a_clear_message(tmp_path):
    path = tmp_path / "new.swbd"
    path.write_text(json.dumps({"format_version": FORMAT_VERSION + 1, "sections": []}), encoding="utf-8")
    with pytest.raises(ProjectFileError, match="newer version"):
        open_project(path)


def test_files_that_are_not_projects_are_refused_with_a_clear_message(tmp_path):
    garbage = tmp_path / "garbage.swbd"
    garbage.write_text("this is not json", encoding="utf-8")
    with pytest.raises(ProjectFileError, match="not a readable project file"):
        open_project(garbage)
    other = tmp_path / "other.swbd"
    other.write_text(json.dumps({"hello": 1}), encoding="utf-8")
    with pytest.raises(ProjectFileError, match="not a switchboard project file"):
        open_project(other)
    damaged = tmp_path / "damaged.swbd"
    damaged.write_text(json.dumps({"format_version": 1, "sections": [{"above": {"kind": "main breaker"}}]}),
                       encoding="utf-8")
    with pytest.raises(ProjectFileError, match="damaged or incomplete"):
        open_project(damaged)
    with pytest.raises(ProjectFileError, match="not found"):
        open_project(tmp_path / "missing.swbd")


def test_attributes_the_block_no_longer_has_are_reported_not_dropped():
    catalog = dict(TEST_CATALOG)
    catalog["TEST_BKR"] = replace(TEST_CATALOG["TEST_BKR"],
                                  attributes=(AttributeInfo("SIZE/POLLS", "Size", ""),))
    board = Switchboard("x", [Section(SectionContents(
        above=MainBreaker(Breaker("52-M", attributes={"SIZE/POLLS": "4000AF", "OLDTAG": "x"}))))])
    found = attributes_no_longer_on_blocks(board, TEST_SETTINGS, catalog)
    assert found == ["Section 1 above: attribute OLDTAG is no longer on block TEST_BKR "
                     "(its value is kept in the project)."]
    assert board.sections[0].contents.above.breaker.attributes["OLDTAG"] == "x"
