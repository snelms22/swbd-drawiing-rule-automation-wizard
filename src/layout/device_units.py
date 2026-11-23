"""The pieces a device page is drawn with: wires, their labels, plain text, wide polylines
(terminal bridges) and the Unit that holds a group of them. Shared by device_pages.py (meters,
fuses, power supplies) and power_ladder.py (the 24 V ladder). Pure Python, no geometry rules.
"""
from dataclasses import dataclass, field

from src.layout.main_breakers import BlockPlacement, Placeholder

TOLERANCE = 1e-6


@dataclass
class Wire:
    """A wire the program draws itself (no block), on its own layer. Every straight piece of
    one wire run carries the run's label ("4A002"; "" = not labelled)."""
    layer: str
    start: tuple[float, float]
    end: tuple[float, float]
    label: str = ""


@dataclass
class WireLabel:
    """A wire's label on the page (decision 2026-11-09): its middle, and turned 90 degrees
    on an upright wire."""
    text: str
    x: float
    y: float
    rotation: float = 0.0


@dataclass
class PageText:
    """Plain text on a page, e.g. a terminal strip's name "1TB24+" (Sammy, 2026-11-16)."""
    text: str
    x: float
    y: float
    layer: str
    height: float
    align: str = "bottom_center"


@dataclass
class WidePolyline:
    """A polyline with a width, e.g. the bridge joining terminals (Sammy, 2026-11-13)."""
    layer: str
    points: list
    width: float


@dataclass
class Unit:
    """One meter with what is wired to it, one fuse on its own, or one page of a section's
    24 V ladder, drawn around (0, 0)."""
    section_number: int
    names: list = field(default_factory=list)       # device names placed here ("PM-1", "FA-12")
    blocks: list = field(default_factory=list)
    wires: list = field(default_factory=list)
    placeholders: list = field(default_factory=list)
    texts: list = field(default_factory=list)       # PageTexts
    polylines: list = field(default_factory=list)   # WidePolylines
    new_page: bool = False                          # starts a page of its own (a ladder's next page)

    def is_empty(self) -> bool:
        return not (self.blocks or self.wires or self.placeholders or self.texts or self.polylines)

    def extents(self):
        xs, ys = [], []
        for b in self.blocks:
            left, bottom, right, top = b.extents
            xs += [b.position[0] + left, b.position[0] + right]
            ys += [b.position[1] + bottom, b.position[1] + top]
        for w in self.wires:
            xs += [w.start[0], w.end[0]]
            ys += [w.start[1], w.end[1]]
        for p in self.placeholders:
            xs += [p.left_x, p.right_x]
            ys += [p.bottom_y, p.top_y]
        for t in self.texts:
            xs.append(t.x)
            ys += [t.y, t.y + t.height]
        for line in self.polylines:
            xs += [x for x, _ in line.points]
            ys += [y for _, y in line.points]
        return min(xs), min(ys), max(xs), max(ys)


def moved_block(b, dx, dy) -> BlockPlacement:
    return BlockPlacement(block=b.block, layer=b.layer, position=(b.position[0] + dx, b.position[1] + dy),
                          attributes=dict(b.attributes), visibility=b.visibility, label=b.label,
                          extents=b.extents, flipped=b.flipped, flip_parameter=b.flip_parameter,
                          distances=dict(b.distances), rotation=b.rotation)


def moved_wire(w, dx, dy) -> Wire:
    return Wire(w.layer, (w.start[0] + dx, w.start[1] + dy), (w.end[0] + dx, w.end[1] + dy), w.label)


def add_unit_to(target, source, dx, dy):
    """Put one unit's contents into another, moved by (dx, dy) (e.g. a meter drawn in the
    24 V ladder)."""
    target.names += source.names
    target.blocks += [moved_block(b, dx, dy) for b in source.blocks]
    target.wires += [moved_wire(w, dx, dy) for w in source.wires]
    target.placeholders += [Placeholder(p.text, p.left_x + dx, p.bottom_y + dy, p.right_x + dx, p.top_y + dy)
                            for p in source.placeholders]
    target.texts += [PageText(t.text, t.x + dx, t.y + dy, t.layer, t.height, t.align) for t in source.texts]
    target.polylines += [WidePolyline(p.layer, [(x + dx, y + dy) for x, y in p.points], p.width)
                         for p in source.polylines]


