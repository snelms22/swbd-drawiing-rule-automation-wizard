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
    assert devices.device_blocks() == ["3P_2P_FUSE_DISCONECT", "3P_PWR_SUP", "CT_Current_Input",
                                      "Female_Shipping_Split", "Janitza_UMG801", "Male_Shipping_Split",
                                      "Remote_Distplay", "Voltage_UMG801_Input"]
    assert devices.power_supply.inputs == {"A": "L1", "B": "L2", "C": "L3"}
    janitza = devices.power_meters["Janitza UMG 801"]
    assert janitza.voltage_input.lands_on == {"V_A": "V1", "V_B": "VN", "V_C": "V3"}
    assert [i.lands_on["CT_A+"] for i in janitza.current_inputs] == ["I1+", "I5+"]
    roles = block_roles(TEST_SETTINGS, devices)
    assert roles["Janitza_UMG801"] == DEVICE


def test_device_blocks_keep_every_named_marker_in_the_catalog():
    entry = catalog_entry({"not_flipped": {}}, {"not_flipped": (0, 0, 1, 1)}, [], [],
                          named_markers={"V_B": (0, 0), "V_A": (15, 0)})
    assert entry["markers"] == {"V_A": [15, 0], "V_B": [0, 0]}
