"""Breaker families by position, comms by family, and the automatic DAS/MMS of every 3WA
(decision 2026-11-09; src/model/devices.py, the section editor)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from src.layout.block_catalog import load_block_catalog  # noqa: E402
from src.layout.settings import load_settings  # noqa: E402
from src.model.devices import comms_choices, load_device_settings, mms_in  # noqa: E402
from src.model.project_file import switchboard_from_dict, switchboard_to_dict  # noqa: E402
from src.model.section_contents import (  # noqa: E402
    Breaker, GroupMounted, LineSideBreaker, MainBreaker, SectionContents, SingleBreaker, SingleLevel,
    TieBreaker,
)
from src.model.switchboard import Section, Switchboard  # noqa: E402

APP = QApplication.instance() or QApplication([])


def lineup():
    return Switchboard("Test", [
        Section(SectionContents(above=MainBreaker(Breaker("52-M1")), tie=TieBreaker(Breaker("52-T1")))),
        Section(SectionContents(above=GroupMounted([SingleLevel(Breaker("52-F1"))]),
                                below=SingleBreaker(Breaker("52-F2")))),
        Section(SectionContents(above=LineSideBreaker(Breaker("52-LB")))),
    ])


def test_every_3wa_gets_a_das_mms_numbered_through_the_lineup():
    names = [(info.name, info.breaker.label) for info in mms_in(lineup())]
    # Main, tie, single and line-side breakers are 3WA; the group-mounted 52-F1 is a 3VA.
    assert names == [("MMS-1", "52-M1"), ("MMS-2", "52-T1"), ("MMS-3", "52-F2"), ("MMS-4", "52-LB")]


def test_comms_are_offered_by_family():
    devices = load_device_settings("config/devices.json")
    assert comms_choices(devices.comms_modules, "3WA") == ["Siemens COM190"]
    assert comms_choices(devices.comms_modules, "3VA") == ["Siemens COM060"]
    assert comms_choices(["A", "B"], "3VA") == ["A", "B"]          # a plain list: every family


def test_a_group_mounted_breaker_saved_with_the_com800_opens_with_the_com060():
    switchboard = lineup()
    data = switchboard_to_dict(switchboard)
    data["sections"][1]["above"]["levels"][0]["slot"]["comms_module"] = "Siemens COM800"
    opened = switchboard_from_dict(data)
    assert opened.sections[1].contents.above.levels[0].slot.comms_module == "Siemens COM060"


def test_the_editor_shows_the_automatic_mms_and_3wa_comms():
    from src.ui.section_editor import SectionEditor

    switchboard = lineup()
    devices = load_device_settings("config/devices.json")
    editor = SectionEditor(load_settings("config/layout_settings.json"),
                           load_block_catalog("catalog/blocks.json"), devices.comms_modules,
                           devices.power_meter_models, switchboard_provider=lambda: switchboard)
    editor.load(switchboard.sections[1], 2)
    below = editor.below_editor
    assert below.mms_info.text() == "MMS-3 (added automatically)"
    assert [below.breaker_comms_combo.itemText(i) for i in range(below.breaker_comms_combo.count())] == \
        ["None", "Siemens COM190"]
    slot_combo = editor.above_editor.single_slot.comms_combo
    assert [slot_combo.itemText(i) for i in range(slot_combo.count())] == ["None", "Siemens COM060"]
    editor.load(switchboard.sections[0], 1)
    assert editor.tie_editor.mms_info.text() == "MMS-2 (added automatically)"
    editor.close()


def test_comms_or_meters_need_the_ethernet_switch_in_one_section():
    from src.model.devices import device_problems, needs_ethernet_switch
    from src.model.section_contents import PowerMeter

    switchboard = lineup()
    assert not needs_ethernet_switch(switchboard) and device_problems(switchboard) == []
    switchboard.sections[1].contents.above.levels[0].slot.comms_module = "Siemens COM060"
    assert needs_ethernet_switch(switchboard)
    assert any("there is an Ethernet switch" in p for p in device_problems(switchboard))
    switchboard.sections[2].contents.ethernet_switch = True
    assert device_problems(switchboard) == []
    switchboard.sections[0].contents.ethernet_switch = True
    assert device_problems(switchboard) == [
        "The Ethernet switch is ticked in more than one section (1, 3); there is only one."]
    # A power meter alone means one too.
    meters_only = Switchboard("M", [Section(SectionContents(power_meters=[PowerMeter("Janitza UMG 801")]))])
    assert needs_ethernet_switch(meters_only)


def test_the_ethernet_switch_box_shows_when_needed_and_ticks_one_section():
    from src.ui.section_editor import SectionEditor

    switchboard = lineup()
    devices = load_device_settings("config/devices.json")
    editor = SectionEditor(load_settings("config/layout_settings.json"),
                           load_block_catalog("catalog/blocks.json"), devices.comms_modules,
                           devices.power_meter_models, switchboard_provider=lambda: switchboard)
    box = editor.devices_editor
    editor.load(switchboard.sections[0], 1)
    assert box.ethernet_check.isHidden()                       # no comms, no meters yet
    switchboard.sections[0].contents.above.breaker.comms_module = "Siemens COM190"
    editor.load(switchboard.sections[0], 1)
    assert not box.ethernet_check.isHidden()
    box.ethernet_check.setChecked(True)
    editor.load(switchboard.sections[2], 3)
    box.ethernet_check.setChecked(True)                        # moved to section 3
    assert [s.contents.ethernet_switch for s in switchboard.sections] == [False, False, True]
    editor.close()


def test_the_ethernet_switch_box_appears_as_soon_as_a_comms_module_is_picked():
    from src.ui.section_editor import SectionEditor

    switchboard = lineup()
    devices = load_device_settings("config/devices.json")
    editor = SectionEditor(load_settings("config/layout_settings.json"),
                           load_block_catalog("catalog/blocks.json"), devices.comms_modules,
                           devices.power_meter_models, switchboard_provider=lambda: switchboard)
    editor.load(switchboard.sections[0], 1)
    assert editor.devices_editor.ethernet_check.isHidden()
    editor.above_editor.breaker_comms_combo.setCurrentText("Siemens COM190")
    assert not editor.devices_editor.ethernet_check.isHidden()
    editor.close()
