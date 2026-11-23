"""Talking to AutoCAD over COM (pywin32). The only module that calls AutoCAD directly.

It does what it is told: open a drawing, find frames, make layers, add the shapes from
draw_page.py, save. It makes no layout decisions.
"""
import math
import os
import shutil
import tempfile
import time
from pathlib import Path

import pythoncom
import pywintypes
import win32com.client

from src.autocad.draw_page import BlockInsert, Line, Polyline, Text

# AutoCAD sometimes refuses a call while it is busy ("call was rejected by callee"). That
# is temporary, so such calls are retried a few times before giving up.
CALL_REJECTED = -2147418111
RETRIES = 20
RETRY_PAUSE_SECONDS = 0.25

# A block's flip settings are found by name: AutoCAD's default "Flip state1", ..., or
# "MIRROR-3W" / "MIRROR-4W" on the feeder breaker. All of them are turned on together,
# unless config names the one to use (the feeder: one mirror per visibility state).
FLIP_NAME_STARTS = ("flip", "mirror")


def is_flip_setting(property_name: str) -> bool:
    return property_name.lower().startswith(FLIP_NAME_STARTS)


# AutoCAD's numbers for MText attachment points.
ATTACH = {"middle_left": 4, "middle_center": 5, "middle_right": 6, "bottom_left": 7, "bottom_center": 8}


class AutocadBusyError(RuntimeError):
    """AutoCAD kept refusing calls: it is waiting on something the user has open."""


BUSY_MESSAGE = ("AutoCAD is busy and won't take commands. Usually a command is still running, "
                "a dialog box is open, or the Block Editor is open. Press Esc in AutoCAD, close "
                "any dialogs or the Block Editor, then try again.")


def _retry(action):
    last_error = None
    for attempt in range(RETRIES):
        try:
            return action()
        except pywintypes.com_error as error:
            if error.hresult != CALL_REJECTED:
                raise
            last_error = error
        except AttributeError as error:
            # While AutoCAD is busy, Python briefly can't see an object's properties
            # ("<unknown>.Count"). That passes on its own once AutoCAD is free.
            last_error = error
        time.sleep(RETRY_PAUSE_SECONDS)
    # The original error is kept in the message in case it was something else.
    raise AutocadBusyError(f"{BUSY_MESSAGE}\n(Details: {last_error})")


def _point(x, y):
    """A 3D point in the form AutoCAD's COM interface expects."""
    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, (float(x), float(y), 0.0))


def _flat_2d(points):
    """[(x, y), ...] -> the flat list of doubles AddLightWeightPolyline expects."""
    coordinates = []
    for x, y in points:
        coordinates += [float(x), float(y)]
    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, coordinates)


class AutocadSession:
    def __init__(self, program_id: str):
        """Use the AutoCAD that is already open, or start it. program_id picks the version
        (e.g. AutoCAD 2026), so AutoCAD Electrical is never used by accident."""
        try:
            self.app = win32com.client.GetActiveObject(program_id)
        except pywintypes.com_error:
            self.app = win32com.client.Dispatch(program_id)
        _retry(lambda: setattr(self.app, "Visible", True))

    def open(self, path) -> "Drawing":
        _retry(lambda: self.app.Documents.Open(str(path)))
        # What Documents.Open hands back is not always usable over COM, so look the drawing
        # up in AutoCAD's list of open documents by its full path instead.
        wanted = str(path).lower()
        active = _retry(lambda: self.app.ActiveDocument)
        if _retry(lambda: active.FullName).lower() == wanted:
            return Drawing(active, self.app)
        documents = _retry(lambda: self.app.Documents)
        for index in range(_retry(lambda: documents.Count)):
            document = _retry(lambda: documents.Item(index))
            if _retry(lambda: document.FullName).lower() == wanted:
                return Drawing(document, self.app)
        raise RuntimeError(f"AutoCAD did not open {path}")


