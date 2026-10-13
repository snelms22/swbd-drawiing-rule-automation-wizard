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

### 2026-10-09 — Build the master drawing with the real program (Option A)
**Decision:** No throwaway script. Each approved part is added to the layout engine (with
tests), then the AutoCAD step is written. The master drawing is the program's first output.
**Reason:** No wasted work; every approved rule becomes tested code.
**Status:** Approved

### 2026-10-09 — Page style comes from Sammy's restyled ES_01
**Decision:** Every 3-line page uses the style of ES_01 in GND_Section_Devider_REFERENCE
(dividers, ground bus, ground symbol, section labels at the same heights on every page).
**Reason:** Sammy restyled page 1 as the example; page 2 was not edited.
**Status:** Approved

### 2026-10-09 — Section labels and "GROUND BUS" text
**Decision:** "SECTION n" labels and the "GROUND BUS" text are on layer 0, style Hyper_Text,
height 1.25 (same size), no underline. Section labels sit below the ground bus, centred
under their section.
**Reason:** Layer 0 matches most drawings; one text size keeps it consistent.
**Status:** Approved

### 2026-10-09 — Divider placement
**Decision:** One divider between adjacent sections. None at the start of the lineup and
none at the end. When a section is the last one on a page and the next section starts on
the next page, its divider is drawn at the end of the current page; if it can't fit there,
it goes at the start of the next page.
**Reason:** Sammy's rule; matches the restyled ES_01.
**Status:** Approved

### 2026-10-09 — A section may continue across a page break
**Decision:** A section can be split across a page break when that makes sense; there is
no divider at that break. When to split, and how, is still to be defined.
**Reason:** Seen in practice; avoids wasting a page.
**Status:** Approved (concept) / To confirm (rules)

### 2026-10-09 — Page-part details
**Decision:**
- "Can't fit" for an end-of-page divider means it would run down through the title block;
  it then goes at the start of the next page.
- A divider between two sections that sits over the title block stops at the title
  block's top edge. No warning.
- On the last page the ground bus stops at the end of the last section.
- A section label that would land in the title block moves up to sit just above it
  (gap 1.34, in config).
**Reason:** Sammy's answers to the page-part questions.
**Status:** Approved

### 2026-10-09 — Sections have no names
**Decision:** Sections are identified only by their position in the lineup and labelled
"SECTION n". Descriptive labels (like "52-F1") belong to components, not sections.
**Reason:** That is the only section label the drawing needs.
**Status:** Approved

### 2026-10-13 — Approved styles win over reference drawings
**Decision:** The styles already approved here (e.g. Sammy's restyled ES_01 page style) are
kept. Most reference drawings are in the old style; they are only raised when they add
something new to the rule set. Arrangements in a reference can be drafting errors (the
sideways main breaker in CORRECTED_FIXED_011511 ES_11 is wrong and will not be supported).
**Reason:** Sammy, 2026-10-13.
**Status:** Approved

### 2026-10-13 — Too tall: split the part below the main bus first
**Decision:** When a section's above and below parts don't both fit on the page, room is
made for the ABOVE part first, and the BELOW part's group-mounted column is split (cut at its
bottom, continued in a new column beside it that starts just below the main bus and runs
down), as in CORRECTED_FIXED_011511 ES_11. Only if the above part alone is too tall is it
split too (rare). Refines "Break blocks, neutral block, prompts, too-tall notice" (2026-10-12).
Details approved the same day:
- Room is reserved below for one level on each of its columns (a continuation needs more
  than column 1, since it starts `continuation_start_gap` from the bus); the above part
  gets the rest. Its continuation shares column 2 with the below part's.
- A continuation that is still too tall goes on in column 3, and so on. Only group-mounted
  parts split; the section's width grows to hold the columns.
- Column 1 is cut `vertical_bus_overhang` past its last level; a continuation column starts
  `continuation_start_gap` (15.5) from the main bus and is not connected to it. Both ends get
  the tilde (A-phase end, VERTICAL) and bracket (over B, HORIZONTAL BRACKET, not flipped).
- Numbers kept from the 2026-10-12 rule (measured ES_12): column pitch 103.22, start gap
  15.5. Columns move further apart if neighbouring breakers would come closer than
  `column_clearance` (10). Bracket gap 2.5 from ES_11 (also used at page breaks).
- The app shows a NOTICE when a section is split.
- Bracket labels: "BUS CONTINUES" where a column is cut; "FROM BELOW" (part below the
  main bus) or "FROM ABOVE" (part above) where the next column starts. Text in config.
