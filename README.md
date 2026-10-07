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

## Status
Milestone 1 (built, awaiting Sammy's review): model, config, layout engine, basic preview
with placeholder section sizes.

## Open items (to decide when the work reaches them)
- Blocks: connection-marker convention (HS_CONN), then add markers to each block.
- Blocks: legacy assumptions to re-decide (junction bullet placed separately from feeder
  blocks; SPD block excludes its drops to the bus).
- Blocks: naming (`SCHEME_` vs `SCHEM_`) and which variants are current
  (`SCHEME_ATC*`, `SCHEME_COM800*`).
- Blocks: no tie breaker block yet.
- Drawing: how bus bars and section dividers (code-drawn lines, not blocks) are drawn.
- Drawing: title block keep-out position on the page, and page-to-AutoCAD coordinate mapping.
- Drawing: how the AutoCAD step uses `templates/EW_SWBD_TEMPLATE.dwg`.
- Project file save format.
- Layout rules still open: tie breaker elevation, vertical bus up/down choice, placement of
  SPD / fuses / CTs.
- Reference: study `ES-011511_A_REFERENCE.dxf` (see `docs/SWBD_reference/INDEX.md`).
- Repo: optional `.gitattributes` so git never changes `.dxf` line endings.