class Drawing:
    def __init__(self, document, app):
        self.document = document
        # Right after opening, AutoCAD can still be busy with the drawing (2026-10-22).
        self.model_space = _retry(lambda: document.ModelSpace)
        self.app = app

    # --- Reading -----------------------------------------------------------------------

    def find_frames(self, block_name: str, name_attribute: str) -> list[tuple[str, float, float]]:
        """(frame name, insertion x, insertion y) for every insert of the frame block."""
        frames = []
        count = _retry(lambda: self.model_space.Count)
        for index in range(count):
            entity = _retry(lambda: self.model_space.Item(index))
            if _retry(lambda: entity.ObjectName) != "AcDbBlockReference":
                continue
            if _retry(lambda: entity.EffectiveName) != block_name:
                continue
            name = ""
            for attribute in _retry(lambda: entity.GetAttributes()):
                if _retry(lambda: attribute.TagString) == name_attribute:
                    name = _retry(lambda: attribute.TextString)
            x, y, _ = _retry(lambda: entity.InsertionPoint)
            frames.append((name, x, y))
        return frames

    def layout_names(self) -> list[str]:
        layouts = _retry(lambda: self.document.Layouts)
        return [_retry(lambda: layouts.Item(i).Name) for i in range(_retry(lambda: layouts.Count))]

    def text_style_names(self) -> list[str]:
        styles = _retry(lambda: self.document.TextStyles)
        return [_retry(lambda: styles.Item(i).Name) for i in range(_retry(lambda: styles.Count))]

    def block_names(self) -> set[str]:
        blocks = _retry(lambda: self.document.Blocks)
        return {_retry(lambda: blocks.Item(i).Name) for i in range(_retry(lambda: blocks.Count))}

    # --- Writing -----------------------------------------------------------------------

    def import_blocks(self, names, library_file, objectdbx_program_id) -> list[str]:
        """Copy the block definitions the program inserts from the library drawing. The
        library's version always wins (decision 2026-10-23): a block of the same name that
        came with the template is renamed "<name>_TEMPLATE" first, so what the template drew
        with it (e.g. the legend) keeps its look, and new inserts get the library's version.
        The library is read in the background (ObjectDBX): it is never opened in AutoCAD's
        window and never changed. Returns the names that are missing from the library."""
        needed = sorted(set(names))
        if not needed:
            return []
        # Read a temporary copy of the saved library: AutoCAD can't read the library file
        # itself while someone has it open for editing.
        library_copy = Path(tempfile.gettempdir()) / f"hyper_configurator_library_{os.getpid()}.dwg"
        shutil.copy2(library_file, library_copy)
        library = _retry(lambda: self.app.GetInterfaceObject(objectdbx_program_id))
        _retry(lambda: library.Open(str(library_copy)))
        library_names = {_retry(lambda: library.Blocks.Item(i).Name)
                         for i in range(_retry(lambda: library.Blocks.Count))}
        found = [name for name in needed if name in library_names]
        present = self.block_names()
        for name in found:
            if name in present:
                old_name = f"{name}_TEMPLATE"
                while old_name in present:
                    old_name += "_"
                _retry(lambda n=name, o=old_name: setattr(self.document.Blocks.Item(n), "Name", o))
                present.add(old_name)
        if found:
            definitions = [_retry(lambda n=n: library.Blocks.Item(n)) for n in found]
            # Pass the raw COM objects: with the wrapped ones, a list of exactly ONE block
            # fails in AutoCAD with "Incorrect SafeArray dimension".
            objects = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_DISPATCH,
                                              [d._oleobj_ for d in definitions])
            _retry(lambda: library.CopyObjects(objects, self.document.Blocks))
        return [name for name in needed if name not in library_names]

    def ensure_layer(self, name: str, color: int | None = None, plottable: bool = True):
        """Use the layer if the template has it (keeping its colour and linetype); create it
        otherwise. Colour/plot settings are only applied to layers this program owns."""
        layers = _retry(lambda: self.document.Layers)
        existing = {_retry(lambda: layers.Item(i).Name).upper()
                    for i in range(_retry(lambda: layers.Count))}
        layer = _retry(lambda: layers.Add(name))
        if name.upper() not in existing:
            if color is not None:
                _retry(lambda: setattr(layer, "Color", color))
            _retry(lambda: setattr(layer, "Plottable", plottable))
        return name.upper() not in existing

    def add_shapes(self, shapes, offset_x: float, offset_y: float):
        """Add shapes, moving them from frame-relative to drawing coordinates."""
        def moved(point):
            return point[0] + offset_x, point[1] + offset_y

        problems = []
        for shape in shapes:
            if isinstance(shape, BlockInsert):
                entity = _retry(lambda: self.model_space.InsertBlock(
                    _point(*moved(shape.position)), shape.block, 1.0, 1.0, 1.0, 0.0))
                problems += self._fill_block(entity, shape)
            elif isinstance(shape, Line):
                entity = _retry(lambda: self.model_space.AddLine(
                    _point(*moved(shape.start)), _point(*moved(shape.end))))
            elif isinstance(shape, Polyline):
                entity = _retry(lambda: self.model_space.AddLightWeightPolyline(
                    _flat_2d([moved(p) for p in shape.points])))
                if shape.closed:
                    _retry(lambda: setattr(entity, "Closed", True))
                if shape.width:
                    _retry(lambda: setattr(entity, "ConstantWidth", shape.width))
            elif isinstance(shape, Text):
                entity = self._add_text(shape, moved(shape.position))
            else:
                raise TypeError(f"Unknown shape: {shape!r}")
            _retry(lambda: setattr(entity, "Layer", shape.layer))
        return problems

    def _fill_block(self, reference, shape: BlockInsert) -> list[str]:
        """Set the block's visibility state, its text, its flips and its stretches, in that
        order. Never scales or explodes."""
        problems = []
        if shape.visibility and _retry(lambda: reference.IsDynamicBlock):
            # Blocks name their visibility setting differently, so find the setting by the
            # state we want (decision 2026-10-12: a state is just what it is called).
            states_seen = []
            for prop in _retry(lambda: reference.GetDynamicBlockProperties()):
                allowed = [value for value in (_retry(lambda: prop.AllowedValues) or [])
                           if isinstance(value, str)]
                states_seen += allowed
                if shape.visibility in allowed:
                    _retry(lambda: setattr(prop, "Value", shape.visibility))
                    break
            else:
                problems.append(f'Block {shape.block} has no visibility state '
                                f'"{shape.visibility}" (it has: {", ".join(states_seen) or "none"}).')
        # The text goes in before the flip (Sammy, 2026-11-19): set after it, a flipped bracket's
        # label didn't land where the block puts it, though the block itself is right.
        if shape.attributes and _retry(lambda: reference.HasAttributes):
            for attribute in _retry(lambda: reference.GetAttributes()):
                tag = _retry(lambda: attribute.TagString)
                if tag in shape.attributes:
                    self._set_attribute_text(attribute, shape.attributes[tag])
        if shape.flipped:
            # AutoCAD only accepts a "short" whole number for flip settings.
            flip_on = win32com.client.VARIANT(pythoncom.VT_I2, 1)
            flips = [prop for prop in _retry(lambda: reference.GetDynamicBlockProperties())
                     if (_retry(lambda: prop.PropertyName) == shape.flip_parameter
                         if shape.flip_parameter
                         else is_flip_setting(_retry(lambda: prop.PropertyName)))]
            if not flips:
                wanted = f'"{shape.flip_parameter}"' if shape.flip_parameter else "flip"
                problems.append(f"Block {shape.block} should be flipped but has no {wanted} parameter.")
            for prop in flips:
                _retry(lambda: setattr(prop, "Value", flip_on))
        if shape.distances:
            # A stretch the block itself draws, e.g. a bracket reaching its outer wires.
            settings = {_retry(lambda: prop.PropertyName): prop
                        for prop in _retry(lambda: reference.GetDynamicBlockProperties())}
            for name, value in shape.distances.items():
                if name in settings:
                    _retry(lambda: setattr(settings[name], "Value", float(value)))
                else:
                    problems.append(f'Block {shape.block} has no "{name}" setting to stretch it with.')
        return problems

    @staticmethod
    def _set_attribute_text(attribute, text):
        """Write an attribute's text. Lines the layout broke ("\\n", e.g. a tilde's two lines,
        Sammy 2026-11-20) become AutoCAD's line breaks in a multi-line attribute, whose box is
        set to no width so AutoCAD never wraps the text again on its own: the lines are the
        layout's, as in the preview. A single-line attribute gets them joined by spaces."""
        if "\n" in text:
            if _retry(lambda: attribute.MTextAttribute):
                _retry(lambda: setattr(attribute, "MTextBoundaryWidth", 0.0))
                text = text.replace("\n", "\\P")
            else:
                text = text.replace("\n", " ")
        _retry(lambda: setattr(attribute, "TextString", text))

    def _add_text(self, shape: Text, position):
        insertion = _point(*position)
        text = _retry(lambda: self.model_space.AddMText(insertion, 0.0, shape.text))
        _retry(lambda: setattr(text, "StyleName", shape.style))
        _retry(lambda: setattr(text, "Height", shape.height))
        _retry(lambda: setattr(text, "AttachmentPoint", ATTACH[shape.align]))
        # Changing the attachment point moves the text, so put it back where it belongs.
        _retry(lambda: setattr(text, "InsertionPoint", insertion))
        if shape.rotation:
            _retry(lambda: setattr(text, "Rotation", math.radians(shape.rotation)))
        if shape.background_mask:
            # Filled with the drawing's background colour, as in Sabey-011486's interlock text.
            _retry(lambda: setattr(text, "BackgroundFill", True))
        return text

    def set_frame_attribute(self, block_name: str, name_attribute: str, tag: str,
                            values: dict[str, str]) -> list[str]:
        """Write `tag` on each frame named in `values` ({frame name: text}), e.g. the page
        numbers. Returns the frame names not found in the drawing."""
        not_found = set(values)
        count = _retry(lambda: self.model_space.Count)
        for index in range(count):
            entity = _retry(lambda: self.model_space.Item(index))
            if _retry(lambda: entity.ObjectName) != "AcDbBlockReference":
                continue
            if _retry(lambda: entity.EffectiveName) != block_name:
                continue
            attributes = _retry(lambda: entity.GetAttributes())
            name = next((_retry(lambda: a.TextString) for a in attributes
                         if _retry(lambda: a.TagString) == name_attribute), "")
            if name not in values:
                continue
            for attribute in attributes:
                if _retry(lambda: attribute.TagString) == tag:
                    _retry(lambda: setattr(attribute, "TextString", values[name]))
                    not_found.discard(name)
        return sorted(not_found)

    def set_drawing_properties(self, values: dict[str, str]):
        """Set the drawing's custom properties (DWGPROPS), adding any that are missing.
        Fields in the template (e.g. the title block) show them after a regen."""
        info = _retry(lambda: self.document.SummaryInfo)
        existing = {_retry(lambda i=i: info.GetCustomByIndex(i))[0]
                    for i in range(_retry(lambda: info.NumCustomInfo()))}
        for key, value in values.items():
            if key in existing:
                _retry(lambda: info.SetCustomByKey(key, value))
            else:
                _retry(lambda: info.AddCustomInfo(key, value))

    def regenerate(self, open_on: str):
        """Regenerate the Model tab and then the page the drawing opens on (`open_on`).

        Fields (title block text from the drawing properties) update on a regen. And AutoCAD
        only regenerates the space that is showing: the drawing is made while a page is
        showing, so without a regen in Model the Model tab kept its old picture (the
        template's empty frames) until the person typed REGEN (2026-10-26). Switching tabs
        doesn't move the view, so Model still opens where the template left it."""
        layouts = _retry(lambda: self.document.Layouts)
        for name in ("Model", open_on):
            _retry(lambda: setattr(self.document, "ActiveLayout", layouts.Item(name)))
            _retry(lambda: self.document.Regen(1))      # 1 = all viewports

    def keep_only_layouts(self, keep: list[str], open_on: str) -> list[str]:
        """Keep the layouts in `keep`, with their tabs in that order, and delete every other
        layout. The drawing opens on `open_on`. Returns the names deleted."""
        layouts = _retry(lambda: self.document.Layouts)
        names = [_retry(lambda i=i: layouts.Item(i).Name) for i in range(_retry(lambda: layouts.Count))]
        if open_on in names:
            _retry(lambda: setattr(self.document, "ActiveLayout", layouts.Item(open_on)))
        deleted = []
        for name in names:
            if name != "Model" and name not in keep:
                _retry(lambda: layouts.Item(name).Delete())
                deleted.append(name)
        for tab, name in enumerate((name for name in keep if name in names), start=1):
            _retry(lambda: setattr(layouts.Item(name), "TabOrder", tab))     # Model is tab 0
        return deleted

    def save(self):
        _retry(lambda: self.document.Save())