**Reason:** Sammy, 2026-10-13.
**Status:** Approved

### 2026-10-13 — Breaker and termination feed directions
**Decision:** Main breakers and single breakers get two editor options, "Breaker Feed
Direction" and "Termination Feed Direction", each **top** or **bottom** (never up / down).
Breaker feed = which end of the breaker the cables connect to ("a bottom-fed breaker");
termination feed = which side of the cabinet they come in from ("fed from a top
termination"). Defaults: the side away from the bus (top above, bottom below). When the two
differ, the bus U-turns between the breaker and the termination, as in NTT-013630 section 1:
out of the breaker, on away from the bus `u_turn_depth` (28.43, A; B and C 5 and 10 more),
`u_turn_width` (35) to the RIGHT, and back to the breaker's far-terminal height, where the
termination block sits (flipped when fed from the top). Every U-turn follows the main bus's
phase rule (A left of B on vertical runs, above it on horizontal runs): staggered corners,
crossings without dots. The U adds its width to the section. Both values will later feed
a breaker part-number configurator.
**Bus-side feeding** (e.g. bottom-fed above the bus) is allowed: the configurator lets the
engineer pick any combination ("it does everything"). Drawn as approved the same day: the
bus comes up beside the breaker on the right (35) and U-turns over it into its top; the
cables leave its bottom, either straight to a termination block between the breaker and
the main bus (termination fed from the bottom; breaker 15 + 30 + 15 from the bus) or in a
U-turn to the LEFT and back up past the breaker (termination fed from the top; breaker
15 + 28.43 + 10 from the bus). Each U-turn adds 35 to the section width; the bus's U-turn
adds its depth to the part's height. It also gets a warning so the engineer checks it can
be built (Sammy may drop the warning later).
**Reason:** Sammy, 2026-10-13.
**Status:** Approved

### 2026-10-13 — Provisions replace "Space"
**Decision:** A group-mounted slot is a breaker or a **Provision** (the editor's checkbox
says "Provision"). The engineer types one line of info. It is drawn as in IMS-REFERENCE:
taps (with dots) from the vertical bus out to where a breaker would connect, ending there,
then a note `provision_text_gap` (10) beyond, centred on B: "PROVISION FOR" and the
engineer's line (just "PROVISION" when the line is empty). Text in config (`feeder`).
**Reason:** Sammy, 2026-10-13; matches the IMS SWBD.
**Status:** Approved

### 2026-10-13 — Every placed block gets editor fields from its attributes
**Decision:** Each library block the configurator places gets one editor field per
attribute, labelled with the attribute's prompt, read from the catalog that Audit Blocks
writes. Feeder breakers (group-mounted) and single-breaker feeders (breaker + output block)
now have fields like main breakers. The attribute the breaker's Label fills is not repeated;
attributes sharing a tag get one field. A new block needs no code for its fields: give its
attributes prompts, run Audit Blocks. This is the standard for new blocks.
**Reason:** Sammy, 2026-10-13.
**Status:** Approved

### 2026-10-13 — Single-breaker feeders and group-mounted feeders as drawn
**Decision:** Single-breaker feeder: the fixed-mount breaker block on a riser off the main
bus (15 from the bus) with the input/output block in its OUTPUT state, as in the
2026-10-12 test drawing. Group-mounted feeders use `SIE_BKR_3P_3L_ASSY_R0` on a vertical bus
(A on the left), taps to each breaker's CONN_A/B/C, nearest tap 10, dots where taps meet
the vertical bus, tees into the main bus with dots (bends where the main bus starts/ends).
Right-side breakers turn on only the mirror that goes with the visibility state in use
(config `feeder.mirror_parameter`, MIRROR-3W); the block mirrors about the vertical bus's
B phase, as in ES_12. Audit Blocks reads the block in that state and mirror, and reports
connection markers that end up outside the block. Measured from ES_12.
**Reason:** Sammy reviewed the 2026-10-12 test drawing ("it's right in your drawing").
**Status:** Approved

### 2026-10-12 — Connection markers are named point parameters
**Decision:** Blocks mark their terminals with dynamic-block point parameters named
`CONN_A`, `CONN_B`, `CONN_C`, `CONN_N`, included in flip/stretch actions. The configurator
reads them (per state and flip) into `catalog/blocks.json` and lines the bus up with them.
**Reason:** Sammy built `PHASE_LUGS_3L_R0` this way; point parameters move with the block's
actions and can be read from any inserted block.
**Status:** Approved (replaces the HS_CONN point-object proposal)

### 2026-10-12 — Room for tie breakers
**Decision:** A tie breaker stepping the bus DOWN needs the bus high enough to drop
`tie_step_height` and stay clear of the ground bus (stepping UP: low enough to rise and stay
under the top). The program makes that room itself:
1. First it raises (or lowers) the bus in the sections before the tie, as far back as they
   allow, so the bus runs level into the tie.
2. Where a section can't move that far, the bus wraps: it steps up (or down) after that
   section, then the tie steps it back.
It never suggests changing the tie's direction (that is a design choice). Only if the tie's
own section has no room is there a warning.
**Reason:** Sammy's rule (2026-10-12).
**Status:** Approved

### 2026-10-12 — Break blocks, neutral block, prompts, too-tall notice
**Decision:**
- Bus breaks (page breaks and too-tall continuations) use `3P_TIDE_R0` (3-phase tilde;
  HORIZONTAL / VERTICAL state, flips; CONN_A on the A phase, B and C follow 5 apart to the
  right or downward) plus `BRACKET_TEXT_R0` (to/from label in its LABLE attribute).
- The input/output block with neutral is `PHASE_LUGS_3L_N_R0` (states INPUT W/ NEUTRAL,
  OUTPUT W/ NEUTRAL; CONN_A/B/C/N). `PHASE_LUGS_3L_R0` is now 3-phase only.
- Prompts may repeat their default value on purpose (shows the engineer the expected
  format). The audit no longer reports that; it only reports empty prompts.
- Too-tall rule approved: a vertical bus that would run past the drawing area is cut after
  the last level that fits (tilde + bracket) and continued in a new column beside it
  (tilde + bracket), column pitch ~103, starting ~15 past the main bus (config). The app
  shows a NOTICE when it does this; it never stops the drawing.
**Reason:** Sammy's blocks and answers (2026-10-12).
**Status:** Approved

### 2026-10-12 — Bus at a page break
**Decision:** Where the bus leaves a page it runs past the page's last divider: 30 when
there is room, less when tight but never under 10, plus room for the break block's to/from
label. Room = up to the side margin, or up to the title block if the bus is beside it.
**Option A:** page fitting always keeps at least the minimum (10 + label space) free at the
end of every page. On the next page the bus starts right away at the left margin (b).
Numbers in config (`main_bus.page_break_*`); label space is a placeholder until the break
block exists.
**Reason:** Looks better and is predictable; the drawing should start right away on a new page.
**Status:** Approved

### 2026-10-12 — Bus only where it is used; step clearance; tie breaker block
**Decision:**
- The main bus runs from the first section that holds something to the last. Empty
  sections before/after have no bus; empty sections in between are passed through. Where
  the bus begins or ends at a main breaker it bends into it (no dots); elsewhere mains tee in.
- Where the bus changes height, its vertical run (10) keeps 10 clear of everything else:
  the step zone is 20 wide (config `step_width` + `step_clearance`).
- Tie breakers are drawn with the breaker blocks (fixed or draw-out, chosen in the
  editor), centred on the bus's vertical run at the section's right edge.
- A bus lowered by a tie counts toward the title block check.
**Reason:** Sammy's review of test drawings (bus ran over input text; bus drawn through an
empty first section).
**Status:** Approved

