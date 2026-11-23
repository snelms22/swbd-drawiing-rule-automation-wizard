"""Turns one laid-out page into a list of simple shapes (lines, polylines, text), each on
its layer, in frame-relative coordinates.

Pure Python, no AutoCAD: everything here is decided by the layout (src/layout/), and this
module only translates it into shapes. connection.py then sends the shapes to AutoCAD.
Keeping the two apart means this part can be tested without AutoCAD.
"""
from dataclasses import dataclass, field

ROUNDING_TOLERANCE = 1e-9
MTEXT_NEW_LINE = "\\P"      # AutoCAD MText's code for "start a new line"


@dataclass
class Line:
    layer: str
    start: tuple[float, float]
    end: tuple[float, float]


@dataclass
class Polyline:
    layer: str
    points: list[tuple[float, float]]
    closed: bool = False
    width: float = 0.0              # constant width (e.g. a terminal bridge, 0.5); 0 = a plain line


@dataclass
class BlockInsert:
    layer: str
    block: str
    position: tuple[float, float]           # base point; always scale 1
    attributes: dict[str, str]
    visibility: str = ""                    # dynamic visibility state; "" = leave as is
    flipped: bool = False                   # set the block's flip parameters
    flip_parameter: str = ""                # only this one when flipped; "" = all of them
    distances: dict = field(default_factory=dict)   # dynamic distance settings, {name: value}
    rotation: float = 0.0                   # degrees, counter-clockwise (the ground strip: -90)


@dataclass
class Text:
    layer: str
    text: str
    position: tuple[float, float]   # the point named by `align`
    height: float
    style: str
    align: str                      # "bottom_left", "bottom_center", "middle_left", "middle_right", "middle_center"
    background_mask: bool = False   # hide what is behind the text (e.g. a dashed line through it)
    rotation: float = 0.0           # degrees, counter-clockwise (an upright wire's label: 90)


def page_shapes(page, settings, placeholder_layer: str) -> list:
    """All shapes for one page. `settings` is the LayoutSettings."""
    parts = page.parts
    shapes = []
    for path in parts.bus_paths:
        shapes += _bus_shapes(path, settings)
    shapes += _divider_shapes(parts.dividers, settings)
    shapes += _ground_shapes(parts.ground_bus, settings)
    shapes += _section_label_shapes(parts.section_labels, settings)
    shapes += _placeholder_shapes(parts.content_boxes, placeholder_layer)
    shapes += [Line(settings.main_bus.layer, line.start, line.end) for line in parts.bus_lines]
    shapes += [BlockInsert(b.layer, b.block, b.position, dict(b.attributes), b.visibility,
                           b.flipped, b.flip_parameter, dict(b.distances), b.rotation)
               for b in parts.blocks]
    shapes += [Line(wire.layer, wire.start, wire.end) for wire in parts.wires]
    shapes += [Polyline(p.layer, list(p.points), width=p.width) for p in parts.polylines]
    shapes += [Text(t.layer, t.text, (t.x, t.y), t.height, settings.text.style, t.align) for t in parts.texts]
    w = settings.wire_labels
    shapes += [Text(w.layer, label.text, (label.x, label.y), w.height, settings.text.style, "middle_center",
                    rotation=label.rotation) for label in parts.wire_labels]
    shapes += _waiting_block_shapes(parts.placeholders, placeholder_layer, settings)
    shapes += _note_shapes(parts.notes, settings)
    shapes += _interlock_shapes(parts.interlocks, settings)
    if parts.title:
        t = settings.page_title
        shapes.append(Text(t.layer, t.mtext_format.format(title=parts.title), (t.x, t.y), t.height,
                           settings.text.style, "middle_right"))
    return shapes


# --- Main bus -------------------------------------------------------------------------

def phase_paths(bus_path, phase_spacing) -> dict[str, list[tuple[float, float]]]:
    """The A, B and C lines for a bus centre line (B).

    Convention from the references: A is above B on horizontal runs and LEFT of B on
    vertical runs; C is the opposite. At a corner a phase takes its x shift from the
    vertical run and its y shift from the horizontal run, so the phases stay parallel.
    (Where the bus steps DOWN, A and C cross without connecting, as in the references.)
    """
    points = _without_repeats(bus_path)
    paths = {}
    for phase, offset in (("A", phase_spacing), ("B", 0.0), ("C", -phase_spacing)):
        shifted = []
        for index, (x, y) in enumerate(points):
            touches_vertical = touches_horizontal = False
            for neighbour in (index - 1, index + 1):
                if 0 <= neighbour < len(points):
                    nx, ny = points[neighbour]
                    if abs(nx - x) < ROUNDING_TOLERANCE:
                        touches_vertical = True
                    else:
                        touches_horizontal = True
            shifted.append((x - offset if touches_vertical else x,
                            y + offset if touches_horizontal else y))
        paths[phase] = shifted
    return paths


