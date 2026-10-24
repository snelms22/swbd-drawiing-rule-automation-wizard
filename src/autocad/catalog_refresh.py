"""Audit Blocks: read every block the configurator uses from the block library and rewrite
catalog/blocks.json (docs/DECISIONS.md, 2026-10-12 "Audit Blocks").

It also CHECKS the blocks and lists problems in plain words (missing or misaligned
connection markers, empty prompts, attribute text that doesn't flip, blocks missing from
the library, and a library open with unsaved changes).
It never changes the library or any existing drawing.

For each block it records:
- connection points from the block's CONN_ point parameters (CONN_A, or CONN_A_TOP /
  CONN_A_BOTTOM on blocks with two ends), for each flip,
- its size (extents), for each flip,
- its visibility states,
- its attributes: tag, prompt (shown as the field label in the app) and default value.

The library is read from a temporary copy in the background (ObjectDBX), so it is never
opened in AutoCAD's window or changed, and this works while someone has it open.

`catalog_entry()` and `audit_problems()` are plain Python so they can be tested without
AutoCAD. `read_library_blocks()` does the reading in AutoCAD.
"""
import json
import os
import shutil
import tempfile
from datetime import date
from pathlib import Path

import pythoncom
import pywintypes
import win32com.client

from src.autocad.connection import _point, _retry, is_flip_setting
from src.model.devices import pairing_problems

PHASES = "ABCN"


# --- Plain Python: build catalog entries ----------------------------------------------

def catalog_entry(markers_by_flip, extents_by_flip, visibility_states, attributes,
                  previous=None, today=None, states=None, named_markers=None) -> dict:
    """markers_by_flip: {"not_flipped": {"CONN_A_TOP": (x, y), ...}, "flipped": {...}}
    (no "flipped" key if the block can't flip). extents_by_flip the same shape, each a
    (left, bottom, right, top). attributes: [{"tag", "prompt", "default"}].
    `previous` is the old entry: its hand-written description is kept."""
    plain = markers_by_flip.get("not_flipped", {})
    entry = {}
    if previous and previous.get("description"):
        entry["description"] = previous["description"]
    entry["source"] = (f"Refreshed {(today or date.today()).isoformat()} from the block library "
                       f"(CONN_ point parameters, attribute definitions).")

    # Two-ended blocks (breakers): CONN_A_TOP ... -> top/bottom terminals, A, B, C order.
    top = [plain[f"CONN_{p}_TOP"] for p in "ABC" if f"CONN_{p}_TOP" in plain]
    bottom = [plain[f"CONN_{p}_BOTTOM"] for p in "ABC" if f"CONN_{p}_BOTTOM" in plain]
    entry["top_terminals"] = [list(point) for point in top]
    entry["bottom_terminals"] = [list(point) for point in bottom]

    # One-ended blocks (input/output): CONN_A ... per flip.
    connections = {}
    for flip, markers in markers_by_flip.items():
        points = {p: list(markers[f"CONN_{p}"]) for p in PHASES if f"CONN_{p}" in markers}
        if points:
            connections[flip] = points
    if connections:
        entry["connections"] = connections

    entry["extents"] = list(extents_by_flip["not_flipped"])
    if "flipped" in extents_by_flip:
        entry["extents_flipped"] = list(extents_by_flip["flipped"])
    entry["visibility_states"] = list(visibility_states)
    entry["attributes"] = [dict(a) for a in attributes]
    if named_markers:
        # Device blocks: every point marker by its own name (decision 2026-10-22).
        entry["markers"] = {name: list(point) for name, point in sorted(named_markers.items())}
    if states:
        # Per visibility state: markers ("CONN_A_L" -> "A_L"; other names as they are) and
        # the visible size.
        entry["states"] = {state: {"markers": {name.removeprefix("CONN_"): list(point)
                                               for name, point in sorted(reading["markers"].items())},
                                   "extents": list(reading["extents"])}
                           for state, reading in states.items()}
    return entry