### 2026-10-12 — App behaviour from first use
**Decision:** The app opens with one empty section. Empty sections give no warning.
Group-mounted levels are all shown at once (no scrolling) and can be duplicated (copy keeps
everything but the breaker names). Warnings are plain text.
**Reason:** Sammy's first use of the app; a warning symbol caused ~0.7 s lag on Windows.
**Status:** Approved

### 2026-10-12 — Coming from Sammy
**Decision:** (1) Input/output block split into a 3-phase block and a 3-phase + neutral
block (being added to the tool palette). (2) Feeder breaker block. (3) "Too tall" means too
tall for the drawing, not the product: the run is cut and continued alongside with a
marker; Sammy will correct a reference drawing to show how. (4) A "break" block that
attaches to the end of a bus line at a page break and carries the to/from label.
**Reason:** Next pieces of the drawing.
**Status:** Approved (waiting on Sammy)

### 2026-10-12 — Audit Blocks also checks the blocks
**Decision:** Besides updating the catalog, Audit Blocks lists problems in plain words:
library open with unsaved changes (the audit read the last saved version), missing
connection markers, markers not 5 apart or not level, prompts that are empty or just the
default value, attribute text that doesn't move when the block flips, and blocks missing
from the library. It never changes the library or any drawing.
**Reason:** Engineers will rely on it to keep blocks usable.
**Status:** Approved