def path_wires(points, layer, label="") -> list[Wire]:
    """A wire run through `points` (each step straight across or straight up / down), the
    pieces of no length left out."""
    return [Wire(layer, a, b, label) for a, b in zip(points, points[1:])
            if abs(a[0] - b[0]) > TOLERANCE or abs(a[1] - b[1]) > TOLERANCE]


def lane_route(start, end, lane_x, layer, label="") -> list[Wire]:
    """A wire from `start` to `end` turning in the upright lane at `lane_x`: across to the
    lane, up or down it, and across to the end (pieces of no length left out)."""
    return path_wires([start, (lane_x, start[1]), (lane_x, end[1]), end], layer, label)


def count_crossings(wires) -> int:
    """How many times a straight-across piece and an upright piece of two different wire runs
    cross (not counting where they meet at an end)."""
    across = [w for w in wires if abs(w.start[1] - w.end[1]) < TOLERANCE]
    upright = [w for w in wires if abs(w.start[0] - w.end[0]) < TOLERANCE]
    count = 0
    for a in across:
        x0, x1, y = min(a.start[0], a.end[0]), max(a.start[0], a.end[0]), a.start[1]
        for u in upright:
            y0, y1, x = min(u.start[1], u.end[1]), max(u.start[1], u.end[1]), u.start[0]
            if ((a.layer, a.label) != (u.layer, u.label) and x0 + TOLERANCE < x < x1 - TOLERANCE
                    and y0 + TOLERANCE < y < y1 - TOLERANCE):
                count += 1
    return count


def _runs(wires) -> list[tuple[str, list]]:
    """[(label, pieces)]: the labelled pieces gathered into runs, pieces with the same label
    that meet end to end. Two runs can carry one label (the two ends of a cable drawn by
    reference, both on one page): each is labelled."""
    runs = []
    for w in wires:
        if not w.label:
            continue
        ends = {w.start, w.end}
        touching = [run for run in runs if run[0] == w.label
                    and any(p.start in ends or p.end in ends for p in run[1])]
        merged = (w.label, [w] + [p for run in touching for p in run[1]])
        runs = [run for run in runs if not any(run is t for t in touching)] + [merged]
    return runs


def label_wires(wires, gap) -> list[WireLabel]:
    """One label per labelled wire run (its pieces share the label and meet end to end):
    centred on the run's longest across piece, `gap` above it; a run that only goes up and
    down gets its label turned 90 degrees, `gap` to the left of its longest piece (decision
    2026-11-09)."""
    labels = []
    for text, pieces in _runs(wires):
        across = [w for w in pieces if abs(w.start[1] - w.end[1]) < TOLERANCE]
        if across:
            w = max(across, key=lambda w: abs(w.end[0] - w.start[0]))
            labels.append(WireLabel(text, (w.start[0] + w.end[0]) / 2, w.start[1] + gap))
        else:
            w = max(pieces, key=lambda w: abs(w.end[1] - w.start[1]))
            labels.append(WireLabel(text, w.start[0] - gap, (w.start[1] + w.end[1]) / 2, rotation=90.0))
    return labels


def tilde_text(text, dp, spacing=None) -> str:
    """A tilde's text on one line or two, never more (Sammy, 2026-11-20). The lines are
    joined by "\\n".
    - One line when it is no longer than wire_break_text_one_line characters, has no space to
      break at, or when the wires beside it are closer together than two lines need
      (`spacing`, e.g. a terminal strip's stubs).
    - Otherwise two lines, broken at the space that makes the longer line shortest
      ("TO MCB01 COM190" / "SECTION 1"). That line may still be over the limit: the label is
      then just wider, never a third line."""
    words = text.split(" ")
    if len(text) <= dp.wire_break_text_one_line or len(words) < 2:
        return text
    if spacing is not None and spacing < text_block_height(2, dp) + dp.wire_break_text_clearance:
        return text
    splits = [(" ".join(words[:i]), " ".join(words[i:])) for i in range(1, len(words))]
    first, second = min(splits, key=lambda pair: max(len(pair[0]), len(pair[1])))
    return f"{first}\n{second}"


