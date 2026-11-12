"""The section editor's CT and power meter boxes change the model (offscreen, no AutoCAD)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QFormLayout  # noqa: E402

from src.layout.block_catalog import load_block_catalog  # noqa: E402
from src.layout.settings import load_settings  # noqa: E402
from src.model.devices import load_device_settings  # noqa: E402
from src.model.section_contents import Breaker, MainBreaker, SectionContents, SingleBreaker  # noqa: E402
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
                           devices.power_meter_models, switchboard_provider=lambda: switchboard,
                           fuse=devices.fuse)
    editor.load(section, 1)

    editor.devices_editor._add_meter()
    editor.devices_editor.model_combo.setCurrentText("Janitza UMG 801")
    meter = section.contents.power_meters[0]
    assert meter.model == "Janitza UMG 801"
    assert editor.devices_editor.meters_list.item(0).text().startswith("PM-1")
    editor.devices_editor.remote_display_check.setChecked(True)
    assert meter.remote_display

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
    taps_editor.feeds_combo.setCurrentIndex(taps_editor.feeds_combo.findData(meter.id))
    assert section.contents.above.feed.voltage_taps[0].feeds == meter.id
    assert taps_editor.taps_list.item(0).text() == "FA-1   to PM-1   (line side)"
    # The fuse's rating is filled by the engineer; its number by the program (no field).
    fields = {taps_editor.fuse_form.itemAt(row, QFormLayout.FieldRole).widget().toolTip(): row
              for row in range(taps_editor.fuse_form.rowCount())}
    assert "Attribute CURRENT" in fields and "Attribute FUSE_DWG_NUM" not in fields
    rating = taps_editor.fuse_form.itemAt(fields["Attribute CURRENT"], QFormLayout.FieldRole).widget()
    rating.setText("1A")
    rating.textEdited.emit("1A")
    assert section.contents.above.feed.voltage_taps[0].fuse_attributes["CURRENT"] == "1A"

    # Moved to the main's load side (decision 2026-10-23): the same tap, now on the main.
    tap = section.contents.above.feed.voltage_taps[0]
    taps_editor.side_combo.setCurrentText("Load side")
    assert section.contents.above.feed.voltage_taps == []
    assert section.contents.above.load_side_taps == [tap]
    assert taps_editor.taps_list.item(0).text() == "FA-1   to PM-1   (load side)"
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


def test_a_single_breaker_has_a_mounting_choice():
    section = Section(SectionContents(below=SingleBreaker(Breaker("52-F1"))))
    switchboard = Switchboard("Test", [section])
    editor = SectionEditor(load_settings("config/layout_settings.json"), load_block_catalog("catalog/blocks.json"),
                           switchboard_provider=lambda: switchboard)
    editor.load(section, 1)
    below = editor.below_editor
    assert below.breaker_form.isRowVisible(below.mounting_combo)
    below.mounting_combo.setCurrentText("draw-out")
    assert section.contents.below.mounting == "draw-out"
    editor.close()
    del editor


def test_mouse_wheel_does_not_change_a_closed_drop_down():
    """Scrolling the editor over a drop-down must not change it (Sammy, 2026-10-23)."""
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtGui import QWheelEvent
    from src.ui.widgets import ScrollSafeComboBox

    combo = ScrollSafeComboBox()
    combo.addItems(["top", "bottom"])
    wheel_down = QWheelEvent(QPointF(5, 5), QPointF(5, 5), QPoint(0, 0), QPoint(0, -120),
                             Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
    APP.sendEvent(combo, wheel_down)
    assert combo.currentIndex() == 0
    assert not wheel_down.isAccepted()      # passed on, so the editor scrolls instead
    combo.close()