def describe_changes(old: dict, new: dict) -> list[str]:
    """What changed between two catalogs, in plain words, for the app to show."""
    lines = []
    for name in sorted(set(old) | set(new)):
        if name not in old:
            lines.append(f"{name}: added")
            continue
        if name not in new:
            continue                     # blocks not refreshed are kept, not removed
        # A field that was missing before and is empty now hasn't really changed.
        changed = [key for key in sorted(set(old[name]) | set(new[name]))
                   if key not in ("source", "description")
                   and (old[name].get(key) or None) != (new[name].get(key) or None)]
        if changed:
            lines.append(f"{name}: {', '.join(changed)} changed")
    return lines or ["No changes."]


# --- AutoCAD: read the blocks ---------------------------------------------------------

def _round(point):
    return [round(float(value), 4) for value in point]


def _set_flips(properties, flipped: bool, only: str = ""):
    """Turn the block's flip settings on or off: just `only` if given, else all of them."""
    value = win32com.client.VARIANT(pythoncom.VT_I2, 1 if flipped else 0)   # AutoCAD wants a short
    for prop in properties:
        name = _retry(lambda: prop.PropertyName)
        if (name == only) if only else is_flip_setting(name):
            _retry(lambda: setattr(prop, "Value", value))


def _attribute_positions(reference) -> dict:
    """{tag: (x, y)} of the block's attribute text as currently placed."""
    positions = {}
    if _retry(lambda: reference.HasAttributes):
        for attribute in _retry(lambda: reference.GetAttributes()):
            point = _retry(lambda: attribute.InsertionPoint)
            positions[_retry(lambda: attribute.TagString)] = _round(point[:2])
    return positions


def _visible_extents(reference) -> list[float]:
    """The size of what the block shows in its current visibility state. (AutoCAD's own
    bounding box also counts hidden states, so a scratch copy is exploded and measured.)"""
    xs, ys = [], []
    for part in _retry(lambda: reference.Explode()):
        try:
            low, high = _retry(lambda: part.GetBoundingBox())
            xs += [low[0], high[0]]
            ys += [low[1], high[1]]
        except pywintypes.com_error:
            pass                          # things without a size (e.g. points)
        _retry(lambda: part.Delete())
    return _round((min(xs), min(ys), max(xs), max(ys)))


def _read_states(work, name, states) -> dict:
    """{state: {"markers": {...}, "extents": [...]}} for every visibility state."""
    readings = {}
    for state in states:
        reference = _retry(lambda: work.ModelSpace.InsertBlock(_point(0, 0), name, 1.0, 1.0, 1.0, 0.0))
        for prop in _retry(lambda: reference.GetDynamicBlockProperties()):
            if state in [v for v in (_retry(lambda: prop.AllowedValues) or []) if isinstance(v, str)]:
                _retry(lambda: setattr(prop, "Value", state))
        markers = _named_markers(list(_retry(lambda: reference.GetDynamicBlockProperties())))
        readings[state] = {"markers": markers, "extents": _visible_extents(reference)}
        _retry(lambda: reference.Delete())
    return readings


