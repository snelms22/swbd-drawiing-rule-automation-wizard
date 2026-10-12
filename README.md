# Hyper Switchboard Configurator (Rebuild)

Configure a switchboard; generate the AutoCAD drawing from it. Owner: Sammy.

Start here: `CLAUDE.md` (working rules) and `docs/DECISIONS.md` (approved design).

## Folders
| Folder | Job |
|---|---|
| `config/` | Editable layout settings (margins, page size, clearances). |
| `blocks/` | Controlled WBLOCK .dwg files. Inserted at scale 1.0, never exploded. |
| `catalog/` | Block footprints and connection points, generated from `blocks/`. |
| `templates/` | Starting drawings the program builds on (e.g. `EW_SWBD_TEMPLATE.dwg`). |
| `docs/SWBD_reference/` | Finished switchboard jobs used as "what correct looks like." Not used by the program. |
| `src/model/` | Project data: switchboard, sections, devices. |
| `src/layout/` | Page-fitting rules. Pure Python, no AutoCAD. |
| `src/ui/` | PySide6 app and preview canvas. |
| `src/autocad/` | COM placement into AutoCAD (final step only). |
| `tests/` | Automated tests, mainly for `layout/`. |

## Debugging guide
- Wrong page break or section spacing: `src/layout/` or `config/`.
- Wrong data or missing device: `src/model/`.
- Preview looks right but drawing is wrong: `src/autocad/` or `catalog/`.

## Setup
The virtual environment lives outside OneDrive (so OneDrive doesn't sync thousands of
library files). Create it once per PC, from this project folder:
```
py -3.14 -m venv C:\venvs\hyper-configurator
C:\venvs\hyper-configurator\Scripts\activate
pip install -r requirements.txt
```
After that, each time you work on the project you only need the `activate` line.
For development (adds tools for reading reference drawings):
```
pip install -r requirements-dev.txt
```

## Run
From the project folder, with the environment activated:
```
python run_configurator.py      # start the app
python -m pytest                # run the automated tests
```
Layout numbers come from `config/layout_settings.json`; restart the app after editing it.

**Generate drawing** (button in the app) copies `templates/EW_SWBD_TEMPLATE.dwg` to a new
file in `output/`, opens it in AutoCAD 2026 (never AutoCAD Electrical), draws every page into
the ES frames, and saves. Which AutoCAD, the template, and the frame/layout names are in
`config/autocad_settings.json`. Placeholder boxes for section contents are on the
non-plotting layer `CFG_PLACEHOLDER` until the real blocks are in.

## Status
Built: layout engine (page fitting, page parts, main bus), section contents and editor,
preview, and a first AutoCAD drawing (bus, dividers, ground bus, labels, placeholders).
Next: real blocks for section contents. Progress per part: `docs/DRAWING_PARTS.md`.

## Open items (to decide when the work reaches them)
- Blocks: waiting on Sammy's Hyper block set for `blocks/` (replaces legacy `SCHEM_*`).
  Then: connection-marker convention, and how dynamic blocks (visibility states) are handled.
- House standard picks (divider layer/linetype, page-break style, feeder row pitch, section
  label position): to come from Sammy's master reference drawing.
- Drawing: switch the main bus from plain lines to the dynamic bus blocks (BUSSING_3PH_3W_3L).
- Project file save format.
- Layout rules still open: when/how a section splits across a page break; placement of
  SPD / fuses / CTs; multi-bus lineups (IMS-style bypass) in scope or not.
- Repo: optional `.gitattributes` so git never changes `.dxf` line endings.
