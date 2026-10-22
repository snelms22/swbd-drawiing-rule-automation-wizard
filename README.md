# Hyper Switchboard Configurator (Rebuild)

Configure a switchboard; generate the AutoCAD drawing from it. Owner: Sammy.

Start here: `CLAUDE.md` (working rules) and `docs/DECISIONS.md` (approved design).

## Folders
| Folder | Job |
|---|---|
| `config/` | Editable layout settings (margins, page size, clearances). |
| `blocks/archived/` | Old block files, kept for reference only. Blocks now come from the shared library `Symbols-blocks.dwg` (see `docs/BLOCK_LIBRARY_STANDARD.md`). |
| `catalog/` | Library blocks' sizes and connection points (`blocks.json`). |
| `templates/` | The configurator's copy of the team's template `HYPER_A.dwt` (refreshed from SharePoint by each release, or `python tools/update_template.py`). |
| `switchboard_library/` | Ready-made switchboard projects (`.swbd`), e.g. the sample. File > Open from Library. |
| `tools/` | Development-only scripts (e.g. the block audit). Not part of the app. |
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

Projects are `.swbd` files (File > New / Open / Open from Library / Save / Save As). They
save to `CAD BLOCKS/CONFIGURATORS/Jobs` in SharePoint by default; each generated drawing
gets a copy of its project next to it.

## Releasing to the team
```
python tools/release.py 2.0.1 --note "One short line per change" --note "..."
```
Runs every test, builds the app outside OneDrive (`%LOCALAPPDATA%\Hyper Configurators\build`),
and publishes it to SharePoint `CAD BLOCKS\CONFIGURATORS\Switchboard Configurator\`
(`Releases\X.Y.Z\`, `Install Switchboard Configurator.zip` (zipped: SharePoint won't sync a loose `.exe`), then
`latest.txt`). It refuses to
run with uncommitted changes or a version that isn't newer, and commits + tags the release.
Everyone gets it the next time they open the app (a running app offers a restart).
Try a release without touching SharePoint or git: add `--test-folder <folder>`.
Undo a bad release: put the previous version number back in `latest.txt`.

Pieces: `distribution/launcher.py` (installer + launcher; log in
`%LOCALAPPDATA%\Hyper Configurators\Switchboard Configurator\launcher.log`),
`distribution/autocad_addin.py` (the Hyper ribbon tab), `distribution/icons.py` (SWBD icon).

Block audit (development only, not in the app; Sammy owns the block library):
```
python tools/audit_blocks.py    # re-read the library blocks into catalog/blocks.json, list problems
```

**Generate drawing** (button in the app) copies `templates/HYPER_A.dwt` to a new
file in `output/`, opens it in AutoCAD 2026 (never AutoCAD Electrical), draws every page into
the ES frames, and saves. Which AutoCAD, the template, and the frame/layout names are in
`config/autocad_settings.json`. Placeholder boxes for section contents are on the
non-plotting layer `CFG_PLACEHOLDER` until the real blocks are in.

## Status
Built: layout engine (page fitting, page parts, main bus), section contents and editor,
preview, and a first AutoCAD drawing (bus, dividers, ground bus, labels, placeholders).
Next: real blocks for section contents. Progress per part: `docs/DRAWING_PARTS.md`.

## Docket (agreed next work, in order; added 2026-10-15)
1. ~~Save and open projects~~ (built 2026-10-15: File menu, `.swbd` files).
1b. ~~Release to the team~~ (2.0.0 released 2026-10-15; installer zipped 2026-10-16).
2. **General Drawing Information** (built 2026-10-20 in the development copy: job number
   (required) + item name, HYPER_A title block filled, only layouts with content kept).
   Release as 2.1.0 after Sammy's review. Open: sheet numbering of kept pages; Arena fetch
   (API machine user, Sammy + software lead).
3. **Communications:** comms checkbox on each breaker (built 2026-10-19, no drawing effect
   yet); then the communications page generated from the breakers (rules: DECISIONS
   2026-10-19). Then other devices on the 3-line.
3b. ~~SPACE option~~ (built 2026-10-19, in 2.0.1).
3c. **Main-to-main interlock line, always drawn** (DRAWING_PARTS S4, now approved).
3d. **Single section switchboards** (one vertical bus, mains fed from the side): design to come.
3e. ~~Line-side output breakers~~ (load bank; built 2026-10-22 with the feed / breaker split,
   DECISIONS 2026-10-22). Later: on a feed by itself, CTs on it, more than one per feed.
3f. **Riser length grows with its devices** (CTs, voltage taps and the load-bank tie built
   2026-10-21/22; CPT etc. to come).
3g. **CTs and power meters** (built 2026-10-21, for review: DECISIONS 2026-10-21). Next:
   split input feed / input breaker (option B, DECISIONS 2026-10-22: step 1 split + voltage
   taps built; step 2 standalone feeds / main lugs only / feed in the next section built;
   step 3 load-bank line-side breaker built), then
   device pages (meters + fuses, "FROM ...", as many per page as fit; CT SHEET# from them;
   grouped by section; meter inputs paired in `config/devices.json`, DECISIONS 2026-10-22).
   Later: power supply block (24V), shipping-split connections between sections.
3h. **Re-assess the editor** (Sammy, 2026-10-22): once more is built, review the UI as a whole:
   where things are placed and how the engineer works with it.
4. Later polish (Sammy, in the block library): `BRACKET_TEXT_R0` label doesn't mirror its
   justification when flipped ("FROM ES_nn" runs back over the bus); `SIE_BKR_3P_3L_ASSY_R0`
   FRAME attributes (shared tag, no prompt, don't move on flip). No code workaround for now.

## Watch list (for Sammy's team meetings)
- Side-jog ("centre-fed") vertical buses: does Hyper build them? (Sabey-011475/011484,
  NTT-013630)

## Open items (to decide when the work reaches them)
- House standard picks (divider layer/linetype, page-break style, feeder row pitch, section
  label position): to come from Sammy's master reference drawing.
- Drawing: switch the main bus from plain lines to the dynamic bus blocks (BUSSING_3PH_3W_3L).
- Layout rules still open: when/how a section splits across a page break; placement of
  SPD / fuses / CTs; multi-bus lineups (IMS-style bypass) in scope or not.
- Repo: optional `.gitattributes` so git never changes `.dxf` line endings.