def _read_one(work, name, visibility="", flip_parameter="") -> dict:
    """Everything the catalog and the audit need from one library block. `visibility` and
    `flip_parameter` (from config) make it read the block the way drawings use it."""
    definition = _retry(lambda: work.Blocks.Item(name))
    attributes = []
    for index in range(_retry(lambda: definition.Count)):
        item = _retry(lambda: definition.Item(index))
        if _retry(lambda: item.ObjectName) == "AcDbAttributeDefinition" and not _retry(lambda: item.Constant):
            attributes.append({
                "tag": _retry(lambda: item.TagString),
                "prompt": _retry(lambda: item.PromptString),
                "default": _retry(lambda: item.TextString),
            })

    reference = _retry(lambda: work.ModelSpace.InsertBlock(_point(0, 0), name, 1.0, 1.0, 1.0, 0.0))
    dynamic = _retry(lambda: reference.IsDynamicBlock)
    properties = list(_retry(lambda: reference.GetDynamicBlockProperties())) if dynamic else []
    visibility_states = []
    for prop in properties:
        allowed = [v for v in (_retry(lambda: prop.AllowedValues) or []) if isinstance(v, str)]
        visibility_states += allowed
        if visibility and visibility in allowed:
            _retry(lambda: setattr(prop, "Value", visibility))
    if visibility:
        properties = list(_retry(lambda: reference.GetDynamicBlockProperties()))
    can_flip =any(is_flip_setting(_retry(lambda: p.PropertyName)) for p in properties)

    reading = {"markers": {}, "extents": {}, "attribute_positions": {},
               "visibility_states": visibility_states, "attributes": attributes,
               "named_markers": _named_markers(properties)}
    for flip in (("not_flipped", "flipped") if can_flip else ("not_flipped",)):
        if can_flip:
            _set_flips(properties, flip == "flipped", flip_parameter)
            properties = list(_retry(lambda: reference.GetDynamicBlockProperties()))
        values = {_retry(lambda: p.PropertyName): p for p in properties}
        markers = {}
        for key in values:
            if key.startswith("CONN_") and key.endswith(" X") and key[:-2] + " Y" in values:
                markers[key[:-2]] = _round((values[key].Value, values[key[:-2] + " Y"].Value))
        reading["markers"][flip] = markers
        low, high = _retry(lambda: reference.GetBoundingBox())
        reading["extents"][flip] = _round((low[0], low[1], high[0], high[1]))
        reading["attribute_positions"][flip] = _attribute_positions(reference)
    return reading


def _named_markers(properties) -> dict:
    """Every point marker ("NAME X" / "NAME Y" pairs), whatever its name."""
    values = {_retry(lambda: p.PropertyName): p for p in properties}
    return {key[:-2]: _round((values[key].Value, values[key[:-2] + " Y"].Value))
            for key in values if key.endswith(" X") and key[:-2] + " Y" in values}


def read_library_blocks(app, library_file, objectdbx_program_id, names,
                        how_used=None, per_state=()) -> tuple[dict, list[str], dict[str, str]]:
    """{block name: reading} for the names found in the library, the missing names, and
    {block name: AutoCAD's error} for blocks AutoCAD failed on while reading them (one
    broken block must not stop the others being read).
    `how_used` is {block name: (visibility state, flip setting)} from block_usage()."""
    how_used = how_used or {}
    library_copy = Path(tempfile.gettempdir()) / f"hyper_configurator_catalog_{os.getpid()}.dwg"
    shutil.copy2(library_file, library_copy)
    library = _retry(lambda: app.GetInterfaceObject(objectdbx_program_id))
    _retry(lambda: library.Open(str(library_copy)))
    work = _retry(lambda: app.GetInterfaceObject(objectdbx_program_id))   # hidden, in memory
    available = {_retry(lambda: library.Blocks.Item(i).Name)
                 for i in range(_retry(lambda: library.Blocks.Count))}
    found = [name for name in names if name in available]
    if found:
        definitions = [_retry(lambda n=n: library.Blocks.Item(n)) for n in found]
        _retry(lambda: library.CopyObjects(
            win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_DISPATCH,
                                    [d._oleobj_ for d in definitions]),
            work.Blocks))
    readings, failed = {}, {}
    for name in found:
        try:
            readings[name] = _read_one(work, name, *how_used.get(name, ("", "")))
            if name in per_state:
                readings[name]["states"] = _read_states(work, name, readings[name]["visibility_states"])
        except pywintypes.com_error as error:
            failed[name] = str(error)
    return readings, [name for name in names if name not in available], failed


# --- Plain Python: the audit checks ---------------------------------------------------

