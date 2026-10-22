"""The section editor's CT and power meter boxes change the model (offscreen, no AutoCAD)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from src.layout.block_catalog import load_block_catalog  # noqa: E402
from src.layout.settings import load_settings  # noqa: E402
from src.model.devices import load_device_settings  # noqa: E402
from src.model.section_contents import Breaker, MainBreaker, SectionContents  # noqa: E402
from src.model.switchboard import Section, Switchboard  # noqa: E402
from src.ui.section_editor import SectionEditor  # noqa: E402

# One application for the whole module. Each test closes its editor itself, so no widget
# outlives the application when Python shuts down (that crashed the test run on exit).
APP = QApplication.instance() or QApplication([])


def test_adding_a_meter_and_ticking_cts_fills_the_model():
    devices = load_device_settings("config/devices.json")
    section = Section(SectionContents(above=MainBreaker(Breaker("52-M1"))))
    switchboard = Switchboard("Test", [section])
    editor = SectionEditor(load_settings("config/layout_settings.json"),
                           load_block_catalog("catalog/blocks.json"), devices.comms_modules,
                           devices.power_meter_models, switchboard_provider=lambda: switchboard)
    editor.load(section, 1)

    editor.devices_editor._add_meter()
    editor.devices_editor.model_combo.setCurrentText("Janitza UMG 801")
    meter = section.contents.power_meters[0]
    assert meter.model == "Janitza UMG 801"
    assert editor.devices_editor.meters_list.item(0).text().startswith("PM-1")

    ct_editor = editor.above_editor.ct_editor
    ct_editor.setChecked(True)
    assert section.contents.above.cts is not None
    ct_editor.meter_combo.setCurrentIndex(ct_editor.meter_combo.findData(meter.id))
    ct_editor.ratio_edit.setText("4000:5A")
    ct_editor.ratio_edit.textEdited.emit("4000:5A")
    assert section.contents.above.cts.meter_id == meter.id
    assert section.contents.above.cts.ratio == "4000:5A"

    ct_editor.setChecked(False)
    assert section.contents.above.cts is None

    # Voltage taps live on the main breaker's incoming feed (decision 2026-10-22).
    taps_editor = editor.above_editor.taps_editor
    assert editor.above_editor.termination_box.title() == "Incoming feed"
    taps_editor._add_tap()
    taps_editor.meter_combo.setCurrentIndex(taps_editor.meter_combo.findData(meter.id))
    assert section.contents.above.feed.voltage_taps[0].meter_id == meter.id
    assert taps_editor.taps_list.item(0).text() == "FA-1   to PM-1"
    editor.close()
    del editor


def test_a_main_breaker_can_be_fed_from_the_next_section():
    first, second = Section(SectionContents()), Section(SectionContents(above=MainBreaker(Breaker("52-M1"))))
    switchboard = Switchboard("Test", [first, second])
    settings = load_settings("config/layout_settings.json")
    catalog = load_block_catalog("catalog/blocks.json")
    editor = SectionEditor(settings, catalog, switchboard_provider=lambda: switchboard)

    # Section 1 above: an Incoming feed on its own is main lugs only until a main picks it.
    editor.load(first, 1)
    editor.above_editor.kind_combo.setCurrentText("Incoming feed")
    feed = first.contents.above
    assert editor.above_editor.feed_info.text() == "Goes to: the main bus (main lugs only)"

    # Section 2's main picks it: its own feed goes, and section 1 now says what it feeds.
    editor.load(second, 2)
    combo = editor.above_editor.feed_source_combo
    combo.setCurrentIndex(combo.findData(feed.id))
    main = second.contents.above
    assert (main.feed, main.feed_from) == (None, feed.id)
    editor.above_editor.breaker_feed_combo.setCurrentText("top")      # no feed of its own: fine
    editor.load(first, 1)
    assert editor.above_editor.feed_info.text() == "Feeds: 52-M1 (section 2 above)"

    # Back to a feed in its own riser.
    editor.load(second, 2)
    combo.setCurrentIndex(combo.findText("In this riser"))
    assert main.feed is not None and main.feed_from == ""

    # Section 1 becomes a line-side (load-bank) breaker fed from that main's feed.
    editor.load(first, 1)
    editor.above_editor.kind_combo.setCurrentText("Line-side breaker")
    load_bank = first.contents.above
    assert editor.above_editor.termination_box.title() == "Output"
    fed_from = editor.above_editor.fed_from_combo
    assert fed_from.itemText(1) == "Feed of 52-M1, section 2 above"
    fed_from.setCurrentIndex(1)
    assert load_bank.fed_from == main.feed.id
    editor.close()
    del editor