### 2026-10-12 — Existing drawings are not changed (out of scope)
**Decision:** The configurator does not update or change drawings that were already
generated (no redefining blocks or syncing attributes in old drawings). Out of scope for now.
**Reason:** Sammy does not want old drawings changed at this stage.
**Status:** Approved

### 2026-10-12 — Audit Blocks, and block attributes in the editor
**Decision:** An "Audit Blocks" button (first called "Refresh block catalog") re-reads every block the configurator uses
from the library (a temporary copy, in the background) and rewrites `catalog/blocks.json`:
connection markers per flip, sizes, visibility states, and attributes (tag, prompt,
default). The section editor shows one field per block attribute for main breakers and
their input block, labelled with the attribute's prompt from the block. An empty field
keeps the block's default. The breaker's Label fills `BREAKER_NAME` (config
`main_breaker.label_attribute`), so that attribute isn't shown twice.
**Reason:** Keeps the configurator in step with the library with one click; Sammy will
write clear prompts in the blocks.
**Status:** Approved

### 2026-10-12 — Markers on blocks with two ends
**Decision:** Blocks with terminals at both ends name their markers `CONN_A_TOP`,
`CONN_A_BOTTOM`, `CONN_B_TOP`, ... (breakers `3P_CB_FM_1` and `3P_CB_DO` done). Verified in a
generated drawing: every marker on every placed block lands exactly on a bus end.
**Reason:** A breaker has an A, B and C connection at the top and again at the bottom.
**Status:** Approved

