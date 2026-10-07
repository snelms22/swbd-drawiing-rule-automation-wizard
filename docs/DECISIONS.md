# Design Decisions Log

All numeric values are placeholders until measured from the template. All are configurable.
Units are drawing units (5 units = spacing between bus bars), not real-world inches.

New entries use this format:

```
### YYYY-MM-DD — Short title
**Decision:** What we're doing.
**Reason:** Why.
**Status:** Approved / Placeholder (measure from template) / To confirm
```

## Decision log

### 2026-10-07 — Decision log format
**Decision:** Every entry has a date, decision, reason, and status, in the format above.
Entries recorded before this date were backfilled with 2026-10-07 and reason "Baseline".
**Reason:** CLAUDE.md requires date + decision + reason; status shows what is still open.
**Status:** Approved

### 2026-10-07 — Template and reference drawing folders
**Decision:** `templates/` holds the drawings the program uses (`EW_SWBD_TEMPLATE.dwg`).
`docs/SWBD_reference/` holds finished jobs for comparison only (`ES-011511_A_REFERENCE.dwg`
and `.pdf`). Files copied unchanged from V4.12.2.
**Reason:** Keep "what the program uses" separate from "what we compare against." Reference
folder is named per product so other products can get their own reference folders later.
**Status:** Approved

### 2026-10-07 — Reference drawing workflow
**Decision:** Sammy drops a `.dxf` + `.pdf` per job into `docs/SWBD_reference/`. At the start
of each session Claude checks the folder against `INDEX.md`, studies any new job, and records
contents, measurements, proposed rules (pending approval), and questions there. The rule lives
in CLAUDE.md. DXF files are read with `ezdxf`, listed in `requirements-dev.txt` (dev-only).
**Reason:** Sammy should not have to track what Claude has seen; notes live in the repo so
every session (and Sammy) can read them. DWG cannot be read directly; DXF can.
**Status:** Approved

### 2026-10-07 — Python version and virtual environment location
**Decision:** Use Python 3.14 (the version installed; meets the 3.11+ rule). The virtual
environment lives at `C:\venvs\hyper-configurator`, outside the OneDrive project folder.
**Reason:** All required libraries support 3.14, so no older install is needed. Keeping the
environment out of OneDrive avoids syncing hundreds of MB of library files and the risk of
OneDrive locking files mid-install.
**Status:** Approved

### 2026-10-07 — Version history
**Decision:** Local git repository in the project folder, branch `main`, no remote. Claude
commits only when Sammy asks.
**Reason:** Shows what changed, when, and why, and allows undoing a specific change.
OneDrive alone can't do that. Kept local so no company drawings leave the PC.
**Status:** Approved

### 2026-10-07 — Milestone 1 scope
**Decision:** Milestone 1 = project data (ordered sections with placeholder width/height,
push and link flags), settings loader, pure-Python page-fitting engine, one automated test
per rule, and a PySide6 preview app (section table, page drawing, warnings list, live
update). Out of scope: AutoCAD, blocks, catalog, devices, bus lines, real measurements,
saving/loading projects.
**Reason:** Prove the page-fitting rules work before anything is drawn in AutoCAD.
**Status:** Approved

### 2026-10-07 — Section order is never changed
**Decision:** Sections stay in the order entered. Layout never reorders them to fill gaps.
**Reason:** The main bus is continuous, so section order is electrical, not cosmetic.
**Status:** Approved

### 2026-10-07 — Linked sections that don't fit
**Decision:** A linked group that doesn't fit on the current page moves to a fresh page
together. If it doesn't fit even on an empty page, it is placed anyway (overflowing) with a
warning so the problem is visible.
**Reason:** Keeps linked sections together; a visible overflow is easier to fix than a silent split.
**Status:** Approved

### 2026-10-07 — Title block keep-out handling
**Decision:** For now, sections hang down from the top margin. A section that sits over the
keep-out's x-range and reaches down into it moves to the next page. Warn only if it can't
move (e.g. it is alone on the page or part of a linked group that still collides).
**Reason:** Simple starting rule.
**Status:** Approved (may change with use)

### 2026-10-07 — Section taller than a page
**Decision:** A section taller than the page (between standard margins) is a design error
and gets a warning, same as a section wider than a page.
**Reason:** Consistent with the oversized-width rule.
**Status:** Approved (may change with use)

### 2026-10-07 — Library versions not pinned
**Decision:** `requirements.txt` and `requirements-dev.txt` list libraries without version numbers.
**Reason:** Single user on a single PC; the environment is set up once and not rebuilt
elsewhere. Revisit if the project is shared or moved to another PC.
**Status:** Approved

## Approach

