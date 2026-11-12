"""Makes the drawing: copy the template, open it in AutoCAD, check its frames, draw every
page, save. Decision: docs/DECISIONS.md, 2026-10-11 "First AutoCAD step".

A copy of the project (.swbd) is saved next to every drawing, with the same name, so any
drawing can be reopened and remade exactly (decision 2026-10-15).

General Drawing Information (decisions 2026-10-19/20): a drawing needs a job number. The
drawing is named after it (replacing an earlier drawing of the same job), and the title
block is filled through drawing properties (job number, item name, number of 3-line
pages), which the template's fields show on every sheet (FGD 900- and the EO-/ES-/EW-
drawing numbers come from the job number). Only the layouts with something in them are kept:
the template pages listed in config (legend, BOM), then the 3-line pages drawn.

Every kept page gets its page number in its frame (decision 2026-11-10): 01, 02, 03... in tab
order, the same numbers the engineers' NumberByLayout.lsp gives.
"""
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from src.autocad.connection import AutocadSession
from src.autocad.draw_page import BlockInsert, page_shapes
from src.layout.page_fitter import fit_pages
from src.model.drawing_info import (
    MISSING_JOB_NUMBER, drawing_file_stem, drawing_properties, job_number_problem,
)
from src.model.project_file import EXTENSION, save_project


class GenerateError(Exception):
    """Something stopped the drawing from being made. The message says what and why."""


@dataclass
class GenerateResult:
    drawing_file: Path
    project_copy: Path | None = None                   # the .swbd saved next to the drawing
    problems: list[str] = field(default_factory=list)   # drawing was made, but check these


def _safe_file_name(name: str) -> str:
    """The name with characters Windows won't allow in a file name replaced."""
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip()


def output_file_name(switchboard_name: str, now: datetime) -> str:
    """Switchboard name + date/time, with characters Windows won't allow replaced."""
    safe_name = _safe_file_name(switchboard_name) or "Switchboard"
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


def drawing_path(switchboard, output_folder: Path, drawing_info_settings=None, now=None) -> Path:
    """Where the drawing goes: named after the job number when there is one, otherwise the
    project name and the date."""
    stem = drawing_file_stem(switchboard, drawing_info_settings) if drawing_info_settings else None
    if stem:
        return output_folder / f"{_safe_file_name(stem)}.dwg"
    return output_folder / output_file_name(switchboard.name, now or datetime.now())


def sheet_count_problems(layout_settings, autocad_settings) -> list[str]:
    """SHEET numbers count the template pages kept before the 3-line (decision 2026-11-10).
    The count is in layout_settings.json and the pages in autocad_settings.json: say so if
    they disagree, as every SHEET reference would then be off."""
    expected = len(autocad_settings.keep_layouts)
    counted = layout_settings.device_pages.sheets_before_pages
    if counted == expected:
        return []
    return [f"SHEET numbers count {counted} page(s) before the 3-line (sheets_before_pages in "
            f"layout_settings.json), but {expected} are kept ({', '.join(autocad_settings.keep_layouts)}, "
            f"keep_layouts in autocad_settings.json); the SHEET references are off by "
            f"{abs(expected - counted)}."]


def generate_drawing(switchboard, layout_settings, autocad_settings, catalog=None,
                     now=None, output_folder=None, drawing_info_settings=None,
                     device_settings=None) -> GenerateResult:
    """`output_folder`: where the drawing goes (the folder the person picked, decision
    2026-10-15); config's output_folder when not given (development). `device_settings`
    (config/devices.json) adds the device pages."""
    if drawing_info_settings is not None and job_number_problem(switchboard):
        raise GenerateError(MISSING_JOB_NUMBER)
    layout = fit_pages(switchboard, layout_settings, catalog, device_settings)
    if not layout.pages:
        raise GenerateError("There is nothing to draw: the switchboard has no sections.")

    template = autocad_settings.template_file
    if not template.exists():
        raise GenerateError(f"Template not found: {template}")
    output_folder = Path(output_folder) if output_folder else autocad_settings.output_folder
    output_folder.mkdir(parents=True, exist_ok=True)
    drawing_file = drawing_path(switchboard, output_folder, drawing_info_settings, now)
    try:
        shutil.copy2(template, drawing_file)      # the template itself is never opened
    except PermissionError:
        raise GenerateError(f"{drawing_file.name} is open (probably in AutoCAD). Close it and "
                            f"generate again.")

    drawing = AutocadSession(autocad_settings.program_id).open(drawing_file)

    # Check everything before drawing anything.
    origins = check_frames(
        drawing.find_frames(autocad_settings.frame_block_name, autocad_settings.frame_name_attribute),
        len(layout.pages), autocad_settings,
    )
    problems = [f"Layout: {warning}" for warning in layout.warnings]
    problems += sheet_count_problems(layout_settings, autocad_settings)
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
                  layout_settings.ground_bus.layer, layout_settings.text.layer,
                  layout_settings.interlocks.layer):
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

    # The wires the program draws go on the same layers as the blocks' own wires (they
    # usually came in with the blocks; made here only if not).
    for layer in sorted({wire.layer for page in layout.pages for wire in page.parts.wires}):
        drawing.ensure_layer(layer)

    for page in layout.pages:
        x, y = origins[page.number]
        problems += drawing.add_shapes(shapes_per_page[page.number], x, y)

    if drawing_info_settings is not None:
        drawing.set_drawing_properties(
            drawing_properties(switchboard, drawing_info_settings,
                               total_pages=len(autocad_settings.keep_layouts) + len(layout.pages)))
    # Page numbers in the frames, in tab order, as the engineers' LISP numbers them
    # (decision 2026-11-10): TOC 01, legend 02, BOM 03, ES_01 04...
    not_numbered = drawing.set_frame_attribute(
        autocad_settings.frame_block_name, autocad_settings.frame_name_attribute,
        autocad_settings.page_number_attribute, autocad_settings.page_numbers(len(layout.pages)))
    if not_numbered:
        problems.append(f"No {autocad_settings.page_number_attribute} attribute was found to number "
                        f"these frames: {', '.join(not_numbered)}; their page numbers are the template's.")
    pages = [autocad_settings.layout_name(page.number) for page in layout.pages]
    # Template pages (legend, BOM) first, then the 3-line pages; it opens on the first page.
    drawing.keep_only_layouts(autocad_settings.keep_layouts + pages, open_on=pages[0])
    drawing.regenerate(open_on=pages[0])

    drawing.save()
    project_copy = None
    try:
        project_copy = save_project(switchboard, drawing_file.with_suffix(EXTENSION))
    except OSError as error:          # the drawing is fine; just say the copy wasn't saved
        problems.append(f"The project copy next to the drawing could not be saved: {error}")
    return GenerateResult(drawing_file=drawing_file, project_copy=project_copy, problems=problems)