### 2026-10-12 — Input block on main breakers
**Decision:** Main breakers use Sammy's input/output block `PHASE_LUGS_3L_R0` (state
"INPUT"), placed so CONN_A sits on the A-phase bus end. Top-fed mains use it flipped
("from the top"); bottom-fed mains use it as is ("from the bottom", the block's default).
Its base point sits at the base of the A-phase triangle; that is accepted for this block.
The library is always read from a temporary copy, so generating works while the library
is open in AutoCAD.
**Reason:** Sammy's block and answers (2026-10-12).
**Status:** Approved

### 2026-10-12 — Visibility states are picked by name
**Decision:** Blocks' visibility parameters can be named anything. The configurator chooses a
state by its name (e.g. "INPUT W/ NEUTRAL"), finding whichever parameter offers it.
**Reason:** Standardising parameter names is too much to keep track of.
**Status:** Approved

### 2026-10-12 — Main breaker mounting from the library
**Decision:** A main breaker is "fixed" or "draw-out" (chosen per breaker in the editor),
using the library blocks `3P_CB_FM_1` and `3P_CB_DO` (set in config, `main_breaker.blocks`).
**Reason:** Use the maintained library blocks.
**Status:** Approved

### 2026-10-12 — Old block files archived
**Decision:** Everything that was in `blocks/` moved to `blocks/archived/` (reference only).
**Reason:** Blocks now come from the shared library.
**Status:** Approved

### 2026-10-12 — Block library standard (first items)
**Decision:** In `docs/BLOCK_LIBRARY_STANDARD.md`: 3-phase blocks have their base point on
the A-phase top terminal (poles at 0 / 5 / 10, A left); revision suffixes (`_R0`, `_R1`, ...)
are used; layers inside a block are part of its design (attributes on TEXT/TXT, bus bars
on BUS, etc.) and the configurator never changes them. Connection markers: Sammy is looking
into them; until then terminals are measured and kept in `catalog/blocks.json`.
**Reason:** Sammy's review of the draft standard.
**Status:** Approved (markers and "Visibility1" naming still to confirm)

### 2026-10-12 — Input / output block
**Decision:** Sammy's input/output block will be based on the library's
`PHASE_LUGS_3L_R0` (TOP/BOTTOM ENTRY, POWER FLOW IN/OUT states), with his edits. Until it
is ready, its place is shown as an "INPUT" placeholder box.
**Reason:** The library block already covers top/bottom entry and power flow direction.
**Status:** Approved (block in progress)

### 2026-10-11 — Blocks come from the shared block library (Option B)
**Decision:** The program copies block definitions from Hyper's maintained block library
drawing (`Symbols-blocks.dwg`, Electrical Team CAD BLOCKS folder) instead of one .dwg file
per block. Its location is in config. A written standard for adding blocks to the library
is kept in `docs/BLOCK_LIBRARY_STANDARD.md`.
**Reason:** The team keeps using and maintaining that library; one source of truth.
**Status:** Approved

### 2026-10-11 — Input / output bus connection
**Decision:** An input/output block (with its label) marks where a bus starts on the
drawing, for sources and for feeders. It sits at the top or bottom of the drawing depending
on the direction of power flow, usually with a breaker: input block -> bus into the breaker
-> out of the breaker -> a bend that carries the bus on to the rest of the drawing.
**Reason:** Matches the references (incoming lugs/labels above or below mains and feeders).
**Status:** Approved (block in progress by Sammy)

### 2026-10-11 — First AutoCAD drawing reviewed
**Decision:** Bus, ground bus, dividers, text and spacing in the first generated drawing are
good for now. Revisit how the bus bars look once real components connect to them.
**Reason:** Sammy's review of `output/Example 2026-10-11 194634.dwg`.
**Status:** Approved

### 2026-10-11 — First AutoCAD step
**Decision:**
- Each run copies `templates/EW_SWBD_TEMPLATE.dwg` to a new file in `output/` (switchboard
  name + date/time), opens the copy, draws, and saves. The template is never changed.
- Use the AutoCAD 2026 that is already open, or start AutoCAD 2026. **Never AutoCAD
  Electrical.**
- Page N goes in the frame named ES_0N, at the frame's insertion point. The program first
  lists the ES frames/layouts in the copy; if there are not enough frames it stops with a
  clear message.
- Draws: main bus (each phase its own line, layer BUS), dividers (DEVIDER), ground bus and
  symbol (GROUND), "GROUND BUS" / "SECTION n" text (layer 0, Hyper_Text, 1.25), and
  placeholder rectangles for section contents on a non-plotting layer CFG_PLACEHOLDER.
- Run from a "Generate drawing" button in the app; it reports the saved file and problems.
- Bus is plain lines for now; later it will use the dynamic bus blocks (BUSSING_3PH_3W_3L).
**Reason:** Sammy's choices; gives a first real drawing to check before blocks arrive.
**Status:** Approved

### 2026-10-09 — What a section holds (Option A)
**Decision:** Each section has an **above** part (above the main bus) and a **below** part.
Each part holds one arrangement: Empty, Main breaker (above = fed from top, below = fed
from bottom), Single breaker, or Group Mounted Distribution. Any combination is allowed,
including a main on one side and something else on the other. A **tie breaker** can be
added to any section, alongside whatever else it holds.
"Above" and "below" are positions, not equal halves: the layout may move the main bus up
or down to fit what is there (e.g. nothing below and a lot above → bus moves down).
**Reason:** Covers every arrangement in the references with one simple structure.
**Status:** Approved

### 2026-10-09 — Main bus height
**Decision:** The main bus stays at the same height as much as possible. It changes height
only where a section needs room above or below it, and then only in that section. A
height change (the bus travelling up or down) adds about 10 to that section's width
(in config).
**Reason:** A level bus is cleaner and matches the physical product; stepping costs space.
**Status:** Approved. Details settled 2026-10-09:
- The bus starts **as low as possible**. As the part below the bus fills up, it pushes the
  bus up; a tall part above can push it back down. Otherwise it stays level.
- The section that causes a height change takes the step (at its left edge) and the extra
  width.
- The extra width is **10 drawing units**: the three phases are 5 apart, so A to C is 10.

### 2026-10-09 — Tie breaker sits at the right edge of its section
**Decision:** In a section that holds a tie breaker, the tie sits at the section's right
edge; the bus steps up or down there as it leaves the section.
**Reason:** Sammy's choice.
**Status:** Approved

### 2026-10-09 — Section editor layout
**Decision:** Section list on the left (add, remove, reorder, push, link). Editor for the
selected section on the right: Above and Below each pick Empty / Main breaker / Single
breaker / Group Mounted; group mounted has add twin / add single / remove / reorder / flip
levels and a label (or SPACE) per slot; tie breaker checkbox with label and step up/down.
Ratings and block choice come later. Page preview and warnings stay as they are.
**Reason:** Approved "for now".
**Status:** Approved

### 2026-10-09 — Group mounted levels: order and sides
**Decision:** Levels in a Group Mounted Distribution are counted outward from the main bus.
Single-mount levels alternate sides automatically; the engineer can flip any level.
**Reason:** Matches the physical stacking and the references; flipping covers exceptions.
**Status:** Approved

### 2026-10-09 — Twin mount and single mount can share a vertical bus
**Decision:** Within one Group Mounted Distribution, twin-mount levels and single-mount
levels can be mixed on the same vertical bus. Example: ES_12 of GND_Section_Devider_REFERENCE.
**Reason:** Seen in real jobs (NTT-013627, NTT-013630).
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
