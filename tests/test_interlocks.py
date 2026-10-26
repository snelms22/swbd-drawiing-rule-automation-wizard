"""Interlocks between main breakers (decision 2026-10-26; src/model/interlocks.py,
src/layout/interlocks.py).

Test numbers (tests/helpers.py): margin 10, section clearance 5, so two main-breaker sections
have their divider at x 50. TEST_BKR: poles at x 0 / 5 / 10, 10 long, reaching 25 right of
its base point. A main breaker above the bus sits with its base point at (15.5, 65) in
section 1 and (55.5, 65) in section 2, so its mid-height is y 60.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from src.autocad.draw_page import Polyline, Text, page_shapes  # noqa: E402
from src.layout.page_fitter import fit_pages  # noqa: E402
from src.model.interlocks import interlock_links, interlock_of, set_interlock  # noqa: E402
from src.model.project_file import switchboard_from_dict, switchboard_to_dict  # noqa: E402
from src.model.section_contents import (  # noqa: E402
    Breaker, CurrentTransformers, MainBreaker, SectionContents, SingleBreaker,
)
from src.model.switchboard import Section, Switchboard  # noqa: E402
from tests.helpers import TEST_CATALOG, TEST_SETTINGS  # noqa: E402

APP = QApplication.instance() or QApplication([])


def two_mains(*more_contents):
    m1, m2 = MainBreaker(Breaker("52-M1")), MainBreaker(Breaker("52-M2"))
    sections = [Section(SectionContents(above=m1)), Section(SectionContents(above=m2))]
    sections += [Section(contents) for contents in more_contents]
    return Switchboard("Test", sections), m1, m2


def test_no_interlock_no_line():
    switchboard, _, _ = two_mains()
    page = fit_pages(switchboard, TEST_SETTINGS, TEST_CATALOG).pages[0]
    assert page.parts.interlocks == []


def test_interlocked_mains_side_by_side_get_a_straight_line():
    switchboard, m1, m2 = two_mains()
    set_interlock(switchboard, m1, m2.id, mechanical=True, electrical=True)
    result = fit_pages(switchboard, TEST_SETTINGS, TEST_CATALOG)
    assert result.warnings == []
    line = result.pages[0].parts.interlocks[0]
    # From 2.5 past M1's C terminal (25.5) to 1 short of M2's A terminal (55.5), at y 60.
    assert line.points == [(28.0, 60.0), (54.5, 60.0)]
    assert line.text_lines == ("MECHANICAL AND", "ELECTRICAL INTERLOCK")
    # Centred between M1's block (its right edge at 40.5) and the line's end.
    assert (line.text_x, line.text_y) == (47.5, 60.0)


def test_the_text_says_which_kind():
    switchboard, m1, m2 = two_mains()
    set_interlock(switchboard, m1, m2.id, electrical=True)
    line = fit_pages(switchboard, TEST_SETTINGS, TEST_CATALOG).pages[0].parts.interlocks[0]
    assert line.text_lines == ("ELECTRICAL INTERLOCK",)
    m1.interlock.electrical, m1.interlock.mechanical = False, True
    line = fit_pages(switchboard, TEST_SETTINGS, TEST_CATALOG).pages[0].parts.interlocks[0]
    assert line.text_lines == ("MECHANICAL INTERLOCK",)


def test_mains_at_different_heights_get_a_stepped_line():
    switchboard, m1, m2 = two_mains()
    m2.cts = CurrentTransformers()          # its riser grows, so M2 sits higher
    set_interlock(switchboard, m1, m2.id, mechanical=True)
    page = fit_pages(switchboard, TEST_SETTINGS, TEST_CATALOG).pages[0]
    m2_block = [b for b in page.parts.blocks if b.label == "52-M2"][0]
    m2_mid_y = m2_block.position[1] - 5
    assert m2_mid_y > 60
    line = page.parts.interlocks[0]
    # Steps halfway between the divider (50) and section 2's contents (55).
    assert line.points == [(28.0, 60.0), (52.5, 60.0), (52.5, m2_mid_y),
                           (m2_block.position[0] - 1, m2_mid_y)]
    assert line.text_x == (40.5 + 52.5) / 2


def test_the_interlock_can_be_set_on_either_main():
    switchboard, m1, m2 = two_mains()
    set_interlock(switchboard, m2, m1.id, electrical=True)      # set on the right-hand main
    line = fit_pages(switchboard, TEST_SETTINGS, TEST_CATALOG).pages[0].parts.interlocks[0]
    assert line.points == [(28.0, 60.0), (54.5, 60.0)]
    # Both mains see the same record.
    assert interlock_of(switchboard, m1) == (m2.interlock, m2.id)
    assert interlock_of(switchboard, m2) == (m2.interlock, m1.id)


def test_setting_an_interlock_again_replaces_the_old_one():
    m3 = MainBreaker(Breaker("52-M3"))
    switchboard, m1, m2 = two_mains(SectionContents(above=m3))
    set_interlock(switchboard, m1, m2.id, mechanical=True)
    set_interlock(switchboard, m2, m3.id, electrical=True)      # from M2's editor
    assert m1.interlock is None
    assert interlock_of(switchboard, m1) is None
    assert interlock_of(switchboard, m3) == (m2.interlock, m2.id)
    set_interlock(switchboard, m3, "")                          # "None" on M3's editor
    assert interlock_of(switchboard, m2) is None


def test_interlocked_sections_stay_on_one_page():
    switchboard, m1, m2 = two_mains()
    switchboard.sections[1].push_to_next_page = True
    set_interlock(switchboard, m1, m2.id, mechanical=True)
    result = fit_pages(switchboard, TEST_SETTINGS, TEST_CATALOG)
    assert [[p.number for p in page.placed_sections] for page in result.pages] == [[1, 2]]
    assert len(result.pages[0].parts.interlocks) == 1


def test_mains_not_next_door_get_a_warning_and_no_line():
    m3 = MainBreaker(Breaker("52-M3"))
    switchboard, m1, _ = two_mains(SectionContents(above=m3))
    set_interlock(switchboard, m1, m3.id, mechanical=True)
    result = fit_pages(switchboard, TEST_SETTINGS, TEST_CATALOG)
    assert result.pages[0].parts.interlocks == []
    assert any("52-M3 (section 3 above), which is not in the section next to it" in w
               for w in result.warnings)


def test_other_problems_are_reported_in_plain_words():
    switchboard, m1, m2 = two_mains()
    set_interlock(switchboard, m1, m2.id)                       # neither kind ticked
    _, problems = interlock_links(switchboard)
    assert "marked mechanical, electrical or both" in problems[0]

    switchboard.sections[1].contents = SectionContents(below=m2)  # other side of the bus
    m1.interlock.mechanical = True
    _, problems = interlock_links(switchboard)
    assert "other side of the main bus" in problems[0]

    switchboard.sections[1].contents = SectionContents(above=SingleBreaker(Breaker("52-F1")))
    _, problems = interlock_links(switchboard)
    assert "no longer exists" in problems[0]


def test_drawn_as_a_dashed_polyline_and_masked_text():
    switchboard, m1, m2 = two_mains()
    set_interlock(switchboard, m1, m2.id, mechanical=True, electrical=True)
    page = fit_pages(switchboard, TEST_SETTINGS, TEST_CATALOG).pages[0]
    shapes = page_shapes(page, TEST_SETTINGS, "PLACEHOLDER")
    line = [s for s in shapes if isinstance(s, Polyline) and s.layer == "INTERLOCK"][0]
    text = [s for s in shapes if isinstance(s, Text) and "INTERLOCK" in s.text][0]
    assert line.points == [(28.0, 60.0), (54.5, 60.0)]
    assert text.text == "MECHANICAL AND\\PELECTRICAL INTERLOCK"
    assert text.align == "middle_center" and text.background_mask


def test_interlock_is_saved_and_opened():
    switchboard, m1, m2 = two_mains()
    set_interlock(switchboard, m1, m2.id, electrical=True)
    opened = switchboard_from_dict(switchboard_to_dict(switchboard))
    o1, o2 = (s.contents.above for s in opened.sections)
    assert (o1.id, o2.id) == (m1.id, m2.id)
    assert o1.interlock == m1.interlock and o2.interlock is None


def test_older_files_open_with_no_interlock():
    switchboard, m1, _ = two_mains()
    data = switchboard_to_dict(switchboard)
    for section in data["sections"]:
        del section["above"]["id"], section["above"]["interlock"]
    opened = switchboard_from_dict(data)
    o1, o2 = (s.contents.above for s in opened.sections)
    assert o1.interlock is None and o1.id and o1.id != o2.id


def test_the_editor_shows_and_edits_one_interlock_from_both_mains():
    from src.layout.settings import load_settings
    from src.layout.block_catalog import load_block_catalog
    from src.model.devices import load_device_settings
    from src.ui.section_editor import SectionEditor

    switchboard, m1, m2 = two_mains()
    devices = load_device_settings("config/devices.json")
    editor = SectionEditor(load_settings("config/layout_settings.json"),
                           load_block_catalog("catalog/blocks.json"), devices.comms_modules,
                           devices.power_meter_models, switchboard_provider=lambda: switchboard,
                           fuse=devices.fuse)
    box = editor.above_editor.interlock_editor
    editor.load(switchboard.sections[0], 1)
    box.with_combo.setCurrentIndex(box.with_combo.findData(m2.id))
    box.electrical_check.setChecked(True)
    assert m1.interlock.with_main == m2.id and m1.interlock.electrical

    editor.load(switchboard.sections[1], 2)             # M2's editor shows the same interlock
    assert box.with_combo.currentData() == m1.id
    assert box.electrical_check.isChecked() and not box.mechanical_check.isChecked()
    box.mechanical_check.setChecked(True)
    assert m1.interlock.mechanical                       # the one record changed

    box.with_combo.setCurrentIndex(box.with_combo.findData(""))   # None
    assert interlock_of(switchboard, m1) is None and interlock_of(switchboard, m2) is None
    editor.close()