BREAKER = "breaker"            # terminals at both ends: CONN_A_TOP ... CONN_C_BOTTOM
INPUT_OUTPUT = "input/output"  # one end: CONN_A, CONN_B, CONN_C (+ CONN_N), per flip
JUNCTION_DOT = "junction dot"  # no connection markers needed
BREAK_TILDE = "break tilde"    # CONN_A on the A phase; B and C follow 5 apart
FEEDER = "feeder breaker"      # one end: CONN_A, CONN_B, CONN_C stacked (A on top), per flip
LABEL = "label"                # no connection markers needed
DEVICE = "device"              # named markers, paired in config/devices.json
VOLTAGE_TAP = "voltage tap"    # per state; on a vertical run: A, B, C markers from config
CURRENT_TRANSFORMERS = "current transformers"   # per state: CONN_A/B/C + _L, _T, _B


def block_roles(layout_settings, device_settings=None) -> dict[str, str]:
    """What each library block in use is for, from config."""
    roles = {name: DEVICE for name in (device_settings.device_blocks() if device_settings else [])}
    roles.update({name: BREAKER for name in layout_settings.main_breaker.blocks.values()})
    roles[layout_settings.input_output.block] = INPUT_OUTPUT
    roles[layout_settings.input_output.neutral_block] = INPUT_OUTPUT
    roles[layout_settings.main_bus.junction_dot_block] = JUNCTION_DOT
    roles[layout_settings.bus_break.tilde_block] = BREAK_TILDE
    roles[layout_settings.bus_break.bracket_block] = LABEL
    roles[layout_settings.feeder.block] = FEEDER
    roles[layout_settings.current_transformers.block] = CURRENT_TRANSFORMERS
    roles[layout_settings.voltage_taps.block] = VOLTAGE_TAP
    roles[layout_settings.device_pages.wire_break_block] = LABEL
    return roles


def blocks_read_per_state(layout_settings, device_settings=None) -> set[str]:
    """Blocks whose markers and size are read in every visibility state."""
    names = {layout_settings.current_transformers.block, layout_settings.voltage_taps.block,
             layout_settings.bus_break.bracket_block, layout_settings.device_pages.wire_break_block}
    if device_settings is not None and device_settings.fuse is not None:
        names.add(device_settings.fuse.block)
    return names


def block_usage(layout_settings) -> dict[str, tuple[str, str]]:
    """{block: (visibility state, flip setting)} for blocks drawn in one particular state
    and flipped with one particular setting, so the audit reads them the same way."""
    fd = layout_settings.feeder
    return {fd.block: (fd.visibility, fd.mirror_parameter)}


def blocks_in_use(layout_settings, device_settings=None) -> list[str]:
    """Every library block the configurator places, from config."""
    return sorted(block_roles(layout_settings, device_settings))


def _stacked_problem(points, spacing) -> str:
    """Feeder markers: A above B above C, `spacing` apart, in one column."""
    ys = [points[0][1], points[1][1], points[2][1]]
    gaps = [round(ys[0] - ys[1], 3), round(ys[1] - ys[2], 3)]
    if any(abs(gap - spacing) > 0.05 for gap in gaps):
        return (f"A-B-C are {gaps[0]:g} and {gaps[1]:g} apart going down; the bus phases are "
                f"{spacing:g} apart")
    if len({round(p[0], 3) for p in points}) > 1:
        return "A, B and C are not lined up in one column"
    return ""


def _spacing_problem(points, spacing) -> str:
    xs = [points[0][0], points[1][0], points[2][0]]
    gaps = [round(xs[1] - xs[0], 3), round(xs[2] - xs[1], 3)]
    if any(abs(gap - spacing) > 0.05 for gap in gaps):
        return f"A-B-C are {gaps[0]:g} and {gaps[1]:g} apart; the bus phases are {spacing:g} apart"
    if len({round(p[1], 3) for p in points}) > 1:
        return "A, B and C are not at the same height"
    return ""


