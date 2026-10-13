"""Tests for turning what AutoCAD reads from a library block into a catalog entry, and for
reading the catalog back. The AutoCAD reading itself is checked in a real refresh."""
import json
from datetime import date

from src.autocad.catalog_refresh import blocks_in_use, catalog_entry, describe_changes
from src.layout.block_catalog import load_block_catalog
from tests.helpers import TEST_SETTINGS

BREAKER_MARKERS = {"not_flipped": {
    "CONN_A_TOP": (0.0, 0.0), "CONN_B_TOP": (5.0, 0.0), "CONN_C_TOP": (10.0, 0.0),
    "CONN_A_BOTTOM": (0.0, -10.0), "CONN_B_BOTTOM": (5.0, -10.0), "CONN_C_BOTTOM": (10.0, -10.0),
}}
LUGS_MARKERS = {
    "not_flipped": {"CONN_A": (0, 5), "CONN_B": (5, 5), "CONN_C": (10, 5), "CONN_N": (15, 5)},
    "flipped": {"CONN_A": (0, -5), "CONN_B": (5, -5), "CONN_C": (10, -5), "CONN_N": (15, -5)},
}
ATTRS = [{"tag": "BREAKER_NAME", "prompt": "Breaker name?", "default": "52-YY"}]


def test_breaker_markers_become_top_and_bottom_terminals():
    entry = catalog_entry(BREAKER_MARKERS, {"not_flipped": (-0.5, -11, 25, 3.5)}, ["1 BOM"], ATTRS,
                          today=date(2026, 10, 12))
    assert entry["top_terminals"] == [[0, 0], [5, 0], [10, 0]]
    assert entry["bottom_terminals"] == [[0, -10], [5, -10], [10, -10]]
    assert "connections" not in entry
    assert entry["attributes"] == ATTRS
    assert entry["visibility_states"] == ["1 BOM"]


def test_input_block_markers_become_connections_per_flip():
    extents = {"not_flipped": (-3, -10.25, 18, 5), "flipped": (-3, -5, 18, 10.25)}
    entry = catalog_entry(LUGS_MARKERS, extents, ["INPUT", "OUTPUT"], [])
    assert entry["connections"]["flipped"]["A"] == [0, -5]
    assert entry["connections"]["not_flipped"]["N"] == [15, 5]
    assert entry["extents_flipped"] == [-3, -5, 18, 10.25]


def test_hand_written_description_is_kept():
    entry = catalog_entry(BREAKER_MARKERS, {"not_flipped": (0, 0, 1, 1)}, [], [],
                          previous={"description": "3-pole fixed breaker"})
    assert entry["description"] == "3-pole fixed breaker"


def test_describe_changes_names_what_changed():
    old = {"B1": {"extents": [0, 0, 1, 1], "source": "x"}}
    new = {"B1": {"extents": [0, 0, 2, 1], "source": "y"}, "B2": {"extents": [0, 0, 1, 1]}}
    assert describe_changes(old, new) == ["B1: extents changed", "B2: added"]
    assert describe_changes(old, {"B1": {"extents": [0, 0, 1, 1], "source": "z"}}) == ["No changes."]


def test_blocks_in_use_come_from_config():
    assert blocks_in_use(TEST_SETTINGS) == ["BUS_NODE", "TEST_BKR", "TEST_BKR_DO", "TEST_BRACKET",
                                            "TEST_FEEDER", "TEST_LUGS", "TEST_LUGS_N", "TEST_TILDE"]


def test_catalog_reads_attributes_and_states(tmp_path):
    entry = catalog_entry(BREAKER_MARKERS, {"not_flipped": (-0.5, -11, 25, 3.5)}, ["1 BOM"], ATTRS)
    path = tmp_path / "blocks.json"
    path.write_text(json.dumps({"blocks": {"BKR": entry}}))
    info = load_block_catalog(path)["BKR"]
    assert info.attributes[0].prompt == "Breaker name?"
    assert info.visibility_states == ("1 BOM",)
    assert info.top_terminals[0] == (0, 0)


def test_missing_then_empty_is_not_a_change():
    assert describe_changes({"B": {"extents": [0, 0, 1, 1]}},
                            {"B": {"extents": [0, 0, 1, 1], "top_terminals": []}}) == ["No changes."]


# --- Audit checks ---------------------------------------------------------------------

from src.autocad.catalog_refresh import BREAKER, FEEDER, INPUT_OUTPUT, JUNCTION_DOT, audit_problems


def reading(markers, attributes=(), positions=None):
    return {"markers": markers, "attributes": list(attributes),
            "attribute_positions": positions or {}, "visibility_states": [], "extents": {}}


GOOD_PROMPT = {"tag": "LOCATION", "prompt": "Where is it coming from?", "default": "TO/FROM"}


def test_good_breaker_has_no_problems():
    assert audit_problems("BKR", BREAKER, reading(BREAKER_MARKERS, [GOOD_PROMPT]), 5) == []