### 2026-10-07 — Rebuild from scratch
**Decision:** Rebuild from scratch for full owner understanding. V4.12.2 is reference only.
**Reason:** Baseline
**Status:** Approved

### 2026-10-07 — Remove "common scale" section shrinking
**Decision:** Root cause of block scaling in V4.12.2: sections were shrunk by a "common scale"
(0.80-0.94) to pack onto sheets. The rebuild removes this entirely.
**Reason:** Baseline
**Status:** Approved

## Tech stack

### 2026-10-07 — UI framework
**Decision:** UI: PySide6 (all Python).
**Reason:** Baseline
**Status:** Approved

### 2026-10-07 — AutoCAD output
**Decision:** AutoCAD output: live COM, blocks inserted at scale 1.0, never exploded.
**Reason:** Baseline
**Status:** Approved

### 2026-10-07 — Block connection points
**Decision:** Block connection points: marker points inside each block (dedicated layer, e.g. HS_CONN).
**Reason:** Baseline
**Status:** Approved

### 2026-10-07 — Layout in pure Python
**Decision:** Layout computed in pure Python; AutoCAD only executes the final placement.
**Reason:** Baseline
**Status:** Approved

## Page layout rules

### 2026-10-07 — Blocks never scaled
**Decision:** Blocks are never scaled.
**Reason:** Baseline
**Status:** Approved

### 2026-10-07 — Section width
**Decision:** Section width: dividing lines sit 5 units outside the section's outermost component.
**Reason:** Baseline
**Status:** Approved

### 2026-10-07 — Shared dividing lines
**Decision:** Adjacent sections share one dividing line, giving 10 units between outermost components.
**Reason:** Baseline
**Status:** Approved

### 2026-10-07 — Page drawable area
**Decision:** Page drawable area: ~500 W x 300 H.
**Reason:** Baseline
**Status:** Approved

### 2026-10-07 — Standard margin
**Decision:** Standard margin: 10 units per side.
**Reason:** Baseline
**Status:** Approved

### 2026-10-07 — Margin relaxation
**Decision:** Margin relaxation: if one more section fits with 5-unit margins per side (10 total gained),
place it on the page. Otherwise it moves to the next page.
**Reason:** Baseline
**Status:** Approved

### 2026-10-07 — Page fill order
**Decision:** Fill pages left to right, as many sections as fit.
**Reason:** Baseline
**Status:** Approved

### 2026-10-07 — Linked sections
**Decision:** User can link sections to keep them on the same page. Warn if they cannot fit.
**Reason:** Baseline
**Status:** Approved

### 2026-10-07 — Manual push to next page
**Decision:** User can manually push a section to the next page.
**Reason:** Baseline
**Status:** Approved

### 2026-10-07 — Oversized sections
**Decision:** A section wider than one page is a design error (revisit later if needed).
**Reason:** Baseline
**Status:** Approved

### 2026-10-07 — Title block keep-out
**Decision:** Title block: rectangular keep-out zone, bottom-right, ~100 x 100. Any section placed over
that x-range must keep its components above it; otherwise bump to the next page or warn.
Keep-out values to be measured from the template later.
**Reason:** Baseline
**Status:** Approved

## Section composition

### 2026-10-07 — Main bus
**Decision:** Main bus runs horizontally, left to right.
**Reason:** Baseline
**Status:** Approved

### 2026-10-07 — Vertical bus
**Decision:** Each section has a vertical bus that branches up and/or down from the main bus
(direction depends on available space).
**Reason:** Baseline
**Status:** Approved

### 2026-10-07 — Feeder breakers
**Decision:** Feeder breakers attach to the vertical bus: left/right pairs, or a single breaker.
**Reason:** Baseline
**Status:** Approved

### 2026-10-07 — Main breakers
**Decision:** Main breakers come in from the top and start the drawing.
**Reason:** Baseline
**Status:** Approved

### 2026-10-07 — Tie breakers
**Decision:** Tie breakers (new): connect input bus to the rest of the bus. Shown inline as a break in
the horizontal main bus, at the main breaker's elevation (to confirm).
**Reason:** Baseline
**Status:** Approved

### 2026-10-07 — Other devices
**Decision:** Other devices (SPD, fuses, CTs, etc.): placement rules to be defined later.
**Reason:** Baseline
**Status:** Approved

## Preview / UI

### 2026-10-07 — Simplified preview
**Decision:** Simplified visual preview of pages and sections in the configurator.
**Reason:** Baseline
**Status:** Approved

### 2026-10-07 — Saved manual overrides
**Decision:** Manual overrides (push to next page, link sections) are saved with the project.
**Reason:** Baseline
**Status:** Approved
