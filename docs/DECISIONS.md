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

### 2026-10-07 — Side margin measured to the outermost divider
**Decision:** The side margin is measured from the edge of the drawable area to the
outermost dividing line, not to the components.
**Reason:** Dividers are the outermost drawn lines of the section row.
**Status:** Approved

### 2026-10-07 — Relaxed margin is left/right only
**Decision:** Margin relaxation (10 -> 5) applies to the left and right sides only. Top and
bottom margins always stay standard.
**Reason:** Relaxation exists to fit one more section across the page; height isn't affected.
**Status:** Approved

### 2026-10-07 — Link wins over push
**Decision:** "Push to next page" on a section that is linked to the previous section is
ignored, with a warning.
**Reason:** Pushing would split a linked group, which contradicts the link.
**Status:** Approved

### 2026-10-07 — Title block overlap test
**Decision:** A section overlaps the title block keep-out when its right dividing line is
past the keep-out's left edge AND its components go below the keep-out's top edge.
Ending exactly at the top edge is allowed.
**Reason:** Matches "components must stay above it" for any section over that x-range.
**Status:** Approved

### 2026-10-07 — Divider height in the preview
**Decision:** The preview draws dividing lines from the top margin to the bottom margin,
stopping at the title block keep-out. Preview only; real divider height is an open item.
**Reason:** Placeholder until divider drawing is decided.
**Status:** Approved

### 2026-10-08 — Breaker direction is the engineer's choice
**Decision:** Every breaker (main, feeder, and others) can connect from above or below the
main bus. The engineer picks the direction per breaker; the drawing follows it.
**Reason:** The drawing must match the physical design (e.g. bus fed from the bottom is
drawn from the bottom). Seen in ES-011511: main fed from bottom-left.
**Status:** Approved

### 2026-10-08 — Margins and divider clearance
**Decision:** Standard side margin 5, relaxed 2.5. Divider clearance 10. A section's
"outermost component" includes its text labels.
**Reason:** ES-011511 uses ~1–6 margins and ~10.8 divider-to-text clearance; text counts so
the drawing looks clean. Fine-tune later once real drawings are generated.
**Status:** Approved (may change with use)

### 2026-10-08 — Page size and title block from the reference
**Decision:** Page drawable area 419.04 x 269.49; title block keep-out 82.41 x 70.96,
bottom-right. Measured from the `TITLE_BLOCK_MODEL` frame in ES-011511.
**Reason:** Replaces the 500 x 300 / 100 x 100 placeholders with measured values.
**Status:** Approved

### 2026-10-08 — Where the drawing goes in AutoCAD
**Decision:** Generated drawings go in model space at 1:1, inside the `EO` title block
frames (`TITLE_BLOCK_MODEL` inserts). Page origin = the frame's insertion point. Each EO
frame is shown by its own paper-space layout view.
**Reason:** Matches how the reference drawings are built.
**Status:** Superseded 2026-10-08 by "3-line goes in the ES frames" (EO was a misreading of
the oldest reference)

### 2026-10-08 — 3-line goes in the ES frames
**Decision:** The 3-line diagram goes in model space at 1:1 inside the `ES_nn` title block
frames (`TITLE_BLOCK_MODEL` inserts), shown by the matching `ES_nn` layouts. Page origin =
the frame's insertion point. `EO` frames are the separate one-line drawing (not in scope yet).
**Reason:** All 7 newer references do this; only the oldest (ES-011511) used an EO frame.
**Status:** Approved

### 2026-10-08 — Drawing matches the physical product
**Decision:** Everything in the drawing is arranged the way it is physically arranged in the
cabinet (e.g. a tie breaker is drawn vertically because that is how it is built).
**Reason:** The drawing should show how the real product looks in space.
**Status:** Approved

### 2026-10-08 — Tie breakers are vertical
**Decision:** A tie breaker is drawn as a vertical breaker. (Seen in PRIME-014034 and
NTT-013630: it joins two parts of the main bus at different heights.)
**Reason:** Matches how it is built into the cabinet.
**Status:** Approved

### 2026-10-08 — Breaker arrangement vocabulary
**Decision:** How feeder breakers connect to the bus, chosen by the engineer per section:
- **Single breaker:** one feeder breaker coming straight off the main bus.
- **Group Mounted Distribution:** several feeder breakers on a vertical bus. Two options:
  - **Twin mount:** two breakers at the same level, left and right of the vertical bus.
  - **Single mount:** one breaker per level, alternating sides ("zig-zag") up the vertical
    bus, used for bigger breakers that take the whole width.