def audit_problems(name: str, role: str, reading: dict, phase_spacing: float,
                   tap_settings=None) -> list[str]:
    """Problems with one block, in plain words. Empty list = nothing found."""
    problems = []
    markers = reading["markers"]

    if role == VOLTAGE_TAP and tap_settings is not None:
        state = tap_settings.vertical_state
        found = reading.get("states", {}).get(state)
        wanted = tap_settings.vertical_markers
        if found is None:
            problems.append(f'{name}: has no visibility state "{state}" (used on a vertical run).')
        elif any(m not in found["markers"] for m in wanted):
            missing = [m for m in wanted if m not in found["markers"]]
            problems.append(f"{name} ({state}): missing markers {', '.join(missing)}.")
        else:
            xs = [found["markers"][m][0] for m in wanted]
            gaps = [round(xs[1] - xs[0], 3), round(xs[2] - xs[1], 3)]
            if any(abs(gap - phase_spacing) > 0.05 for gap in gaps):
                problems.append(f"{name} ({state}): {', '.join(wanted)} are {gaps[0]:g} and {gaps[1]:g} "
                                f"apart across; the bus phases are {phase_spacing:g} apart.")

    if role == BREAKER:
        plain = markers.get("not_flipped", {})
        for end in ("TOP", "BOTTOM"):
            needed = [f"CONN_{p}_{end}" for p in "ABC"]
            missing = [m for m in needed if m not in plain]
            if missing:
                problems.append(f"{name}: missing connection markers {', '.join(missing)}.")
            else:
                issue = _spacing_problem([plain[m] for m in needed], phase_spacing)
                if issue:
                    problems.append(f"{name}: {end.lower()} markers: {issue}.")
    elif role == INPUT_OUTPUT:
        for flip, points in markers.items():
            needed = [f"CONN_{p}" for p in "ABC"]
            missing = [m for m in needed if m not in points]
            if missing:
                problems.append(f"{name} ({flip.replace('_', ' ')}): missing connection markers "
                                f"{', '.join(missing)}.")
            else:
                issue = _spacing_problem([points[m] for m in needed], phase_spacing)
                if issue:
                    problems.append(f"{name} ({flip.replace('_', ' ')}): {issue}.")

    elif role == FEEDER:
        for flip, points in markers.items():
            needed = [f"CONN_{p}" for p in "ABC"]
            missing = [m for m in needed if m not in points]
            if missing:
                problems.append(f"{name} ({flip.replace('_', ' ')}): missing connection markers "
                                f"{', '.join(missing)}.")
            else:
                issue = _stacked_problem([points[m] for m in needed], phase_spacing)
                if issue:
                    problems.append(f"{name} ({flip.replace('_', ' ')}): {issue}.")
        if "flipped" not in markers:
            problems.append(f"{name}: has no flip/mirror setting, so right-side breakers can't "
                            f"be drawn.")

    # A prompt that repeats the default is fine (it shows the expected format); only an
    # empty prompt leaves the field without a label (decision 2026-10-12).
    if role == BREAK_TILDE:
        for flip, points in markers.items():
            if "CONN_A" not in points:
                problems.append(f"{name} ({flip.replace('_', ' ')}): missing connection marker CONN_A.")

    # Markers sit on the block's terminals, so they are always within its outline. One
    # outside it (usually after a flip) was left out of the flip action.
    for flip, points in markers.items():
        outline = reading["extents"].get(flip)
        if not outline:
            continue
        left, bottom, right, top = outline
        outside = sorted(m for m, (x, y) in points.items()
                         if not (left - 0.05 <= x <= right + 0.05 and bottom - 0.05 <= y <= top + 0.05))
        if outside:
            problems.append(f"{name} ({flip.replace('_', ' ')}): connection markers "
                            f"{', '.join(outside)} are outside the block. Add them to the flip "
                            f"action so they move with the terminals.")

    tags = [a["tag"] for a in reading["attributes"]]
    repeated = sorted({tag for tag in tags if tags.count(tag) > 1})
    if repeated:
        problems.append(f"{name}: several attributes share the tag {', '.join(repeated)}; the "
                        f"configurator can only give them all the same text.")

    # Break blocks are filled in by the configurator itself, so their prompts never show.
    filled_automatically = role in (BREAK_TILDE, LABEL)
    weak = [a["tag"] for a in reading["attributes"] if not a["prompt"].strip()]
    if weak and not filled_automatically:
        problems.append(f"{name}: these attributes have no prompt, so their field in the app "
                        f"will only show the tag: {', '.join(weak)}.")

    positions = reading.get("attribute_positions", {})
    if "flipped" in positions:
        stuck = [tag for tag, point in positions["not_flipped"].items()
                 if positions["flipped"].get(tag) == point]
        if stuck:
            problems.append(f"{name}: attribute text doesn't move when the block flips "
                            f"({', '.join(stuck)}). Add the attributes to the flip action so the "
                            f"text stays clear of the bus.")
    return problems


