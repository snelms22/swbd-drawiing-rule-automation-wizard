"""A tilde's text on one line or two, and the room kept for it (Sammy, 2026-11-20)."""
from dataclasses import replace

from src.layout.block_catalog import AttributeInfo
from src.layout.device_units import tilde_text, tilde_text_box, wire_breaks
from tests.helpers import TEST_CATALOG, TEST_SETTINGS

DP = TEST_SETTINGS.device_pages


def multiline_catalog():
    """The test tilde with a multi-line TEXT_H, as Sammy is making TILDE_R0's."""
    tilde = TEST_CATALOG["TEST_WIRE_TILDE"]
    return {**TEST_CATALOG, "TEST_WIRE_TILDE": replace(tilde, attributes=(
        AttributeInfo("TEXT_V", "Vertical Text", "X", True), AttributeInfo("TEXT_H", "Horizontal Text", "X", True)))}


def test_a_short_text_stays_on_one_line():
    for text in ("TO 1TBG", "FROM 5SSM-1", "FROM PM-1", "TO 5SSM-2"):
        assert tilde_text(text, DP) == text


def test_a_long_text_breaks_where_the_longer_line_is_shortest():
    assert tilde_text("TO ES-1 SECTION 1", DP) == "TO ES-1\nSECTION 1"
    assert tilde_text("CUSTOMER CONNECTION", DP) == "CUSTOMER\nCONNECTION"
    assert tilde_text("TO COM800-1 SECTION 5", DP) == "TO COM800-1\nSECTION 5"


def test_never_a_third_line_the_label_is_wider_instead():
    # "TO MCB01 COM190" is over 12 characters, but it stays one line of two.
    assert tilde_text("TO MCB01 COM190 SECTION 1", DP) == "TO MCB01 COM190\nSECTION 1"
    assert tilde_text("TO A VERY LONG DEVICE NAME IN SECTION 12", DP).count("\n") == 1
    # Nowhere to break: one line, however long.
    assert tilde_text("TO-A-VERY-LONG-DEVICE", DP) == "TO-A-VERY-LONG-DEVICE"


def test_where_the_wires_are_too_close_for_two_lines_it_stays_on_one():
    # Two lines need 1.25 + 2.08 = 3.33, plus 0.5 clear: a terminal strip's 2.5 is too close,
    # the switch's ports 5 apart are not.
    assert tilde_text("FROM COM800-12", DP, spacing=2.5) == "FROM COM800-12"
    assert tilde_text("FROM COM800-12", DP, spacing=5.0) == "FROM\nCOM800-12"


def test_the_tilde_takes_in_its_text():
    # Un-mirrored the text starts 0.5 past the tilde; mirrored it ends 0.5 before it.
    plain = wire_breaks([(10.0, 0.0)], TEST_SETTINGS, TEST_CATALOG, "HORIZONTAL", text="TO 1TBG")[0]
    left, bottom, right, top = plain.extents
    assert right == 0.5 + 7 * 1.15 and left == -0.83
    mirrored = wire_breaks([(10.0, 0.0)], TEST_SETTINGS, TEST_CATALOG, "HORIZONTAL",
                           flip_parameter="Flip state1", text="TO 1TBG")[0]
    left, bottom, right, top = mirrored.extents
    assert left == -0.5 - 7 * 1.15 and right == 0.83
    # No text: just the tilde, as before.
    bare = wire_breaks([(10.0, 0.0)], TEST_SETTINGS, TEST_CATALOG, "HORIZONTAL")[0]
    assert bare.extents == (-0.83, -1.25, 0.83, 1.25)


def test_two_lines_only_when_the_blocks_text_is_multi_line():
    text = "TO ES-1 SECTION 1"
    single = wire_breaks([(0.0, 0.0)], TEST_SETTINGS, TEST_CATALOG, "HORIZONTAL", text=text)[0]
    assert single.attributes["TEXT_H"] == text
    double = wire_breaks([(0.0, 0.0)], TEST_SETTINGS, multiline_catalog(), "HORIZONTAL", text=text)[0]
    assert double.attributes["TEXT_H"] == "TO ES-1\nSECTION 1"
    # Its room: the longer line wide, two lines tall.
    assert double.extents[2] == tilde_text_box("TO ES-1\nSECTION 1", DP, False)[2] == 0.5 + 9 * 1.15
    assert double.extents[3] == (1.25 + 2.08) / 2


def test_stacked_ends_closer_than_two_lines_keep_one_line():
    ends = [(0.0, 0.0), (0.0, -2.5)]
    tildes = wire_breaks(ends, TEST_SETTINGS, multiline_catalog(), "HORIZONTAL", text="TO ES-1 SECTION 1")
    assert [t.attributes["TEXT_H"] for t in tildes] == ["TO ES-1 SECTION 1"] * 2
