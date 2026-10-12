"""Makes the drawing: copy the template, open it in AutoCAD, check its frames, draw every
page, save. Decision: docs/DECISIONS.md, 2026-10-11 "First AutoCAD step".
"""
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from src.autocad.connection import AutocadSession
from src.autocad.draw_page import BlockInsert, page_shapes
from src.layout.page_fitter import fit_pages


class GenerateError(Exception):
    """Something stopped the drawing from being made. The message says what and why."""


@dataclass
class GenerateResult:
    drawing_file: Path
    problems: list[str] = field(default_factory=list)   # drawing was made, but check these


def output_file_name(switchboard_name: str, now: datetime) -> str:
    """Switchboard name + date/time, with characters Windows won't allow replaced."""
    safe_name = re.sub(r'[<>:"/\\|?*]', "_", switchboard_name).strip() or "Switchboard"
    return f"{safe_name} {now:%Y-%m-%d %H%M%S}.dwg"


def check_frames(frames, page_count, autocad_settings) -> dict[int, tuple[float, float]]:
    """Map each page to its frame's insertion point. Raises GenerateError if a frame is
    missing or appears more than once (we would not know which to use)."""
    by_name = {}
    duplicated = set()
    for name, x, y in frames:
        if name in by_name:
            duplicated.add(name)
        by_name[name] = (x, y)

    origins = {}
    missing = []
    for page in range(1, page_count + 1):
        frame = autocad_settings.frame_name(page)
        if frame in duplicated:
            raise GenerateError(f'The template has more than one frame named "{frame}".')
        if frame not in by_name:
            missing.append(frame)
        else:
            origins[page] = by_name[frame]
    if missing:
        found = sorted(name for name in by_name if name.startswith("ES_"))
        raise GenerateError(
            f"The drawing needs {page_count} pages but the template has no frame named "
            f"{', '.join(missing)}. ES frames found: {', '.join(found) or 'none'}."
        )
    return origins


def generate_drawing(switchboard, layout_settings, autocad_settings, catalog=None,
                     now=None) -> GenerateResult:
    layout = fit_pages(switchboard, layout_settings, catalog)
    if not layout.pages:
        raise GenerateError("There is nothing to draw: the switchboard has no sections.")

    template = autocad_settings.template_file
    if not template.exists():
        raise GenerateError(f"Template not found: {template}")
    autocad_settings.output_folder.mkdir(parents=True, exist_ok=True)
    drawing_file = autocad_settings.output_folder / output_file_name(
        switchboard.name, now or datetime.now())
    shutil.copy2(template, drawing_file)          # the template itself is never opened

    drawing = AutocadSession(autocad_settings.program_id).open(drawing_file)

    # Check everything before drawing anything.
    origins = check_frames(
        drawing.find_frames(autocad_settings.frame_block_name, autocad_settings.frame_name_attribute),
        len(layout.pages), autocad_settings,
    )
    problems = [f"Layout: {warning}" for warning in layout.warnings]
    layouts = drawing.layout_names()
    for page in layout.pages:
        if autocad_settings.layout_name(page.number) not in layouts:
            problems.append(
                f"Page {page.number} was drawn in frame {autocad_settings.frame_name(page.number)}, "
                f"but the template has no layout named {autocad_settings.layout_name(page.number)} "
                f"to show it."
            )
    if layout_settings.text.style not in drawing.text_style_names():
        problems.append(f'The template has no text style "{layout_settings.text.style}"; '
                        f"AutoCAD's current style was used.")

    for layer in (layout_settings.main_bus.layer, layout_settings.divider.layer,
                  layout_settings.ground_bus.layer, layout_settings.text.layer):
        if drawing.ensure_layer(layer):
            problems.append(f'The template had no layer "{layer}"; it was created with default settings.')
    drawing.ensure_layer(autocad_settings.placeholder_layer,
                         color=autocad_settings.placeholder_layer_color, plottable=False)

    shapes_per_page = {page.number: page_shapes(page, layout_settings, autocad_settings.placeholder_layer)
                       for page in layout.pages}
    block_names = {shape.block for shapes in shapes_per_page.values()
                   for shape in shapes if isinstance(shape, BlockInsert)}
    if block_names:
        if not autocad_settings.block_library_file.exists():
            raise GenerateError(f"Block library not found: {autocad_settings.block_library_file}")
        missing = drawing.import_blocks(block_names, autocad_settings.block_library_file,
                                        autocad_settings.objectdbx_program_id)
        if missing:
            raise GenerateError(f"These blocks are not in the block library: {', '.join(missing)}")

    for page in layout.pages:
        x, y = origins[page.number]
        problems += drawing.add_shapes(shapes_per_page[page.number], x, y)

    drawing.save()
    return GenerateResult(drawing_file=drawing_file, problems=problems)