def library_unsaved_problem(app, library_file) -> str:
    """The audit reads the last SAVED library. Warn if it is open with unsaved changes."""
    wanted = str(library_file).replace("/", "\\").lower()
    documents = _retry(lambda: app.Documents)
    for index in range(_retry(lambda: documents.Count)):
        document = _retry(lambda: documents.Item(index))
        if _retry(lambda: document.FullName).replace("/", "\\").lower() == wanted \
                and not _retry(lambda: document.Saved):
            return ("The block library is open in AutoCAD with unsaved changes. This audit read "
                    "the last saved version; save the library and run Audit Blocks again.")
    return ""


# --- The one-click audit --------------------------------------------------------------

def audit_blocks(app, layout_settings, autocad_settings, catalog_file,
                 device_settings=None) -> tuple[list[str], list[str]]:
    """Re-read the blocks in use, rewrite the catalog, and check the blocks.
    Returns (what changed in the catalog, problems found)."""
    catalog_file = Path(catalog_file)
    data = json.loads(catalog_file.read_text(encoding="utf-8"))
    old_blocks = data.get("blocks", {})
    roles = block_roles(layout_settings, device_settings)

    problems = []
    unsaved = library_unsaved_problem(app, autocad_settings.block_library_file)
    if unsaved:
        problems.append(unsaved)

    readings, missing, failed = read_library_blocks(app, autocad_settings.block_library_file,
                                            autocad_settings.objectdbx_program_id, sorted(roles),
                                            block_usage(layout_settings),
                                            blocks_read_per_state(layout_settings, device_settings))
    new_blocks = dict(old_blocks)
    for name, reading in readings.items():
        named = reading.get("named_markers") if roles[name] == DEVICE else None
        new_blocks[name] = catalog_entry(reading["markers"], reading["extents"],
                                         reading["visibility_states"], reading["attributes"],
                                         old_blocks.get(name), states=reading.get("states"),
                                         named_markers=named)
        problems += audit_problems(name, roles[name], reading, layout_settings.main_bus.phase_spacing,
                                   layout_settings.voltage_taps)
    if device_settings is not None:
        # Do the meters' input blocks connect where config says? (decision 2026-10-22)
        device_markers = {name: {m: tuple(p) for m, p in entry.get("markers", {}).items()}
                          for name, entry in new_blocks.items() if roles.get(name) == DEVICE}
        for model in device_settings.power_meters.values():
            problems += pairing_problems(model, device_markers)
    problems += [f"{name}: not found in the block library." for name in missing]
    problems += [f"{name}: AutoCAD failed while reading it (often a flip or visibility "
                 f"parameter it can't set); its catalog entry was kept as it was. "
                 f"Check it in the Block Editor. ({error})" for name, error in failed.items()]

    data["blocks"] = new_blocks
    data["note"] = ("Library blocks the configurator uses: connection points (from CONN_ point "
                    "parameters), sizes, visibility states and attributes. Written by "
                    "'Audit Blocks' in the app; do not edit by hand except 'description'.")
    catalog_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    changes = describe_changes(old_blocks, {name: new_blocks[name] for name in readings})
    return changes, problems