def text_block_height(lines, dp) -> float:
    """How tall a tilde's text is on this many lines."""
    return dp.wire_break_text_height + (lines - 1) * dp.wire_break_text_line_spacing


def tilde_text_box(text, dp, mirrored, vertical=False) -> tuple:
    """Where a tilde's text lies around its wire end, (left, bottom, right, top): along the
    wire, starting wire_break_text_offset past the tilde, centred on the wire. Lying: to the
    right (to the left when mirrored). Upright: upward (downward when mirrored up-down, its
    wire arriving from above). The length is an estimate (the program can't measure
    AutoCAD's font)."""
    lines = text.split("\n")
    length = max(len(line) for line in lines) * dp.wire_break_text_character_width
    half = text_block_height(len(lines), dp) / 2
    start = dp.wire_break_text_offset
    if vertical:
        return (-half, -start - length, half, -start) if mirrored else (-half, start, half, start + length)
    return (-start - length, -half, -start, half) if mirrored else (start, -half, start + length, half)


def _stacked_spacing(ends, vertical=False):
    """How close together the ends stacked side by side are, or None: above each other (same
    x) for lying tildes, beside each other (same y) for upright ones."""
    across, along = (1, 0) if vertical else (0, 1)
    gaps = [abs(a[along] - b[along]) for i, a in enumerate(ends) for b in ends[i + 1:]
            if abs(a[across] - b[across]) < TOLERANCE and abs(a[along] - b[along]) > TOLERANCE]
    return min(gaps) if gaps else None


def wire_breaks(ends, settings, catalog, state_name="", flip_parameter="", text="", spacing=None) -> list:
    """A tilde on each wire end that goes on elsewhere (through a TO / FROM bracket, or by
    reference): its CONN point on the end, in its vertical state (or `state_name`), mirrored
    with `flip_parameter` when given (lying tildes face wires arriving from the left). Its
    text attribute says `text` (e.g. "TO 1TBG", Sammy 2026-11-17); every other text attribute
    is set empty on purpose, not left to the block's default. None if it isn't catalogued.

    The text goes on two lines when it is long and the attribute is multi-line (tilde_text;
    `spacing` is how close the next wire is when it isn't one of `ends`). The tilde's size
    takes in its text, so whatever is placed by size keeps clear of it (Sammy, 2026-11-20).
    Upright (its vertical state) the text goes in the vertical text attribute, under the
    tilde when it is flipped up-down (wire_break_flip_vertical: its wire arrives from above)."""
    dp = settings.device_pages
    state_name = state_name or dp.wire_break_state
    block = catalog.get(dp.wire_break_block)
    if block is None or not block.states or state_name not in block.states:
        return []
    state = block.states[state_name]
    mx, my = state["markers"][dp.wire_break_marker]
    left, bottom, right, top = state["extents"]
    vertical = state_name == dp.wire_break_state
    upside_down = vertical and flip_parameter == dp.wire_break_flip_vertical
    if upside_down:
        extents = (left, -top, right, -bottom)
    else:
        extents = (-right, bottom, -left, top) if flip_parameter else (left, bottom, right, top)
    tag = dp.wire_break_text_attribute_vertical if vertical else dp.wire_break_text_attribute
    attribute = next((a for a in block.attributes if a.tag == tag), None)
    if text and attribute is not None and attribute.multiline:
        text = tilde_text(text, dp, spacing if spacing is not None else _stacked_spacing(ends, vertical))
    if text:
        t_left, t_bottom, t_right, t_top = tilde_text_box(text, dp, bool(flip_parameter), vertical)
        extents = (min(extents[0], t_left + mx), min(extents[1], t_bottom + my),
                   max(extents[2], t_right + mx), max(extents[3], t_top + my))
    values = {**{a.tag: "" for a in block.attributes}, tag: text}
    return [BlockPlacement(block=dp.wire_break_block, layer=settings.bus_break.layer,
                           position=(x - mx, y - my), attributes=values, visibility=state_name, label=text,
                           extents=extents, flipped=bool(flip_parameter), flip_parameter=flip_parameter)
            for x, y in ends]