def _without_repeats(points):
    cleaned = []
    for point in points:
        if not cleaned or (abs(point[0] - cleaned[-1][0]) > ROUNDING_TOLERANCE
                           or abs(point[1] - cleaned[-1][1]) > ROUNDING_TOLERANCE):
            cleaned.append(point)
    return cleaned


def _bus_shapes(bus_path, settings):
    if len(bus_path) < 2:
        return []
    paths = phase_paths(bus_path, settings.main_bus.phase_spacing)
    return [Polyline(settings.main_bus.layer, paths[phase]) for phase in ("A", "B", "C")]


# --- Page parts -----------------------------------------------------------------------

def _divider_shapes(dividers, settings):
    return [Line(settings.divider.layer, (d.x, d.bottom_y), (d.x, d.top_y)) for d in dividers]


def _ground_shapes(ground, settings):
    if ground is None:
        return []
    g = settings.ground_bus
    shapes = [Line(g.layer, (ground.start_x, ground.y), (ground.end_x, ground.y))]
    # Ground symbol: stem down from the bus, then bars getting narrower.
    stem_x = ground.start_x + g.symbol_offset_x
    stem_bottom_y = ground.y - g.symbol_stem_length
    shapes.append(Line(g.layer, (stem_x, ground.y), (stem_x, stem_bottom_y)))
    for index, width in enumerate(g.symbol_bar_widths):
        bar_y = stem_bottom_y - index * g.symbol_bar_spacing
        shapes.append(Line(g.layer, (stem_x - width / 2, bar_y), (stem_x + width / 2, bar_y)))
    t = settings.text
    shapes.append(Text(
        t.layer, g.label_text, (ground.start_x + g.label_offset_x, ground.y + g.label_gap_above_bus),
        t.height, t.style, "bottom_left",
    ))
    return shapes


def _section_label_shapes(labels, settings):
    t = settings.text
    return [Text(t.layer, label.text, (label.center_x, label.bottom_y), t.height, t.style,
                 "bottom_center") for label in labels]


def _note_shapes(notes, settings):
    """Plain notes (e.g. provisions): one MText each. MText starts a new line at "\\P"."""
    t = settings.text
    return [Text(t.layer, MTEXT_NEW_LINE.join(note.lines), (note.x, note.middle_y), t.height, t.style,
                 note.align) for note in notes]


def _interlock_shapes(interlocks, settings):
    """Each interlock: its dashed line (the layer's linetype) and its text centred on it."""
    s, t = settings.interlocks, settings.text
    shapes = []
    for line in interlocks:
        shapes.append(Polyline(s.layer, line.points))
        shapes.append(Text(t.layer, MTEXT_NEW_LINE.join(line.text_lines), (line.text_x, line.text_y),
                           t.height, t.style, "middle_center", background_mask=s.background_mask))
    return shapes


def _waiting_block_shapes(placeholders, layer, settings):
    """Boxes (with a name) where a block will go once it's ready, e.g. the input block."""
    shapes = []
    for box in placeholders:
        corners = [(box.left_x, box.bottom_y), (box.right_x, box.bottom_y),
                   (box.right_x, box.top_y), (box.left_x, box.top_y)]
        shapes.append(Polyline(layer, corners, closed=True))
        # A name on two lines (e.g. a trip unit and its COM190) is one MText: \P breaks a line.
        shapes.append(Text(layer, box.text.replace("\n", "\\P"), ((box.left_x + box.right_x) / 2, box.bottom_y + 1.0),
                           settings.text.height, settings.text.style, "bottom_center"))
    return shapes


def _placeholder_shapes(content_boxes, layer):
    shapes = []
    for box in content_boxes:
        corners = [(box.left_x, box.bottom_y), (box.right_x, box.bottom_y),
                   (box.right_x, box.top_y), (box.left_x, box.top_y)]
        shapes.append(Polyline(layer, corners, closed=True))
    return shapes
