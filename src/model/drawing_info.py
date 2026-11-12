"""General Drawing Information: the job number and the item name (decisions 2026-10-19/20).

The job number is required: no drawing is made without it. It names the drawing file and
gives the title block numbers; later it is also how the item name is fetched from Arena.
The item name comes from Arena (pasted in for now).

How they reach the HYPER_A template's title block: only through drawing properties
(DWGPROPS custom properties), which the template's fields show on every sheet:
    FG NUMBER          = job number  (the template's fields turn it into FGD 900-<job> and
                                      each row's drawing number EO-/ES-/EW-<job>)
    FG DESCRIPTION     = item name, line 1
    NUMBER OF BREAKERS = item name, line 2 (when it needs two lines)
    TOTAL PAGES ES     = number of 3-line pages
The FGD / drawing number formats in config are only for the app's preview.
Pure Python.
"""
import json
from dataclasses import dataclass
from pathlib import Path

from src.layout.settings import SettingsError


@dataclass
class DrawingInfo:
    job_number: str = ""
    item_name: str = ""             # from Arena


@dataclass(frozen=True)
class DrawingInfoSettings:
    fgd_format: str                 # e.g. "900-{job_number}"
    drawing_number_formats: dict    # drawing type (EO / ES / EW) -> e.g. "ES-{job_number}"
    default_drawing_type: str       # rows that are none of these (TOC, legend) use this
    drawing_file_format: str        # e.g. "{job_number}"
    item_name_line_length: int      # longer item names are split over two lines
    drawing_properties: dict        # what -> drawing property name in the template


def load_drawing_info_settings(path) -> DrawingInfoSettings:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return DrawingInfoSettings(**{name: data[name] for name in DrawingInfoSettings.__dataclass_fields__})
    except FileNotFoundError:
        raise SettingsError(f"Settings file not found: {path}")
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise SettingsError(f"{path.name} is missing something or is not valid JSON: {error}")


MISSING_JOB_NUMBER = ("Enter the job number (Drawing Information, at the top of the list): "
                      "a drawing can't be made without it.")


def job_number_problem(switchboard) -> str:
    """The warning to show while there is no job number, or ""."""
    return "" if switchboard.drawing_info.job_number.strip() else MISSING_JOB_NUMBER


def item_name_lines(item_name: str, line_length: int) -> tuple[str, str]:
    """The item name on the title block's two lines: all on line 1 if it fits, otherwise
    split at the comma nearest the middle (Arena names are comma-separated lists)."""
    name = " ".join(item_name.split())
    if len(name) <= line_length or "," not in name:
        return name, ""
    commas = [i for i, char in enumerate(name) if char == ","]
    split = min(commas, key=lambda i: abs(i - len(name) / 2))
    return name[:split + 1].strip(), name[split + 1:].strip()


def fgd_number(switchboard, settings: DrawingInfoSettings) -> str:
    return settings.fgd_format.format(job_number=switchboard.drawing_info.job_number.strip())


def drawing_number(switchboard, settings: DrawingInfoSettings, drawing_type: str) -> str:
    """EO-/ES-/EW- + job number for a frame row of that type (others: the default type)."""
    fmt = settings.drawing_number_formats.get(
        drawing_type, settings.drawing_number_formats[settings.default_drawing_type])
    return fmt.format(job_number=switchboard.drawing_info.job_number.strip())


def drawing_properties(switchboard, settings: DrawingInfoSettings, total_pages: int) -> dict[str, str]:
    """{drawing property name: value} to write into the drawing. `total_pages` is every page
    of the drawing (TOC, legend, BOM and the ES pages): the title block's "OF nn"
    (decision 2026-11-11)."""
    line_1, line_2 = item_name_lines(switchboard.drawing_info.item_name, settings.item_name_line_length)
    names = settings.drawing_properties
    return {
        names["job_number"]: switchboard.drawing_info.job_number.strip(),
        names["item_name_line_1"]: line_1,
        names["item_name_line_2"]: line_2,
        names["total_pages"]: f"{total_pages:02d}",
    }


def drawing_file_stem(switchboard, settings: DrawingInfoSettings) -> str | None:
    """The drawing's file name (without .dwg) from the job number, or None without one."""
    job = switchboard.drawing_info.job_number.strip()
    return settings.drawing_file_format.format(job_number=job) if job else None