- **Combination:** the part of a section above the main bus and the part below can be
  different arrangements (e.g. single breaker on top, group mounted below).
**Reason:** Covers every way breakers connect to the bus in the references; names match the
terms used at Hyper.
**Status:** Approved

### 2026-10-08 — Mirroring is allowed, scaling is not
**Decision:** A block may be flipped (X scale -1, e.g. the right-hand breaker of a twin
mount). It is never scaled. Text and attributes must still read normally after flipping.
**Reason:** Engineers build twin mounts by flipping a standard breaker block.
**Status:** Approved

### 2026-10-08 — Hyper's block set replaces the legacy blocks
**Decision:** Sammy will add Hyper's current block set to `blocks/`. The configurator is
built around those blocks, not the legacy `SCHEM_*` files.
**Reason:** None of the 8 references use the legacy `SCHEM_*` blocks.
**Status:** Approved

### 2026-10-08 — Current scope: the 3-line diagram
**Decision:** Nail down the 3-line (power) diagram first. Other schematic pages (control,
thermal sensors, comms, elevation, TOC) come later.
**Reason:** Get the core page right before expanding to the whole drawing set.
**Status:** Approved

### 2026-10-08 — Layers handled automatically
**Decision:** The configurator draws every item on the correct layer (BUS, GROUND, TEXT,
etc.). Layer names live in config; the user never chooses layers.
**Reason:** Consistent drawings without extra work for the user.
**Status:** Approved

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
**Status:** Approved (clarified 2026-10-08: flipping is allowed, see "Mirroring is allowed")

### 2026-10-07 — Section width
**Decision:** Section width: dividing lines sit 5 units outside the section's outermost component.
**Reason:** Baseline
**Status:** Approved (clearance changed to 10 on 2026-10-08, see "Margins and divider clearance")

### 2026-10-07 — Shared dividing lines
**Decision:** Adjacent sections share one dividing line, giving 10 units between outermost components.
**Reason:** Baseline
**Status:** Approved (with clearance 10, the gap is now 20)

### 2026-10-07 — Page drawable area
**Decision:** Page drawable area: ~500 W x 300 H.
**Reason:** Baseline
**Status:** Superseded 2026-10-08 by "Page size and title block from the reference"

### 2026-10-07 — Standard margin
**Decision:** Standard margin: 10 units per side.
**Reason:** Baseline
**Status:** Superseded 2026-10-08 by "Margins and divider clearance"

### 2026-10-07 — Margin relaxation
**Decision:** Margin relaxation: if one more section fits with 5-unit margins per side (10 total gained),
place it on the page. Otherwise it moves to the next page.
**Reason:** Baseline
**Status:** Approved (rule kept; values now 5 / 2.5, see "Margins and divider clearance")

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
**Status:** Approved (size measured 2026-10-08: 82.41 x 70.96)

## Section composition

### 2026-10-07 — Main bus
**Decision:** Main bus runs horizontally, left to right.
**Reason:** Baseline
**Status:** Approved

### 2026-10-07 — Vertical bus
**Decision:** Each section has a vertical bus that branches up and/or down from the main bus
(direction depends on available space).
**Reason:** Baseline
**Status:** Superseded 2026-10-08 by "Breaker arrangement vocabulary" (not every section has
a vertical bus; arrangement and direction are the engineer's choice)

### 2026-10-07 — Feeder breakers
**Decision:** Feeder breakers attach to the vertical bus: left/right pairs, or a single breaker.
**Reason:** Baseline
**Status:** Superseded 2026-10-08 by "Breaker arrangement vocabulary"

### 2026-10-07 — Main breakers
**Decision:** Main breakers come in from the top and start the drawing.
**Reason:** Baseline
**Status:** Superseded 2026-10-08 by "Breaker direction is the engineer's choice"

### 2026-10-07 — Tie breakers
**Decision:** Tie breakers (new): connect input bus to the rest of the bus. Shown inline as a break in
the horizontal main bus, at the main breaker's elevation (to confirm).
**Reason:** Baseline
**Status:** Superseded 2026-10-08 by "Tie breakers are vertical"

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
