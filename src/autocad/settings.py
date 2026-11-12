"""Loads config/autocad_settings.json: which AutoCAD to use, where the template, block
library and project folders are, and how pages map to the template's frames and layouts.

Paths starting with ~ are in each person's own user folder (where SharePoint syncs), so one
settings file works on every PC; relative paths are inside the configurator's folder."""
import json
from dataclasses import dataclass
from pathlib import Path

from src.layout.settings import SettingsError


@dataclass(frozen=True)
class AutocadSettings:
    program_id: str            # e.g. "AutoCAD.Application.25.1" (AutoCAD 2026)
    template_file: Path            # the configurator's copy of the template (drawn from)
    template_source: Path          # the team's template in SharePoint (copied by releases)
    keep_layouts: list             # layouts kept besides the drawn pages (e.g. the legend)
    keep_layout_frames: dict       # {kept layout: the frame it shows}, e.g. "TOC_ES": "TOC_01"
    output_folder: Path
    frame_block_name: str      # "TITLE_BLOCK_MODEL"
    frame_name_attribute: str  # "NAME" (holds e.g. "ES_01")
    page_frame_format: str     # "ES_{page:02d}" -> page 1 is frame "ES_01"
    page_layout_format: str
    page_number_attribute: str  # "PAGE": the frame's page number (decision 2026-11-10)
    page_number_format: str     # "{number:02d}" -> "04"
    placeholder_layer: str
    placeholder_layer_color: int
    block_library_file: Path       # Hyper's block library drawing (read only)
    objectdbx_program_id: str      # reads a .dwg in the background (version must match AutoCAD)
    jobs_folder: Path              # default folder for project files (every user, every product)
    switchboard_library_folder: Path   # ready-made switchboards, e.g. the sample

    def frame_name(self, page_number: int) -> str:
        return self.page_frame_format.format(page=page_number)

    def layout_name(self, page_number: int) -> str:
        return self.page_layout_format.format(page=page_number)

    def page_numbers(self, page_count: int) -> dict[str, str]:
        """{frame name: page number text} for every page of a drawing with `page_count`
        3-line and device pages. The rule of the engineers' NumberByLayout.lsp (decision
        2026-11-10): pages are numbered 01, 02, 03... in tab order, which is the kept
        template pages (TOC, legend, BOM) followed by ES_01, ES_02..."""
        frames = [self.keep_layout_frames[name] for name in self.keep_layouts]
        frames += [self.frame_name(page) for page in range(1, page_count + 1)]
        return {frame: self.page_number_format.format(number=number)
                for number, frame in enumerate(frames, start=1)}


def load_autocad_settings(path, project_root) -> AutocadSettings:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SettingsError(f"Settings file not found: {path}")
    except json.JSONDecodeError as error:
        raise SettingsError(f"{path} is not valid JSON: {error}")

    def text(key):
        value = data.get(key)
        if not isinstance(value, str) or not value:
            raise SettingsError(f'"{key}" in {path.name} must be some text.')
        return value

    program_id = text("autocad_program_id")
    # Guard the "never AutoCAD Electrical" rule: Electrical registers its own program ids.
    if "electrical" in program_id.lower():
        raise SettingsError("autocad_program_id must not point at AutoCAD Electrical.")

    color = data.get("placeholder_layer_color")
    if isinstance(color, bool) or not isinstance(color, int) or not 1 <= color <= 255:
        raise SettingsError(f'"placeholder_layer_color" in {path.name} must be 1-255.')

    for key in ("page_frame_format", "page_layout_format"):
        if "{page" not in text(key):
            raise SettingsError(f'"{key}" in {path.name} must contain "{{page:02d}}".')

    frames = data.get("keep_layout_frames", {})
    if not isinstance(frames, dict):
        raise SettingsError(f'"keep_layout_frames" in {path.name} must map each kept layout to its frame.')
    for name in data.get("keep_layouts", []):
        if not isinstance(frames.get(name), str) or not frames.get(name):
            raise SettingsError(f'"keep_layout_frames" in {path.name} has no frame for the kept '
                                f'layout "{name}" (needed to number its page).')
    if "{number" not in text("page_number_format"):
        raise SettingsError(f'"page_number_format" in {path.name} must contain "{{number:02d}}".')

    root = Path(project_root)
    return AutocadSettings(
        program_id=program_id,
        template_file=root / text("template_file"),
        template_source=_resolve(root, text("template_source")),
        keep_layouts=[str(name) for name in data.get("keep_layouts", [])],
        keep_layout_frames={str(k): str(v) for k, v in frames.items()},
        output_folder=root / text("output_folder"),
        frame_block_name=text("frame_block_name"),
        frame_name_attribute=text("frame_name_attribute"),
        page_frame_format=text("page_frame_format"),
        page_layout_format=text("page_layout_format"),
        page_number_attribute=text("page_number_attribute"),
        page_number_format=text("page_number_format"),
        placeholder_layer=text("placeholder_layer"),
        placeholder_layer_color=color,
        block_library_file=_resolve(root, text("block_library_file")),
        objectdbx_program_id=text("objectdbx_program_id"),
        jobs_folder=_resolve(root, text("jobs_folder")),
        switchboard_library_folder=_resolve(root, text("switchboard_library_folder")),
    )


def _resolve(root: Path, value: str) -> Path:
    """~ is the person's user folder; absolute paths are used as they are; relative ones
    are inside the project."""
    path = Path(value).expanduser()
    return path if path.is_absolute() else root / path