def test_breaker_missing_markers_is_reported():
    markers = {"not_flipped": {k: v for k, v in BREAKER_MARKERS["not_flipped"].items()
                               if k != "CONN_B_BOTTOM"}}
    problems = audit_problems("BKR", BREAKER, reading(markers), 5)
    assert problems == ["BKR: missing connection markers CONN_B_BOTTOM."]


def test_markers_not_5_apart_are_reported():
    markers = {"not_flipped": dict(BREAKER_MARKERS["not_flipped"], CONN_C_TOP=(11.0, 0.0))}
    problems = audit_problems("BKR", BREAKER, reading(markers), 5)
    assert problems == ["BKR: top markers: A-B-C are 5 and 6 apart; the bus phases are 5 apart."]


def test_markers_at_different_heights_are_reported():
    markers = {"not_flipped": dict(BREAKER_MARKERS["not_flipped"], CONN_A_TOP=(0.0, 0.05))}
    problems = audit_problems("BKR", BREAKER, reading(markers), 5)
    assert problems == ["BKR: top markers: A, B and C are not at the same height."]


def test_input_block_checked_in_both_flips():
    markers = {"not_flipped": LUGS_MARKERS["not_flipped"],
               "flipped": {k: v for k, v in LUGS_MARKERS["flipped"].items() if k != "CONN_A"}}
    problems = audit_problems("LUGS", INPUT_OUTPUT, reading(markers), 5)
    assert problems == ["LUGS (flipped): missing connection markers CONN_A."]


def test_only_empty_prompts_are_reported():
    # A prompt repeating its default is fine (decision 2026-10-12); an empty one is not.
    attrs = [GOOD_PROMPT,
             {"tag": "BREAKER_NAME", "prompt": "52-YY", "default": "52-YY"},
             {"tag": "1BOM1", "prompt": "", "default": "##"}]
    problems = audit_problems("DOT", JUNCTION_DOT, reading({}, attrs), 5)
    assert len(problems) == 1
    assert problems[0].endswith(": 1BOM1.")


def test_attribute_text_that_does_not_flip_is_reported():
    positions = {"not_flipped": {"LOCATION": [1.0, -8.25], "TERMINATION": [5.0, -10.25]},
                 "flipped": {"LOCATION": [1.0, -8.25], "TERMINATION": [5.0, 10.25]}}
    problems = audit_problems("LUGS", INPUT_OUTPUT, reading(LUGS_MARKERS, [], positions), 5)
    assert problems == ["LUGS: attribute text doesn't move when the block flips (LOCATION). "
                        "Add the attributes to the flip action so the text stays clear of the bus."]



def test_shared_attribute_tags_are_reported():
    attrs = [{"tag": "#", "prompt": "Phase", "default": "A"}] * 3
    problems = audit_problems("TILDE", JUNCTION_DOT, reading({}, attrs), 5)
    assert problems == ["TILDE: several attributes share the tag #; the configurator can only "
                        "give them all the same text."]



def test_break_blocks_are_not_asked_for_prompts():
    from src.autocad.catalog_refresh import LABEL
    attrs = [{"tag": "LABLE", "prompt": "", "default": "XXX"}]
    assert audit_problems("BRACKET", LABEL, reading({}, attrs), 5) == []


FEEDER_MARKERS = {
    "not_flipped": {"CONN_A": (0, 10), "CONN_B": (0, 5), "CONN_C": (0, 0)},
    "flipped": {"CONN_A": (0, 10), "CONN_B": (0, 5), "CONN_C": (0, 0)},
}


def test_good_feeder_has_no_problems():
    assert audit_problems("FDR", FEEDER, reading(FEEDER_MARKERS, [GOOD_PROMPT]), 5) == []


def test_feeder_markers_must_stack_5_apart():
    bad = {"not_flipped": {"CONN_A": (0, 12), "CONN_B": (0, 5), "CONN_C": (0, 0)},
           "flipped": FEEDER_MARKERS["flipped"]}
    problems = audit_problems("FDR", FEEDER, reading(bad, [GOOD_PROMPT]), 5)
    assert problems == ["FDR (not flipped): A-B-C are 7 and 5 apart going down; the bus "
                        "phases are 5 apart."]


def test_feeder_without_mirror_is_reported():
    plain = {"not_flipped": FEEDER_MARKERS["not_flipped"]}
    problems = audit_problems("FDR", FEEDER, reading(plain, [GOOD_PROMPT]), 5)
    assert problems == ["FDR: has no flip/mirror setting, so right-side breakers can't be drawn."]


def test_markers_left_out_of_the_flip_are_reported():
    # The mirrored breaker moved to x 20..62 but its markers stayed at x 0.
    stuck = reading(FEEDER_MARKERS, [GOOD_PROMPT])
    stuck["extents"] = {"not_flipped": (-32, -6.5, 8.6, 23.4), "flipped": (20.1, -6.5, 62.2, 23.4)}
    problems = audit_problems("FDR", FEEDER, stuck, 5)
    assert problems == ["FDR (flipped): connection markers CONN_A, CONN_B, CONN_C are outside "
                        "the block. Add them to the flip action so they move with the terminals."]
