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
    template_file: Path
    output_folder: Path
    frame_block_name: str      # "TITLE_BLOCK_MODEL"
    frame_name_attribute: str  # "NAME" (holds e.g. "ES_01")
    page_frame_format: str     # "ES_{page:02d}" -> page 1 is frame "ES_01"
    page_layout_format: str
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

    root = Path(project_root)
    return AutocadSettings(
        program_id=program_id,
        template_file=root / text("template_file"),
        output_folder=root / text("output_folder"),
        frame_block_name=text("frame_block_name"),
        frame_name_attribute=text("frame_name_attribute"),
        page_frame_format=text("page_frame_format"),
        page_layout_format=text("page_layout_format"),
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
