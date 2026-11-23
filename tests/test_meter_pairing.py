"""Tests for meter models and their input-block pairs (decision 2026-10-22; config/devices.json,
src/model/devices.py pairing_problems, Audit Blocks)."""
from src.autocad.catalog_refresh import DEVICE, block_roles, catalog_entry
from src.model.devices import InputBlock, MeterModel, load_device_settings, pairing_problems
from tests.helpers import TEST_SETTINGS

# Shaped like Janitza_UMG801: voltage terminals on top (VN, V3, V2, V1, 5 apart), current
# inputs underneath (I1+ ... I3-, 5 apart).
METER = {"VN": (-44.5, 14), "V3": (-39.5, 14), "V2": (-34.5, 14), "V1": (-29.5, 14),
         "I1+": (-44, -14), "I1-": (-39, -14), "I2+": (-34, -14), "I2-": (-29, -14),
         "I3+": (-24, -14), "I3-": (-19, -14)}
VOLTAGE = {"V_B": (0, 0), "V_C": (5, 0), "V_A": (15, 0)}
CURRENT = {"CT_A+": (0, 0), "CT_A-": (5, 0), "CT_B+": (10, 0), "CT_B-": (15, 0),
           "CT_C+": (20, 0), "CT_C-": (25, 0)}
MODEL = MeterModel(
    name="Meter", block="METER",
    voltage_input=InputBlock("VOLTAGE", {"V_A": "V1", "V_B": "VN", "V_C": "V3"}),
    current_inputs=(InputBlock("CURRENT", {"CT_A+": "I1+", "CT_A-": "I1-", "CT_B+": "I2+",
                                           "CT_B-": "I2-", "CT_C+": "I3+", "CT_C-": "I3-"}),),
)


def blocks(meter=METER):
    return {"METER": meter, "VOLTAGE": VOLTAGE, "CURRENT": CURRENT}


def test_inputs_that_line_up_have_no_problems():
    assert pairing_problems(MODEL, blocks()) == []


def test_a_misnamed_meter_marker_is_found_where_it_should_be():
    meter = {("V4" if name == "V1" else name): point for name, point in METER.items()}
    assert pairing_problems(MODEL, blocks(meter)) == [
        "Meter voltage input (VOLTAGE on METER): METER has no marker V1 (for V_A). "
        "The marker where it should be is named V4."]


def test_a_marker_in_the_wrong_place_is_reported():
    meter = dict(METER, V3=(-38.5, 14))
    assert pairing_problems(MODEL, blocks(meter)) == [
        "Meter voltage input (VOLTAGE on METER): V_C would land at (-39.5, 14) but V3 is at "
        "(-38.5, 14); they don't line up."]


def test_a_model_without_a_block_is_not_checked():
    assert pairing_problems(MeterModel("Later", "", None, ()), blocks()) == []


def test_the_real_devices_file_loads_and_names_its_blocks():
    devices = load_device_settings("config/devices.json")
    assert devices.power_meter_models == ["Janitza UMG 801", "Schneider PM8000"]
    # The UMG 801 Rev2 (2026-11-17) is wired straight into its pins: no input blocks.
    # The Ethernet switch's three sizes (2026-11-19) are read too.
    assert devices.device_blocks() == ["1P_FUSE_1", "3P_2P_FUSE_DISCONECT", "3P_PWR_SUP", "Ethernet_Switch_16PORT",
                                      "Ethernet_Switch_5PORT", "Ethernet_Switch_8PORT", "Female_Shipping_Split",
                                      "Janitzia_UMG801_Rev2", "Male_Shipping_Split", "Remote_Distplay",
                                      "Terminal_Block"]
    assert devices.power_supply.inputs == {"A": "L1", "B": "L2", "C": "L3"}
    janitza = devices.power_meters["Janitza UMG 801"]
    assert janitza.wired_by_pins and janitza.voltage_terminals() == {"A": "V1", "B": "VN", "C": "V3"}
    assert [pins["A+"] for pins in janitza.current_pins] == ["I1+", "I5+"]
    assert janitza.supply_pins == {"+": "24V+", "-": "24V-"} and janitza.name_attribute == "NAME"
    roles = block_roles(TEST_SETTINGS, devices)
    assert roles["Janitzia_UMG801_Rev2"] == DEVICE


def test_a_pin_wired_meter_reports_pins_its_block_lacks():
    model = MeterModel("Rev2", "METER2", None, (), voltage_pins={"A": "V1", "B": "VN", "C": "V3"},
                       supply_pins={"+": "24V+", "-": "24V-"})
    assert pairing_problems(model, {"METER2": {"V1": (0, 0), "VN": (0, 5), "24V+": (0, 10)}}) == [
        "Rev2: METER2 has no marker V3, 24V- (named in config/devices.json)."]


def test_device_blocks_keep_every_named_marker_in_the_catalog():
    entry = catalog_entry({"not_flipped": {}}, {"not_flipped": (0, 0, 1, 1)}, [], [],
                          named_markers={"V_B": (0, 0), "V_A": (15, 0)})
    assert entry["markers"] == {"V_A": [15, 0], "V_B": [0, 0]}
