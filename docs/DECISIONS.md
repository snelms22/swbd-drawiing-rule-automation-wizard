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
**Status:** Approved. Changed 2026-11-23: pushed to GitHub, see "2026-11-23 — GitHub remote;
the reference DXFs kept out of git".

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

### 2026-10-15 — Project files: extension and saving
**Decision:** A switchboard project is saved as one plain-JSON file with the extension
`.swbd` (each future product line gets its own extension). Saving is manual only (Save /
Save As), with a Save / Don't save / Cancel prompt when unsaved changes would be lost. No
autosave for now.
- The file holds only what the engineer entered (sections, breakers, feeds, attribute
  values), with `format_version` (older files are upgraded on opening) and `saved_with`
  (the app version). Layout is always worked out again. Attribute values a block no longer
  has are kept and reported on opening.
- Default folder: `CAD BLOCKS/CONFIGURATORS/Jobs` (every user, every product line).
- Saving overwrites the same file (no revisions for now).
- Every generated drawing gets a copy of its project next to it (same name, `.swbd`).
- A **switchboard library** (`switchboard_library/`, shipped with the app) holds ready-made
  switchboards, starting with the sample. File > Open from Library opens one as an untitled
  copy, so saving never changes the library. File > New = one empty section.
- The project's name is its file name.
**Reason:** Sammy, 2026-10-15: the tool will be remade for other product lines.
**Status:** Approved

### 2026-10-15 — Releasing the app to the team
**Decision:**
- The app is packaged with PyInstaller (it carries its own Python; Python already installed
  on a PC doesn't matter).
- Releases live in SharePoint: `CAD BLOCKS/CONFIGURATORS/Switchboard Configurator/`
  (`CONFIGURATORS` will also hold future product lines), each version in its own
  `Releases/X.Y.Z/` folder, with `latest.txt` naming the current one.
- Each PC runs a one-time installer: desktop + Start menu shortcut, and an AutoCAD bundle
  that adds a ribbon tab. A launcher copies the latest version to the PC and starts it, so
  updates reach everyone with no action. If a newer version appears while the app is open,
  it offers the user a restart.
- Names: the app and its icon are **Switchboard Configurator**; the AutoCAD ribbon tab is
  **Hyper**.
- The installer is built first; IT approval is sought afterwards.
- **Audit Blocks is removed from the app.** Sammy owns the block audit; Claude runs it on
  request during development (`tools/audit_blocks.py`).
**Reason:** Sammy, 2026-10-15.
**Status:** Approved (to build after saving / opening projects)

### 2026-11-19 — Ground strip always; the meter's ground; the Ethernet switch sized for its ports
**Decision (Sammy, 2026-11-19):**
- **The ground strip is drawn whenever there is a power supply**, even with nothing else to
  connect ("better to add it than not"). (It already was, with the supply feeding the 24 V;
  now tested.)
- **The UMG 801's ground is its DIGITAL_GND, for now**: by reference, a tilde with a label at
  each end ("TO 1TBG" at the meter, "FROM PM-1" on the strip), no wire across. Its
  ANALOG_GND stays unwired. Config: `ground.pin_markers` gains DIGITAL_GND.
- **Ethernet switches:** Sammy added three blocks, the sizes supply chain offers:
  Ethernet_Switch_5PORT / _8PORT / _16PORT (NAME attribute "ES-#"). The program counts what
  plugs into the switch and picks the smallest size with a port for each, so the block too.
  One port always has the **customer's connection**.
**As built:**
- What needs a port (`ethernet_connections` in devices.py): each 3WA's COM190 (its comms
  module), each COM800 (the COM060s reach the switch through it), each power meter, and the
  customer's connection. The showcase needs 9: the 16-port switch.
- More than 16: the 16-port with a warning. More than one switch ticked: each sized for the
  whole lineup, with a warning, until we know how they share the connections.
- The switch block stands in the switch's place in the row, NAME "ES-1", a 24 V load like
  the others (24V+ / 24V- markers). The customer's connection: first built on the last port,
  then port 1 (below). Any ground pin on it goes to 1TBG by reference.
- **The library's switch blocks have no markers yet**, so until they do the switch stays a
  box that names its size ("ETHERNET SWITCH / 16 PORT"), with a note in Generate's list.
  Markers it needs: `24V+` (top of the left edge), `24V-` (bottom of the left edge), each
  port `PORT_1` ... `PORT_n`; a ground pin `G` if it has one. Config: `ethernet_switch` in
  devices.json.
- **Later the same day (Sammy's answers):** the customer's connection on **port 1**; **one
  spare port** kept free when picking the size ("might take it out later"); **both ends of
  every cable show**: at the switch a stub on its port ending in a tilde "TO PM-1 SECTION 4"
  ("CUSTOMER CONNECTION" on port 1), at the device a stub ending in a tilde "TO ES-1
  SECTION 1", both stubs carrying the cable's number (E-001 the customer's on port 1, then
  E-002 ... in port order). The devices take ports 2, 3 ... in lineup order. A box (a trip
  unit with its COM190, a COM800) takes its cable on its right edge, half way down; the
  switch's box down its right edge, a port every 5. Config: `ethernet_switch` in devices.json.
- **The meter's end of its cable isn't drawn yet:** the UMG 801's RJ45 ports (right edge, y
  -6.5 and -12.5) sit where its remote display hangs off the USB just below them (-18.5), so
  a stub from RJ45A runs into the display and its USB line. Proposed block tweak: USB above
  the RJ45 ports on the right edge, so the display sits up top and the cable goes out under it.
- **Bracket text (Sammy, 2026-11-19):** a flipped bracket's label lands right only when its
  text goes in before the flip. Generate now fills every block's text before its flips.
- **One switch per lineup for now (Sammy, 2026-11-19):** if more than one section is ticked,
  the first section's switch is drawn (ES-1) and Generate warns the others are left out.
- **Blocks (Sammy, 2026-11-19):** the switch blocks have their markers: `24+` / `24-` (config
  names them, the meter's are `24V+` / `24V-`), ports `PORT_1` ... in two columns, the left
  column's cables leaving to the left, the right column's to the right. The meter's USB
  moved above its RJ45 ports, so its cable leaves RJ45A to the right under the remote
  display (`ethernet_pin` on the meter model).
- **Wire numbers:** two stubs with the same number on one page (both ends of a cable, or a
  ground drawn by reference near the strip) each get their label.
- **Bracket text checked** in the generated drawing: a flipped bracket's label now ends at the
  bracket whatever its length (before, every label started at the same spot and longer ones
  ran over the bracket).
**Reason:** Sammy, 2026-11-19.
**Status:** Built 2026-11-19 for 2.3.1. Open: several switches sharing the connections (later).

### 2026-11-19 — Every tilde says where its wire goes; a fuse's phases to a meter in another section
**Decision (Sammy, 2026-11-19):**
- **Every tilde has a tag** saying where the connection goes, and the other end has one too.
  Wire numbers (E-001 ...) go on both ends, like every other wire. Tildes at a bracket take
  their tag from the bracket ("FROM SHEET 4"); tildes on their own carry it in their text.
- **A fuse's phases to a meter in another section** should carry on the same way through the
  drawing, not stop as bare stubs on the splits; up on top if there's room, otherwise tildes
  saying which split they go on through. Where they reach their meter they go straight into
  it, no tildes.
- **As built:**
  - Into the meter: when the fuse is in a section to its left, the phases come in on the
    split on the meter's left and run straight into VN / V3 / V1, each turning in a lane of
    its own left of the meter's 24 V lanes. The meter keeps no FROM bracket. A still crosses
    B and C (it goes to the lowest pin), as when the fuse is beside the meter.
  - Passing a section with devices: a labelled stub on each split pin, its tilde saying
    "TO 5SSM-2" at the end it leaves by and "FROM 5SSM-1" at the end it came in by.
    Over the top was checked and doesn't fit: the 24 V comes in from the same side both
    above (+) and below (-) the phases, so a wire drawn through crosses 24 V wires (6 to 9
    times in section 5 of the showcase job). A section with nothing in its row still gets
    the straight wires across.
  - Any other stub on a split says where its wire goes: "FROM FA-2" in the fuse's own
    section when the fuse stands on its own, "TO PM-3" in the meter's section when the
    meter can't take the wires straight in (its fuse is to its right: the phases would go
    round the meter and its 24 V, so it keeps its FROM bracket).
  - Meters stand in their section's row whenever the section has splits, with or without
    the 24 V.
- **Tilde text is hidden by the block:** TILDE_R0's HORIZONTAL state (every tilde on a
  horizontal wire) shows neither TEXT_H nor TEXT_V, so "TO ES-1 SECTION 1", "TO 1TBG",
  "FROM PM-1" etc. are filled in but don't show. Block fix for Sammy: make TEXT_H visible in
  the HORIZONTAL state.
- **2026-11-20 (Sammy):**
  - **No step in A's wire:** the left split is moved up or down so phase A runs level into
    its pin (the supply's L1, the meter's V1), as when the fuse lies beside the meter. It may
    stand out of the row into the gap above or below it (ladder_zone_gap), never into the
    24 V wires.
  - **A power supply** fed from a fuse in a section to its left takes its phases straight from
    the split too (L1-L3 run top to bottom like the split's pins: no crossings). If no ladder
    draws it (it doesn't feed the 24 V), it keeps its FROM bracket.
  - **Split stubs 12 long** (were 6), like the Ethernet and ground stubs, so the wire number
    and the tilde's text don't run together.
  - **TILDE_R0 fixed by Sammy:** the HORIZONTAL state shows TEXT_H just past the tilde, on the
    wire's line. Later the same day he added TEXT_H / TEXT_V to the flip action, so on a
    mirrored tilde (a wire leaving to the left) the text sits on the far side too: AutoCAD
    puts its end 0.5 left of the tilde, as it starts 0.5 right of an un-mirrored one.
**Reason:** Sammy, 2026-11-19: "it's not good that they just cut the way they do."
**Status:** Built 2026-11-19 / 2026-11-20 for 2.3.1. The room for a tilde's text: see
"2026-11-20 — A tilde's text on one line or two, with room kept for it".

### 2026-11-20 — A tilde's text on one line or two, with room kept for it
**Decision (Sammy, 2026-11-20):** with the text on the far side of mirrored tildes, PM-1's
"TO ES-1 SECTION 1" ran into the switch's "TO TB02 COM190 SECTION 3". Sammy: make the
attribute multi-line so long labels stack ("hopefully we would not have any overlap"), and
"drag out the boundary if needed to make sure it stays no more than 2 lines and sacrifice the
width only in that case". Approved: the program picks the lines itself, and the layout keeps
room for the text (option A).
- **One line or two:** one line up to `wire_break_text_one_line` characters (12); longer,
  two lines broken at the space that makes the longer line shortest ("TO MCB01 COM190" /
  "SECTION 1", "CUSTOMER" / "CONNECTION"). Never three: if that line is still long, the
  label is just wider. No space to break at: one line.
- **Too close for two lines:** where the next wire is nearer than two lines need (their
  height plus `wire_break_text_clearance`), the label stays on one line. The ground strip's
  FROM stubs (2.5 apart) are the case today; the switch's ports (5 apart) have room.
- **Only with a multi-line attribute:** Audit Blocks records which attributes are multi-line
  (`"multiline": true` in the catalog). Until TILDE_R0's TEXT_H is, labels stay on one line,
  and the room kept matches.
- **AutoCAD:** the line break is written as AutoCAD's `\P` and the attribute's box width set
  to 0, so AutoCAD never wraps the text again on its own. The drawing shows the program's
  lines, as the preview does. (Checked in a throwaway drawing: the text and the 0 width are
  taken.)
- **Room kept (option A):** a tilde's size takes in its text, so whatever is placed by size
  keeps clear of it (the row's devices). The program can't measure AutoCAD's font, so the
  width is estimated: characters x `wire_break_text_character_width` (1.15; measured in
  AutoCAD 0.89 to 1.13 at height 1.25). The ground strip's stubs and their text stop a lane
  short of the - terminals.
- **Checked in the showcase (labels still one line):** no tilde text runs into other text or a
  wire. Keeping room for the switch's one-line labels pushed ES-1 onto section 1's second
  page; with two-line labels it fits on the first again (layout checked).
**Reason:** Sammy, 2026-11-20.
**Status:** Built 2026-11-20 for 2.3.1. Sammy made TEXT_H and TEXT_V multi-line 2026-11-23;
Audit Blocks recorded it. Open: check a mirrored two-line label in AutoCAD (its lines may
stay left-aligned, leaving the shorter one short of the tilde).

### 2026-11-23 — The power supply's section: fuses beside the + wires, room for 11+ fuses
**Decision (Sammy, 2026-11-20 / 2026-11-23):** more than 8 fuses didn't fit (each fuse is 20
tall, and its wire adds a level along the top). "There is plenty of space to fit more if the
first fuses and the power supply get moved up", the ground strip into the empty space, its
labels vertical. The biggest job seen has 12 fuses: "build the 11 logic and see if that'll do
for now"; past that the logic may change, later, when needed. Plan 1-3 approved:
1. **The supply and its fuses move up**, beside the + wires instead of under them: as far as
   no fuse's wire has to turn down (the first then runs straight across along the top), and
   staying ladder_zone_gap under any + wire passing over them (to a split on the left). The
   ladder is built twice: once to find the + wires' heights, then drawn with the supply up.
2. **The - terminal group stands right of the fuses**, in a slot of its own after the + slots.
   The supply's - drops between the supply and its fuses, runs under the fuses a lane below
   the lowest, and comes into its group from above, or from below when the fuses reach lower
   than the - wires. The - wires no longer run under the fuses (unless one goes on to a split
   on the left: then they run below the supply and its fuses, as before).
3. **The ground strip (1TBG) stands under the supply**, ladder_zone_gap under it, left of the
   fuses. The supply's ground drops in from its pin; TO GROUND BUS leaves on the left as
   before. Each other device's ground goes out on the right to a lane of its own (the top
   one outermost, so none cross) and down to an upright tilde flipped up-down (Flip state2),
   its text (TEXT_V) under it reading up. The lanes stay a lane short of the supply's - lane.
- **Measured on the showcase lineup** (real blocks, layout only): 8 fuses fitted before, 12 now.
  The showcase's own 6 fuses: no new crossings (the 7 known ones).
- **The fuses add lanes**, and the - has its own slot now, so the supply's section is wider:
  with 7 or more fuses its row carries on to one more page than before.
**Reason:** Sammy, 2026-11-20 / 2026-11-23.
**Status:** Built 2026-11-23 for 2.3.1; Sammy to look at the drawing and say whether to keep it.
Open (found 2026-11-23, there before this change): a + terminal group that feeds a device in
its own section, ahead of fuses for the split, sends that wire low, across the later fuses'
risers (the trip units' shared fuse with meters in other sections).

### 2026-11-23 — GitHub remote; the reference DXFs kept out of git
**Decision (Sammy, 2026-11-23):** the history is pushed to GitHub: `origin` is
github.com/snelms22/swbd-drawiing-rule-automation-wizard (`main` tracks `origin/main`).
GitHub refuses files over 100 MB and Sabey-011485.dxf is 135 MB (four more are about 70 MB),
so the reference DXFs are kept out of git: the history was rewritten without
`docs/SWBD_reference/*.dxf` (every commit and release tag) and `.gitignore` leaves them out.
The DXFs stay on disk in that folder (backed up by OneDrive); their PDFs and INDEX.md stay
in git. Claude still commits and pushes only when Sammy asks.
**Reason:** Sammy, 2026-11-23 (chose this over Git LFS, which would use most of GitHub's free
1 GB, and over dropping only the 135 MB file).
**Status:** Done 2026-11-23. A bundle of the history before the rewrite was kept.

### 2026-11-17 — Ground terminal strip in the power supply's section
**Decision (Sammy, 2026-11-17):**
- A ground terminal strip in the section that has the power supply, wired with the same
  rules as the rest, named like the others: **1TBG** (`{section}TBG`). Same Terminal_Block.
- **The supply's ground** (pin `G` on 3P_PWR_SUP) is wired straight in. **One wire out "TO
  GROUND BUS"**, a tilde and a bracket at its end (as in NTT-013628: TB1-G -> G001 TO
  GROUND BUS).
- **Anything else with a ground pin**, in any section, is wired by reference, the same idea as
  a wire through a shipping split: a stub from its pin ending in a tilde that says "TO 1TBG"
  (the tilde's own text), and on the strip a stub with the same wire number ending in a tilde
  that says "FROM PM-1".
**As built:** the strip stands at the bottom left of the supply's ladder, under the supply,
level with the - terminals and left of them. The supply's ground drops into its top (3_TOP),
the wire to the ground bus leaves its left side, the devices' stubs its right side (stopping
clear of the - terminals). Wires on WIRE_GROUND, numbered G001 (to the ground bus), G002 (the
supply's), then the devices in lineup order. A device's ground pin is a marker named in
`ground.pin_markers` (config: G, GND, PE). The UMG 801's ANALOG_GND / DIGITAL_GND are signal
grounds and aren't in that list (to confirm with Sammy). Config: `ground` in devices.json.
**Reason:** Sammy, 2026-11-17.
**Status:** Built 2026-11-17 for 2.3.1.

### 2026-11-17 — 24 V ladder: devices in a row, + along the top, - along the bottom (design)
A rewrite of how each section's 24 V group is drawn (not of the 24 V plan). Sammy asked for the
details to be settled before building.
**Decision (Sammy's answers, 2026-11-17):**
- **Fuse per section: not happening** (the team). Each device keeps its own fuse; the trip
  units share one, split on terminal blocks as now.
- **Devices** are tall and skinny, 24V+ at the top of the left edge and 24V- at the bottom of the
  left edge. Sammy moves the - pin on his blocks (the meter's included). The boxes do the same
  (config: + from the top, - from the bottom), back to full height once they sit in a row.
- **The ladder, on every section's page:**
  - The devices stand in one row, tops lined up. Each gets its + from a wire that comes down
    in the gap to its left and its - from a wire that comes up in the same gap.
  - The + wires run along the top: the farther a wire goes, the higher it runs. The - wires
    run along the bottom: the farther it goes, the lower. So no 24 V wire crosses another.
  - Terminal blocks: the TB+ at the top, the TB- at the bottom.
- **Source section:** the power supply (its fuse lying left of it) and its fuse column at the
  left. Each fuse's wire climbs to its place along the top. The top fuse feeds the device
  furthest away, so the fuse order follows the row; FD-1 is the top fuse. The supply's - drops
  to the TB- at the bottom left.
- **Other sections:** the incoming split sits at the left, centred between the top and bottom.
  Its + wires go up to the TB+ (or straight along the top when they only pass through), its -
  down to the TB-. The outgoing split sits at the right end, centred, + coming down into it,
  - coming up.
- **Split pins:** + on top (the farthest-going first, those that stop or branch in the next
  section last), wires that aren't 24 V in the middle, - at the bottom.
- **Row order (left to right):** meters, the Ethernet switch, each COM800 with its COM060s next
  to it (small boxes, no 24 V: the Siemens cable powers them), then the trip units (with their
  COM190). A list in config. Why: a meter's fuse and FROM bracket need the gap on its left,
  and phases coming through a split land straight in; with the trip units last, their shared
  circuit's two branches (to the trip unit and on to the next section) sit side by side.
- **Meters always get a place in the row**, wired or not (24 V now, 120 V later).
- **A section wider than a page** carries on on its next page. Its shipping splits stay at the
  section's ends: the incoming on its first page, the outgoing on its last. Where the page
  breaks, every wire that carries on ends in **one bracket spanning the whole side** ("TO
  SHEET 6"), from the top + wire to the bottom - wire, and picks up on the next page from one
  bracket ("FROM SHEET 5"), no tildes (Sammy chose option C of the sample drawing: other wires
  can break and start again the same way). Each wire keeps its number.
- **Wires that aren't 24 V:** where they pass through a section that has devices, they are
  labelled stubs on the split pins (a wire can't cross the row there without crossing 24 V).
  Signal wires may have tildes, with clear information on where they go. **No tildes on
  24 V.**
- **A lone fuse** goes wherever it fits, near the shipping split its phases leave by. Its phases
  run straight into the split's middle pins.
- **Ethernet (later, once the switch is set up):** a short labelled stub with a tilde at each
  end (the switch's port, the device's port) saying which section it goes to. Ethernet doesn't
  go through the shipping splits.
- **Later:** the ATC (half a page or more; its signals through the splits follow the stub rule),
  120 V, and mechanically vs electrically operated breakers.
**How it is built:**
- `control_power.py`: the plan keeps its circuits, terminal blocks and wire numbers. Only the
  fuse order and the split pin order change, both by where the wires go.
- A new module `src/layout/power_ladder.py` draws the ladder. `device_pages.py` (about 1,500
  lines) hands it the devices and keeps building the meters, fuses and boxes.
- Spacings, the row order and the box pins in config. The tests count crossings: none
  allowed between 24 V wires.
**Status:** Approved 2026-11-17 (Sammy: "let's go with that", after the page-break sample).
Built 2026-11-17 for 2.3.1. As built:
- `src/layout/power_ladder.py` draws the ladder; `src/layout/device_units.py` holds the
  drawing pieces (wires, units) it shares with device_pages.py. The plan orders the fuse
  column and the split pins (`_fuse_key`, `_boundary_key` in control_power.py).
- The splits stand at the page's ends when the ladder fits on one page (as on 2026-11-11);
  on a section that takes more pages, the outgoing split ends its last page's row.
- Terminal groups: + takes its wire in on a bottom point (1_BOTTOM), - on a top point
  (2_TOP); the wires out leave from the side points, stepping down in lanes beside the group.
- Boxes back to full height (trip unit, Ethernet switch 25 x 60). The COM800 box is tall too
  (25 x 40), and COM060 boxes small (20 x 15), breaker and module on two lines. All config.
- The showcase drawing: 97 crossings before, 5 now. Four are the meters' voltage (A crosses
  B and C, from the meter's pin order). One is the trip units' shared wire (below).
- **Crossings the ladder can't avoid:** the trip units share one fuse, so their wire runs
  through every section, branching down to a trip unit in each. A wire that passes a section
  where it branches and ends in a section where it branches again (or ends left of the trip
  unit) has to cross it once. About one crossing per such device. With the supply in the
  middle of the lineup, its wire branches both ways from one terminal group and adds a few
  more (4 in the test job). Offered: in the last section the trip units' wire reaches, stand
  the trip unit first in the row (removes the showcase's one). Sammy, 2026-11-17: the one
  crossing is okay; the trip units stay last in the row.

### 2026-11-17 — Bracket stretched to its wires; wires cross only where they must; device shapes
**Decision / status:**
- **Bracket stretched (Sammy, approved; he did it by hand first):** beside a block's pins (a
  meter's CT set, or its voltage FROM another section) BRACKET_TEXT_R0 is stretched with its
  own `Distance1` setting so its grip lines up with the outer wire. Read from the block: as
  drawn, Distance1 is 10 and the grip is 5 below the middle; each unit more moves the grip
  and both arms one unit out, so the bracket stays centred. Six CT wires (25 top to bottom)
  get 17.5; the meter's VN/V3/V1 (15) get 12.5; three wires 5 apart keep 10 and the setting
  is left alone. The block draws the stretch; the program only sets the value. Other
  brackets (3-line, fuses, splits) are unchanged. Config: `bus_break.bracket_stretch_*`.
- **Wires don't cross unless they have to (Sammy's request).** The test drawing had 97
  crossings on the section pages, most avoidable. Claude proposed ordering rules (split pins,
  fuse column, a fuse's phases above the incoming split, terminal points and lanes in order,
  a crossing count in the tests). Sammy then asked about putting the - along the bottom of
  the page and at the bottom of each block. Claude's answer: it removes the - / + crossings
  only with the devices side by side in a row (+ down from the top, - up from the bottom); in
  today's stacked column a - wire still crosses one + per device it passes. Pending Sammy.
- **Device blocks to come (Sammy):** the trip unit and the Ethernet switch will be tall
  rectangles like the meter, their 24 V pins at the top (as the meter's are). The trip unit's
  block includes its COM190, wired to it inside the block. The COM190 holds the Ethernet port:
  later, a wire with a tilde from the Ethernet switch (once the switch is set up).
- **Boxes reshaped (Sammy approved):** the trip unit and Ethernet switch boxes are tall
  (25 x 40), + and - on the left edge 2.5 and 7.5 below the top (config). 40, not 60: in the
  stacked column, 60-tall boxes ran section 1 off the bottom of the page. A 3WA's comms
  module is named on a second line in its trip unit's box and gets no box of its own; with no
  supply to feed the trip units it keeps its own box, as before.
**Reason:** Sammy, 2026-11-17.
**Status:** Bracket stretch and box shapes built 2026-11-17. Crossing rules and the - along the
bottom pending Sammy.

### 2026-11-17 — Fuse markers in; new UMG 801 block; a fuse per section (to the team)
**Decision / status:**
- **Fixed fuse markers:** Sammy named them `<pole>_LINE` / `<pole>_LOAD` (`1_LINE`, `1_LOAD`
  ...), on the line side (left, x 0) and load side (right, x 10). Config now uses them
  (`control_power.fuse_line_marker` / `fuse_load_marker`). The 24 V fuses are drawn as the
  1P_FUSE_1 block, not boxes. Block standard rule 13 is updated.
- **New UMG 801 block:** Sammy finished it, to go into the next test drawing. In the library
  it is spelled `Janitzia_UMG801_Rev2`.
  - Every pin is on an edge, for horizontal wires.
    - Left, top down: 24V+, 24V-, VN, V3, V2, V1, I1+ to I4-, ANALOG_GND, DIGITAL_GND.
    - Right: I5+ to I8-, DI_COM, DI_4, DI_3, USB, RJ45A/B.
  - A `NAME` attribute takes the whole name ("PM-#").
  - The old input blocks (Voltage_UMG801_Input, CT_Current_Input) don't fit its pins.
  - **How it is wired (Sammy approved Claude's proposal the same day; "use the block as is"):**
    1. `NAME` gets the meter's whole name, "PM-1".
    2. **Voltage:** its fuse lies to the meter's left, phase A level with its pin (one straight
       wire). The phase-to-pin mapping is kept: A to V1, B to VN, C to V3, V2 unused. B and C
       turn in lanes between the fuse and the CT inputs, C's lane right of B's, so they don't
       cross each other. A fuse in another section: tildes and a "FROM FA-n SHEET n" bracket
       on the voltage pins, as the power supply has.
    3. **CTs:** each set's six wires go straight into its pins, I1-I3 on the left (the second
       set I5-I7 on the right). Each wire is a labelled stub (3+ / 3-, numbered by the set:
       set k = 3k-2 ... 3k) with a tilde, and one bracket "FROM STB-k SHEET n" is centred on
       the set. The bracket is drawn for three wires, so on six it covers the middle. (Fixed
       later the same day: the bracket is stretched to the wires, see "Bracket stretched".)
    4. **Remote display:** on the side its USB pin is on, the right for Rev2.
    5. **24 V (option A of 2026-11-12, built):** the meter is a 24 V load on a fuse of its own.
       It is drawn whole, with its fuse, CT inputs and remote display, in its section's 24 V
       group, its left edge at the loads' column. The 24 V wires run straight to its pins
       over its fuse, which sits below them.
  - Config: `power_meters` in devices.json (`voltage_pins`, `current_pins`,
    `current_wire_layers`, `supply_pins`, `name_attribute`). Meters with input blocks still
    work the old way (no meter uses them now).
  - Without a supply that can feed it, the meter is drawn on its own, its 24 V pins unwired.
  - **Not changed:** a meter whose fuse is in another section still gets the FROM bracket on
    its voltage pins. The phases stop at stubs on the shipping split (2026-11-11). With the
    new block they could run straight from the split into its pins; Sammy's call.
- **A fuse per section (Sammy's proposal, 2026-11-17; for the team's meeting the same day):**
  where a section has more than just a trip unit, that section gets its own fuse beside the
  power supply. Its one + wire goes through the shipping splits to the section, where a
  terminal block powers everything in it. This would change "each device its own fuse"
  (2026-11-10). Not built. In the program, which loads share a fuse is decided in one place
  (`plan_control_power` in control_power.py); terminal blocks, splits and wire numbers follow.
**Reason:** Sammy, 2026-11-17.
**Status:** Fuse markers built. UMG 801 Rev2 with its 24 V built 2026-11-17 (test drawing for
the team). The fuse per section is not happening (the team, 2026-11-17).

### 2026-11-16 — 2.3.1: 24 V through fuses and terminal blocks (plan approved, as built)
**Decision (Sammy's answers, 2026-11-16):**
- **The plan of 2026-11-13 is approved** ("This plan looks good, lets move forward"). It goes out
  as 2.3.1. The UI release (2.4.0) follows once Sammy is happy with the drawing logic.
- **Bridge:** the `BRIDGE` layer is in the template now. A layer can't make a polyline; the
  program draws the bridge as a polyline **0.5 wide**.
- **24 V fuses: the library's fixed fuses** `1P_FUSE_1` (with `2P_FUSE` and `3P_FUSE_1` for later),
  to which Sammy added attributes. On a column of fixed fuses, the bridge runs between the
  line-side connection points (the same point serves as its top and bottom).
- **COM800:** takes 24 V on a fuse of its own. The COM060s connect to it with a Siemens
  proprietary cable that carries power and comms; how that is shown comes later.
- **Several connections on one pin are numbered** (`24V+_1`, `24V+_2`): approved, and added to
  the block standard (docs/BLOCK_LIBRARY_STANDARD.md, rule 10).
- **Wire labels stay as they are** ("if it ain't broke, don't fix it"): the program writes
  them as plain text. The `WIRELABEL` block in Sammy's sketch is the one the team's wire
  label LISP uses; the program doesn't need it.
**As built (2.3.1):**
- **What takes 24 V:** every 3WA's trip unit (all on one fuse), the Ethernet switch and each
  COM800 (a fuse each). They are boxes until their blocks exist, with + and - on their left
  edge. The COM190 and COM060 boxes get no wires. Without a power supply that can feed
  them, the Ethernet switch is an unwired box as before, and the trip units and COM800s
  aren't drawn.
- **COM800s:** one in each section with a group-mounted breaker that has a comms module.
  *This is the program's placeholder rule until Sammy says how many there are.* Named
  COM800-n through the lineup.
- **Fuses:**
  - FD-1, FD-2 ... in the power supply's section, standing in a column 10 right of the
    supply, 20 apart.
  - The first fuse is level with the supply's + (24P1), so one straight wire feeds it. Their
    line sides are bridged.
  - The supply's - drops in a lane between the supply and the fuses, to below them.
  - The fuse block's line and load markers are named in config: `CONN_A_LINE` /
    `CONN_A_LOAD`. Until 1P_FUSE_1 has them, the fuses are boxes, and Generate says so.
  - The rating is left at the block's default for the engineer (no current list yet).
- **Circuits:** a fuse's + and all it feeds, plus the shared -. Each circuit reaches the
  sections from the supply's to its farthest load, one shipping split pin per boundary. The
  pin order is the fuses' circuits, then the -, then any fuse phases.
- **Terminal blocks:**
  - A circuit is split on a terminal block in a section where it meets three or more points:
    what it comes in on, its loads there, and the splits it goes on through. With two points
    it's one wire.
  - One wire per terminal point, on the side points only: wires from the left on the points
    facing left, the rest on the points facing right. In a strip, TOP and BOTTOM face the
    next terminal. Which side each point faces is read from its markers' names.
  - A circuit's terminals stack 5 apart, with a bridge from the top one's `BRIDGE_TOP` to the
    bottom one's `BRIDGE_BOTTOM`.
  - Terminals are numbered within the strip (`#`), and each group has the strip's name above
    it as plain text, "1TB24+" / "1TB24-".
- **Page layout, left to right:**
  1. The incoming split's male at the page's left edge. In the supply's section it sits
     below the supply and its fuses.
  2. The supply and its fuses.
  3. The terminal blocks in one column, each group level with the wire it comes in on unless
     that would cover a wire passing by.
  4. The loads, stacked below the wires going to the outgoing split, each + level with its
     feed where it can be.
  5. The outgoing split's male at the page's right edge, lined up first with a fuse's phase,
     then with a 24 V wire passing straight through, then with anything else.
  - Wires that can't run straight turn in a lane of their own, 5 apart, in the gap before the
    terminal blocks or before the loads. No junction dots (2.3.0's rails are gone).
- **Wire numbers:** every wire its own (2+001 ..., 2-001 ...), counted through the job, starting
  with the supply's + to the fuses. A wire keeps its number through the shipping splits it
  passes. On the SHIPPING SPLITS page, each cable carries the number of the wire through it.
- Spacing and sizes are in `device_pages` (layout_settings.json). Blocks, names and the
  bridge are in `control_power` (devices.json).
**Reason:** Sammy, 2026-11-13 and 2026-11-16.
**Status:** Approved. Built 2026-11-16 for 2.3.1.
- Waiting on blocks: 1P_FUSE_1's connection markers, plus the COM190, Ethernet switch, new
  UMG 801 and trip unit (ETU pins) blocks.
- Noticed: the fixed fuses' rating tags differ (1P CURRENT, 2P RATING, 3P RAITING). The
  library was open with unsaved changes on 2026-11-16, so the catalog has the last saved
  version.

### 2026-11-13 — 24 V distribution through terminal blocks; blocks are never final
**Decision (Sammy's rules):**
- **+ side:** one 24 V fuse per device (2026-11-10). A fuse feeding one termination point is a
  single + wire from the fuse to it. When one fuse feeds several termination points, the wire
  is split on a terminal block.
- **- side (shared):** in the power supply's section, one big terminal block splits the -.
  One - wire goes through each shipping split to the next section. There it lands on a
  terminal block, which sends one wire on to the next shipping split, plus every - wire that
  section needs.
- **Block:** `Terminal_Block`, added to the library 2026-11-12. Read 2026-11-13:
  - 4 points, 12.5 x 5. Each point takes a wire from one of 3 directions, and each direction
    has its own marker. Points 1 and 2 open to the left (LEFT / TOP / BOTTOM); points 3 and 4
    open to the right (RIGHT / TOP / BOTTOM).
  - One attribute, `#`, in the middle. It has no flip and no visibility states.
  - Slip found: two markers used a hyphen (`2-LEFT`, `2-BOTTOM`). Sammy fixed them the same
    day; re-read: all 12 are `<point>_<SIDE>`, so the program reads points and directions
    from the names.
- **Sammy's answers (same day):**
  - **The fuses are always next to the power supply.** So each device in another section
    takes its own shipping split pin for its +; only the - is shared (one pin per boundary).
  - **More than one terminal block (a strip):** the block is designed so the next one goes
    5 units below the one before. A polyline 0.1 units wide joins them all (the bridge).
    Sammy leans towards a layer of its own for it rather than layer 0.
  - **The strip's name is plain text,** not an attribute. Where it goes depends on how the
    wires connect to the strip, so it won't always be in the same place.
  - **Naming follows the legend for now** (it will probably change; an easy change): strips
    "1TB24+" / "1TB24-" (section, TB, voltage, polarity), terminals numbered inside the
    strip, and a wire end "2TB24+(1-4)" (terminal, then point).
  - **Device blocks (Sammy will follow this for 24 V):** + and - both on the block's left
    edge. A pin that takes more than one wire (daisy-chaining) gets a separate marker for
    each connection.
- **Blocks are never final** (Sammy, 2026-11-13). Any block can change at any time, to adjust
  the look or flow of a drawing or to make the program's rules simpler. How the terminal
  blocks are used and how the 24 V is laid out through each section will shape the device
  blocks Sammy is making (COM190, Ethernet switch, UMG 801).
**Reason:** Sammy, 2026-11-13. He brought it up now, before the device blocks are designed.
- **Sammy's answers (second round, same day):**
  - **The bridge:** Sammy added `BRIDGE_TOP` (-1, 2.5) and `BRIDGE_BOTTOM` (-1, -2) to
    Terminal_Block. The bridge is a polyline 0.5 wide that the program draws (a layer can't
    make it a polyline). As in Sammy's example (120V_POWER-SCH_EXAMPLE), it is one line from
    the top block's `BRIDGE_TOP` to the bottom block's `BRIDGE_BOTTOM`. It goes on its own
    layer, `BRIDGE`. On 2026-11-13 that layer was only in Sammy's HYPER_A_copy.dwg, not yet
    in the shared HYPER_A.dwt; until it is, the program creates the layer itself. Sammy
    added it to the shared HYPER_A.dwt on 2026-11-20 and the program's copy was refreshed.
  - **The strip's name** goes as plain text on the TEXT layer, on the first side of the
    strip with no wires: above, then below, then left, then right (order in config).
  - **Several connections on one device pin** are named by number, not side: `24V+_1`,
    `24V+_2`, `24V-_1` ... The second may sit on the right edge; the program works out the
    side from where the marker is, so the name only says which pin it belongs to.
  - **Build it now as 2.3.1.** The UI release (2.4.0) comes once Sammy is happy with the
    drawing logic. The goal: make the drawing work first, then make the tool fast and easy
    for everyone.
**Status:** Rules and answers recorded. The 2.3.1 plan was approved on 2026-11-16 and built
(see that entry).

### 2026-11-12 — 24 V to the power meters waits for the new meter block
**Decision:** The power meters need 24 V on their + and - supply inputs (24V+ / 24V- on the
UMG 801), but this is left out for now.
- **Plan (option A):** each meter, with its fuse, CT inputs and remote display, joins its
  section's 24 V group and is fed along the bottom from the rails. Meters then count as
  24 V loads when working out the shipping splits.
- **Power by model:** which terminals and which voltage go in config per model. The
  Schneider PM8000 takes 120 V and comes with the 120 V work.
- **Blocks still to come** (each replaces a placeholder): COM190, Ethernet switch, the new
  UMG 801.
**Reason:** Sammy, 2026-11-12: the UMG 801 block isn't final; its wires will come out
horizontally.
**Status:** Deferred until the new meter block. Possibly an update to 2.3.0 after it ships.
*(Built 2026-11-17 with the UMG 801 Rev2: see that entry.)*

### 2026-11-11 — One 24 V power supply; 24 V moves between sections through shipping splits
**Decision (Sammy's rules):**
- A lineup has only one 24 V power supply. Its 24 V reaches the other sections through
  shipping splits.
- **Blocks:** Female_Shipping_Split and Male_Shipping_Split, 10 connections each.
  - Sammy fixed the male's name and its CONN_7 the same day.
  - Read 2026-11-11: CONN_1-CONN_10, 5 apart. The female's are on its left; the male's
    are on its right. Both can flip. Attribute SS_DWG_NUM (default "#SSF-##" / "#SSM-##").
- **Names** start with the section number, then SSF or SSM, then the split's number within
  the section. The 3rd shipping split in section 5 is 5SSM-3. They keep the section number,
  as terminal blocks do (2026-11-10 naming).
**Reason:** Sammy, 2026-11-11.
**Status:** Approved. Built 2026-11-11.
- **Where splits go (Sammy's answers, same day):** every boundary between two sections that
  wires cross. How many depends on how many wires cross (10 per split); wires take the next
  free pin, so + is pin 1 and - is pin 2 for now.
- **Males:** on the ends of each section's device page, showing what connects to them.
- **Females:** the two of each split (the cable between the sections) go on a new page at the
  very end, "SHIPPING SPLITS", showing the wires and their labels.
- **Numbering:** within the section, males and females counted separately, left boundary
  first, then the right.
- **As built:**
  - 24 V crosses a boundary when the supply is on one side and a box it feeds is on the
    other. A section in between only passes it on.
  - In each section, the 24 V group comes first on its page. On the left: the supply (in its
    own section), then the left boundary's male, facing right. On the right: the boxes, then
    the right boundary's male, flipped to face left. A + rail and a - rail join them all.
  - *(Sammy, same day: the males sit at the page's ends.)* The left boundary's male is flush
    with the page's left margin. The right boundary's male is flush with its right margin,
    below the boxes, with the 24 V wires running across to it. If that would reach the title
    block, it stays beside the boxes.
  - On the last page, each split's two females are side by side, the left section's flipped,
    `shipping_split_cable` apart, with a labelled wire per pin used.
  - Blocks and names are in `shipping_split` in config/devices.json.
  - With more than one supply, only the first is wired, and Generate says so.
  - *(Sammy, same day: rare, but kept.)* A fuse feeding a meter or power supply in another
    section sends its three phases through the splits at every boundary in between. They
    take the next pins after the 24 V. On the SHIPPING SPLITS page the phases are in the
    cable, labelled.
  - **Routing (Sammy, same day): avoid jumps unless they make a page less busy.**
    - The fuse lies down in its section's split group and its load side runs straight into
      the outgoing male. No TO bracket.
    - Wires passing through a section run straight across the page from male to male. The
      outgoing male lines up with the first passing wire or fuse wire it carries (the 24 V
      if nothing else), and the boxes drop below those wires.
    - The rails start clear of whatever is in the left column.
    - The receiving meter or power supply keeps its FROM bracket for now (the meter block is
      changing), with a short labelled stub on the male's pin (`split_stub_length`).
  - **Wire labels (confirmed by Sammy):** a wire keeps one label on both sides of a jump, since
    it's the same wire.
  - More connections will come later, some from other pages of the same section. Each
    boundary already takes as many splits as its wires need, 10 pins each.
  - Seen in Sammy's Hybrid_ES-013631 (not in docs/SWBD_reference/ yet), 2026-11-11:
    - three splits' worth of wires between two sections;
    - the section pages end each wire in a tag "1SSM-2 (4)" (split, then pin);
    - the splits page lists each male pin with where its wire comes from ("ATC-1 (22)"),
      its label, and what it is ("FA-4 / PHASE-A", "52-MSB-H01-M (X6.9)"), beside the
      mated females 1SSF-n / 2SSF-n;
    - pins 1-3 there carry a fuse's phases.
    A possible later step, not built.
  - Terminal blocks will be needed on the hybrid pages; what they look like is not decided.

### 2026-11-11 — First 24 V wiring: power supply to the comms modules and Ethernet switch
**Decision:** In a section with a power supply, the supply feeds that section's Ethernet switch
and comms module boxes. If the section has more than one supply, the first one feeds them.
- **Wires:** a + wire and a - wire from its 24 V outputs (24P1 / 24N1 on 3P_PWR_SUP, set in
  config/devices.json), ending just inside each box. They go on layers WIRE - 24+_RED and
  WIRE - 24-_BLK, labelled 2+00n / 2-00n (n = the supply's number; a placeholder like the
  other wire labels).
- **Layout:** the boxes stack down to the supply's right with their left edges lined up.
  - The first box is level with the outputs, so its wires run straight across.
  - The others branch off a + rail and a - rail, with a junction dot (BUS_NODE) at each tee.
  - Spacing is set in `device_pages` (`feed_*`).
- **Sections without a supply:** their boxes stay unwired, after the section's other devices.
**Reason:** Sammy, 2026-11-11: "send a positive and a negative wire to right inside the box for
now", to show some wire routing in this release.
**Status:** Approved. Built 2026-11-11. The full 24 V chain (fusing per device, the ETUs) is
still group B. *(Same day: a lineup has only one 24 V supply, so sections without it will get
their 24 V through shipping splits: see the entry above.)*

### 2026-11-11 — Boxes for the Ethernet switch and comms modules until their blocks exist
**Decision:**
- Until their blocks exist, the device pages draw a box in place of:
  - the Ethernet switch, in the section ticked for it, labelled "ETHERNET SWITCH";
  - each breaker's comms module, in its breaker's section, labelled with the breaker and the
    module ("52-M1 Siemens COM190").
- The boxes come after the section's other devices, so the devices already drawn don't move.
- They go on the non-printing placeholder layer, like the meter boxes, and have no wires yet.
- A section with only comms modules now gets its own device page.
- Generate notes once that these are boxes.
- Box sizes and the switch's text are in `device_pages` in config/layout_settings.json.
**Reason:** Sammy, 2026-11-11: "place temporary boxes in their place for now."
**Status:** Approved. Built 2026-11-11. Sizes are placeholders.

### 2026-11-11 — The title block's page total counts every page
**Decision:** The title block's "OF nn" (field on the drawing property TOTAL PAGES ES) is the
drawing's whole page count: the kept template pages (TOC, legend, BOM) plus the ES pages.
Six pages read 01 OF 06 … 06 OF 06. It was the ES pages only (03).
**Reason:** Sammy, 2026-11-11: the page numbers changed but the total didn't. It must agree
with the page numbers written into the frames.
**Status:** Approved. Built 2026-11-11.

### 2026-11-10 — Page numbers written by Generate; the resources folder's purpose
**Decision:**
- Generate writes each page's number into its frame's `PAGE` attribute. It uses the rule of
  the engineers' NumberByLayout.lsp: 01, 02, 03... in tab order. That is the kept template
  pages first (TOC 01, legend 02, BOM 03), then ES_01 = 04 and so on.
- These are the same numbers the SHEET references use. The LISP gives the same result if an
  engineer runs it afterwards.
- The frame each kept layout shows is in config (`keep_layout_frames`). A frame without a
  `PAGE` attribute is reported, and that page keeps the template's number.
- `docs/AI_resources/` holds the team's existing tools. Their logic is taken and built into
  the configurator, so it becomes one tool that integrates all of them. CLAUDE.md and
  AI_RESOURCES_INDEX.md say so.
**Reason:** Sammy, 2026-11-10 ("Do the page numbers with your option 1"). Option 2 (run the
LISP from the program) would depend on where the file lives and leave its "renumber on
save" reactor on. Option 3 (leave it to the engineers) would ship drawings with wrong
numbers.
**Status:** Approved. Built 2026-11-10.

### 2026-11-10 — Wire labels on layer 0; smaller tildes
**Decision:** Wire labels go on layer 0 (was TEXT): `wire_labels.layer` in
config/layout_settings.json. Sammy made TILDE_R0 and 3P_TIDE_R0 smaller in the block library
to match the other tildes in the drawing. The catalog was refreshed the same day: only their
outlines changed, and their connection points stayed the same.
**Reason:** Sammy, 2026-11-10.
**Status:** Approved. Built 2026-11-10.

### 2026-11-10 — Team meeting: page numbers, naming, 120 V and 24 V control power
**Decision:** From Sammy's team meeting (2026-11-10):
- **Build resources folder:** `docs/AI_resources/` holds files Sammy puts there to help
  build the program (LISP routines, spreadsheets). Claude only reads them, never edits them;
  Claude's notes go in `docs/AI_RESOURCES_INDEX.md`. Rule in CLAUDE.md.
- **Page numbers:** an engineer's LISP fills in the template's page number fields. Sammy
  puts it in the resources folder; Claude takes its logic or suggests something different.
  (The template's frames carry a fixed `PAGE` attribute: TOC_01 = 01, LEG_01 = 02,
  ES_01 = 08 ...)
- **The table of contents is page 1,** then the pages as before: TOC_ES, LEG_ES, BOM_ES,
  ES_01 ... (`keep_layouts` in config/autocad_settings.json). Built 2026-11-10.
- **Device names:** names and abbreviations stay the same (PM, FA, PS, MMS, RD, ...), but
  **the section number is no longer in the name**, because the devices are already shown
  by section: FA-3-12 becomes FA-12. **Exceptions: terminal blocks and shipping splits keep
  the section number** in their name. Replaces the naming in "Device names hold their
  section" (2026-10-23) and PS-s-n / MMS-s-n (2026-11-05, 2026-11-09).
- **Wire labels: to discuss** (on the docket). The labels built in group A (2026-11-09,
  legend prefixes, tap n = 2n-1 / 2n) are a placeholder until then. The team's wire label
  LISP will probably change and may not help the program.
- **120 V control power:** the engineer picks how many sources (1, 2, 3 or 4) and which:
  **Utility, Generator, Critical Bus (sometimes shown as UPS), Customer Source.** From that
  the program draws the whole circuit. Sources are ranked by priority, highest first:
  **Customer, Critical, Generator, Utility**, and go into the 120 V control power circuit
  in that order. Sammy makes the block (1, 2, 3 and 4 source versions); the program adds
  fuses or tildes to it as needed. **Each source has a checkbox for availability indicator
  lights.** Two spreadsheets (to the resources folder) size the overcurrent protection,
  the power supply and the transformer; the program will use their rules.
- **24 V control power distribution:** in general **each device gets its own fuse.** Each
  device in config/devices.json gets its current draw (A); the fuse is that x 1.25, rounded
  up to the next available fuse. **Available fuses: 1 to 6 A.** Exception: **trip units and
  lights can all share one fuse.** More exceptions may be added (so exceptions live in
  config). Replaces "How much goes on one fuse: the engineer's choice" (2026-11-09).
- **Conflicts found while recording this; Sammy's answers (2026-11-10):**
  1. **SHEET references are the drawing's overall sheet number,** not the ES page number:
     TOC 1, legend 2, BOM 3 (counted, though empty for now), so ES_01 is sheet 4, ES_02
     sheet 5, and so on (as in the hybrid, "FROM SHEET 3" for its 3-line). Built:
     `sheets_before_pages` (3) in layout_settings.json `device_pages`, matching
     `keep_layouts`; Generate warns if the two disagree. **Labels name sheets too**
     (Sammy, 2026-11-10): "FROM ES_01" / "TO ES_02" became "FROM SHEET 4" / "TO SHEET 5"
     (`page_reference` "SHEET {sheet}" in `bus_break`). Later: the program writes the
     hybrid's fuller labels itself ("FROM SHEET 3 LINE SIDE 52-MAIN", "TO 52-F1 TRIP
     UNIT"...), so the engineer doesn't have to (proposal in INDEX.md, NTT-013628).
  2. **TOC vs revision history:** use what is in the template (TOC_ES). Changes to it are
     made in the template.
  3. **No section in any device name built so far:** shorting kits are STB-k (not the kind of
     terminal block meant above) and CTs go back to plain numbers (set k: 3k-2, 3k-1, 3k).
     Built: PM-n, RD-n, FA-n, PS-n, MMS-n, STB-k, CTs 1-2-3 ...
  4. **120 V is the engineer's choice** in the configurator. With an ATC there is generally
     switching and so 120 V control power (that matters for how the drawing is laid out),
     but 120 V doesn't need an ATC: e.g. the Schneider power meter takes 120 V.
     *Replaces "an ATC brings 120 V" (2026-11-09) as the trigger.*
  5. **120 V sources, as the engineer picks them:** the program can't tell which section is
     the generator or the utility, so the choices are: **line-side taps** (the engineer
     picks which), **Critical Bus** (with taps the engineer must pick), and **Customer
     Source**. (Priority order from above: Customer, Critical, Generator, Utility.)
  6. **Trip units and lights share a fuse, and when that total x 1.25 is over the largest
     fuse (6 A), they are split onto more fuses.** Sammy is getting a list of every device.
     **Docket: workshop how devices and their current draw are kept** (config, or maybe
     Arena).
  7. **"Lights" are the availability indicator lights,** not the MMS (the MMS is a switch and a
     light in one): per source, a contact relay and an LED that lights when that source is
     available.
  8. **The COM190 is powered through a Siemens-supplied cable from the ETU:** no fuse, no
     24 V wire of its own.
  9. **With 120 V present, the 24 V supply is the 2-pole** off the 120 V circuit (as far as
     Sammy knows).
**Reason:** Sammy's team meeting, 2026-11-10, and his answers the same day.
**Status:** Approved. Built 2026-11-10: TOC first, device names without the section, SHEET =
overall sheet number, page numbers by Generate (entry above); wire labels to discuss; 120 V waits
for Sammy's block and the spreadsheets; 24 V fusing waits for the device list

### 2026-11-09 — Breakers, their ETUs, and control power (general rules)
**Decision:** Background and rules from Sammy that apply throughout:
- **Designations follow the legend** of the hybrid NTT-013628 (sheet 02) for now: terminal
  block "2TB24+(1-4)", shipping split "SS1-2M-2(4)", wire "120N-J3". Can be tweaked later.
- **3WA (Siemens "air breaker"):** very large; generally the input breakers (mains), the
  kind found alone in a section or as a top-fed and a bottom-fed single breaker in one
  section. Its **ETU** (electronic trip unit) is built in. Its control pins come on
  block-like connectors that slot into the top of the breaker, labelled X<connector>.<pin>,
  e.g. X8.4. These pins are the ETU's; the drawings name the ETU the same as its breaker.
  **Every ETU pin is doubled**, so daisy-chaining through a pin is fine.
  - **Every 3WA needs 24 V control power** for its ETU, so the program adds the control
    power for every 3WA by itself; the engineer only decides where its taps go.
  - **A DAS/MMS always comes with a 3WA:** added automatically for now. The DAS takes its
    24 V from the ETU.
  - **COM190:** the 3WA's communication module, connected to the ETU over the CubicleBUS
    (Modbus), and from it to the Ethernet switch. The drawings don't show this well yet.
- *(2026-11-10: 120 V control power is now its own choice by the engineer, picked from
  line-side taps, Critical Bus taps and Customer Source; an ATC generally means 120 V, but
  120 V doesn't need an ATC. The COM190 is powered by a Siemens cable from the ETU.)*
- **ATC:** whether there is one is the engineer's choice. With an ATC, the two breakers it
  controls need **120 V** control power to their ETUs. Needing 120 V means: a 3-phase tap to
  a transformer (CPT) for each source, logic choosing which source is used, and then 120 V
  stepped down to 24 V (the 2-pole power supply) instead of 24 V straight from the taps.
- **3VA:** smaller, with less going on; usually the group-mounted distribution breakers.
  With comms: one COM060 per breaker, and a COM800 connecting to each of them (as in the
  references, DECISIONS 2026-10-19 item 8).
- **Ethernet switch:** there is one if there is any COM190, COM800 or power meter. The
  engineer chooses the section it lives in. Cable lengths: left out for now.
- **How much goes on one fuse:** the engineer's choice; no rule yet. *Replaced 2026-11-10:
  each device its own fuse, sized from its current draw; trip units and lights share one.*
- **Wires per terminal:** the hybrid style shows every wire, so the number of wires on each
  terminal (terminal blocks, device pins) must be tracked and shown. Daisy-chaining through
  doubled pins (3WA ETU) helps keep it down; this is to be known for each device.
- **Coming from Sammy:** a better power meter block, and a new breaker ETU pins block more in
  line with the wiring diagram.
- **How the program does it (Sammy, 2026-11-09):**
  - **Breaker family by position:** main, single and tie breakers are 3WA; group-mounted
    breakers are 3VA. No new field; change later if it becomes a problem.
  - **COM190 stays the engineer's choice** on each 3WA.
  - **One 24 V power supply per switchboard,** in the section the engineer picks, fed from
    the tap the engineer picks.
  - **The ATC does not always control interlocked mains,** and mains are not always
    interlocked: what the ATC controls is a question for Sammy's team (the standard).
  - Build order: (A) one device page per section, wire labels by the legend, breaker
    family + automatic MMS/DAS, the Ethernet switch's section; (B) the automatic 24 V chain
    when the ETU pins block arrives; (C) ATC and 120 V.
- **Group A as built (2026-11-09, for Sammy's review):**
  - **One device page per section,** titled "ELECTRICAL SCHEMATIC SECTION n"; its devices
    left to right in rows from the top left (power supplies first), carrying on on another
    page if full. A section with no devices gets no page. The "SECTION n" headings are gone.
  - **Page titles** on every page the program draws, as in the hybrid: "THREE-LINE DIAGRAM
    01" on the 3-line pages too; MText height 3 at the bottom right (right end 327.84 from
    the frame's left, middle 5.03 up), bold Century Gothic, spaced, underlined
    (`page_title` in layout_settings.json).
  - **Wire labels** on every wire the program draws on the device pages, by the legend's
    prefixes (`wire_labels` in layout_settings.json): tap n's wires from the 3-line are
    2n-1, from its fuse onward 2n (one tap: 4A001 / 4A002, as in the hybrid); MText 1.25 on
    layer TEXT, centred 1.05 above the wire's longest across piece, or turned 90 degrees
    1.05 to the left of an upright wire. The 3-line tap's own wires are inside its block:
    labelled there once `3P_Voltage_Tap` has wire label attributes.
  - **Breaker family by position;** comms by family (config/devices.json): 3WA offers
    COM190, 3VA COM060 (projects that had COM800 on a group-mounted breaker open with
    COM060). **Every 3WA has a DAS/MMS,** MMS-s-n (named by section like every device),
    shown in its editor as "added automatically"; not drawn until its block exists.
  - **Ethernet switch:** "Ethernet switch in this section" in the Devices box, shown when
    there are comms modules or power meters; one section only; warning until ticked.
**Reason:** Sammy, 2026-11-09, answering the hybrid NTT-013628 study questions.
**Status:** Approved; group A built 2026-11-09, for Sammy's review

### 2026-11-05 — Device pages: drop the column-per-section layout
**Decision:** The device pages will no longer be laid out as one column per section (the
2026-10-23 layout). The devices will mostly be wired together, so they are to be placed in
whatever way suits the wiring. The rule for that is not settled yet; a proposal from the
references is in INDEX.md ("Device page layout", pending approval). Until the new rule is
built, the current layout stays (power supplies first in each section).
**Reason:** Sammy, 2026-11-05: the column scheme will be restricting as more devices are
connected (power supply, meters, COM190). Behind it: Hyper is combining the schematic and
the wiring diagram into one hybrid drawing (the wiring diagram takes too long on its own).
The schematic therefore shows much more detail: terminal blocks that split wires, how fuses
connect (or don't), and every connection to the shipping splits. Devices stay on pages by
section. The first hybrid drawing is Sammy's recreated NTT-013628 (to be added to the
references); the older references are all schematic-only.
**Status:** Approved (direction); rule to agree, from the hybrid NTT-013628

### 2026-11-05 — Power supplies: 2-pole and 3-pole (direction)
**Decision:** Two library blocks: `3P_PWR_SUP` (fed from the 480 V voltage taps, 480 V to
24 V) and `2P_PWR_SUP` (used when there is already 120 V in the circuit, 120 V to 24 V).
Every connection on both is marked and every attribute has a prompt. Where this is going:
the engineer says what control power is needed (120 V and/or 24 V) and the program adds the
matching power supply and taps. Step by step (Sammy approved the recommendations,
2026-11-05):
1. **Added by hand for now:** "+ Power supply" in a section's Devices box, beside the power
   meters; named PS-s-n like the other devices.
2. **Fed by its own voltage tap:** a tap feeds a power meter or a power supply; its fuse
   (FA) is drawn above it on the device pages, as for a meter. Taps off taps (a meter and a
   power supply sharing one tap, PRIME-014034) right after.
3. **3-pole only for now:** the 2-pole waits for a 120 V source (CPTs).
4. **Step 1 draws the power supply and its 480 V feed only.** The 24 V side (FD fuses and
   their loads) comes with the communications page.
5. **Wire routing** design talk when the 24 V side is built.
- **Fuses get their own set of rules later** (Sammy): fuse disconnects and fuse blocks are
  different devices and look different, and the schematic style is changing. Until then
  taps use the fuse they use today (`3P_2P_FUSE_DISCONECT`).
- **On the device pages (Sammy chose option A, 2026-11-05):** the fuse lies down (its
  "3-POLE HORIZONTAL" state) to the left of the power supply, its load side level with
  `L1`-`L3`, so the three wires run straight across; its box ends `wire_spacing` before the
  supply's. Its line side: stubs left, a `TILDE_R0` in its HORIZONTAL state on each end, and
  the bracket (horizontal-bus state, mirrored) "FROM ES_0n". A power supply whose tap is in
  another section gets the same on its inputs, "FROM FA-s-n SHEET n"; its fuse is drawn on
  its own, "TO PS-s-n SHEET n". Fuse states and markers in config/devices.json
  (`horizontal_*`); labels in layout_settings.json (`from_fuse_label`). Built 2026-11-05, for
  Sammy's review in AutoCAD.
- **After Sammy's first look (2026-11-05):** the lying tildes are mirrored to face the
  wires (`Flip state1` only, `wire_break_flip_horizontal`); every text attribute on a tilde
  is set blank (not only `TEXT_H`); in each section the power supplies come first (top left),
  then the meters, then fuses on their own: the power supply powers what comes after it
  (meters, the COM190 next). `TILDE_R0`'s HORIZONTAL state also shows a plain MText "X"
  (not an attribute), which the program can't change: Sammy to make it an attribute or
  remove it in the block.
- Block audit (2026-11-05): both blocks have named markers (`L1`-`L3` / `L1`+`N` in,
  `24P1`/`24N1`/`24P2`/`24N2` out, `G`, and `NO13`/`NO14` on the 3-pole) and prompts. The
  number tag differs: `PS_DRW_NUM` (3-pole) vs `PS_DWG_NUM` (2-pole).
**Reason:** Sammy, 2026-11-05. Matches the references: NTC-013632, NTT-013627 and
PRIME-014034 have "PS-1 480VAC/24VDC" off a fused 480 V tap; Sabey-011486 has
"PS-1 120VAC-24VDC".
**Status:** Approved (direction); blocks to audit once the library is saved

### 2026-10-26 — GROUND layer only for the main ground bus
**Decision:** For what the program draws itself, the `GROUND` layer is for the main ground
bus only (the ground bus line and its symbol); ground wires the program draws anywhere else
go on the wire layer (`WIRE_GROUND` in HYPER_A). Layers inside a block are the block's
business (BLOCK_LIBRARY_STANDARD rule 9): e.g. Janitza_UMG801's ground terminal on GROUND is
fine. Sammy added `DEVIDER` and `GROUND` to the team template (HYPER_A) after purging layers.
**Reason:** Sammy, 2026-10-26, with the template layer audit. The program draws no ground
wires yet; the rule is for later.
**Status:** Approved

### 2026-10-26 — Interlocks are chosen by the engineer; plan to the next major release
**Decision:**
- **Interlocks (corrects 2026-10-19 item 10):** not every pair of mains is interlocked. The
  engineer chooses which main breakers are interlocked and whether the interlock is
  **mechanical, electrical, or both**. What "always drawn" meant: when there is an interlock,
  the line is always on the drawing. For now an interlock is only between **main breakers in
  sections next to each other**; if the engineer picks mains that aren't next door, a warning
  says so. How it is entered and drawn (Sammy approved 2026-10-26):
  - **Entered on the main breaker:** an "Interlock" box in the main breaker's editor:
    "Interlocked with" (the other mains, by label and section) and Mechanical / Electrical
    checkboxes. Each main gets a hidden id (as feeds have); the interlock is saved once, on
    one of the two mains, and both mains' editors show it.
  - **Drawn as in Sabey-011486 / NTT-013631:** a dashed line at the breakers' mid-height,
    on its own layer `INTERLOCK` (Sammy changed this 2026-10-26: he added the layer to
    HYPER_A, red, HIDDEN2; the references used the divider layer), from just past the left main's C pole (running through its label
    text, as the references do) to just short of the right main's A pole.
  - **Mains at different heights:** the line steps (across, up or down, across) between the
    two sections, clear of the divider. Mains on opposite sides of the main bus: warning,
    no line.
  - **Same page:** interlocked sections are kept on one page (as if "link with next" were
    ticked).
  - **Text:** "MECHANICAL INTERLOCK", "ELECTRICAL INTERLOCK" or "MECHANICAL AND ELECTRICAL
    INTERLOCK" by the checkboxes; height 1.25, layer 0, centred on the line with a background
    mask. Wording, layer and gaps in config.
  - **As built (2026-10-26, for review):** line from 2.5 past the left main's C terminal to 1
    short of the right main's A terminal (`interlocks` in config/layout_settings.json); the
    step sits halfway between the divider and the right section's contents (the empty strip
    beside the divider); the text is centred on the line between the left main's block and
    the end of the first run. One interlock per main for now: the "Interlocked with" list
    leaves out mains already interlocked with another. Changing a main into anything else
    removes its interlock. Code: `src/model/interlocks.py`, `src/layout/interlocks.py`.
- **Mouse wheel:** a closed drop-down in the editor ignores the mouse wheel, so scrolling the
  editor never changes a setting. An open (clicked) list still scrolls with the wheel
  (`src/ui/widgets.py`, `ScrollSafeComboBox`).
- **Page-numbering bug** (known issue since 2.1.0) waits: it needs a talk with the leads about
  the template.
- **Device pages** will likely become one section per page as more devices are added. Keep
  adding one thing at a time and keep checking how the drawing works.
- **Order of work:** (1) clean-up release 2.2.1: interlock line + mouse wheel; (2) power
  supply, then communications; (3) next major release: re-assess the user interface (it is
  getting cluttered as drawing logic is added).
**Reason:** Sammy, 2026-10-26.
**Status:** Approved; built and checked by Sammy in AutoCAD; released in 2.2.1 (2026-10-26)

### 2026-10-23 — Voltage taps on either side of a main breaker
**Decision:**
- Each voltage tap on a main breaker is on its **line side** (between the termination and
  the breaker, as before) or its **load side** (between the breaker and the main bus). The
  engineer picks "Side of the main breaker" for each tap in the main's tap list.
- Load-side taps are saved on the main breaker (`load_side_taps`), not on its feed, so a main
  fed from another section still has them. A tap moved to the other side goes to the end of
  that side's list. Line side is only offered when the main's feed is in its own riser.
- Placement on the load side: nearest the breaker, the taps (each `clearance` from the
  breaker's text and from the next tap, in the order entered), then the CTs (if any), then
  the main bus. The riser grows to fit them; one function (`bus_side_gap`) sizes the section
  and places the blocks, so the preview and the drawing agree.
- Numbering: in each part, the feed's (line-side) taps first, then the load-side taps
  (FA-s-n through the lineup, as before).
- Not drawn yet on a breaker fed on the bus side (its riser is a U-turn); a warning says so,
  as for CTs.
- Editor: the voltage tap list moved out of the "Incoming feed" box to just below it, so it
  still shows for a main whose feed is in another section.
**Reason:** Sammy, 2026-10-23.
**Status:** Built 2026-10-23, for Sammy's review

### 2026-10-23 — Remote display on a power meter; CT sheet filled by the program
**Decision:**
- **Remote display:** a "Remote display" checkbox on each power meter. Drawn on the device page
  to the left of its meter (`Remote_Distplay` block), joined meter USB marker to display USB
  marker by a line on layer 0 (as in PRIME-014034): left `remote_display_gap`, then up
  `remote_display_rise`. Named RD-s-n (s = the meter's section, n through the lineup); the
  program fills RD_DWG_NUM. Block, markers and layers in config/devices.json.
- **CT block SHEET#** (the meter's sheet) is filled by the program and no longer offered in the
  editor.
- **Taps off taps** (load side on the device pages, line side on the 3-line) and the mouse wheel
  not changing drop-downs: on the docket (README 3h, 3j).
**Reason:** Sammy, 2026-10-23.
**Status:** Approved; remote display and CT sheet built

### 2026-10-23 — Single breakers can be fixed or draw-out
**Decision:** a single breaker has a Mounting choice (fixed / draw-out), using the same blocks as
main breakers (`main_breaker.blocks`). Saved with the project; older files open as fixed.
**Reason:** Sammy, 2026-10-23 (found rebuilding a test drawing: single breakers were always fixed).
**Status:** Approved; built

### 2026-10-23 — The library's blocks win over the template's; tildes on fuse wires
**Decision:**
- **Block source:** for every block the program inserts, drawings get the **symbol library's**
  version. A block of the same name that came with the HYPER_A template is renamed
  "<name>_TEMPLATE" first, so what the template drew with it (e.g. the legend) keeps its look.
  Found because HYPER_A carries an old TILDE_R0 (fixed "X" text, no attribute).
- **Tildes on fuse wires:** every wire end that goes to or comes from a fuse through a TO / FROM
  bracket on the device pages gets a TILDE_R0 (one per wire, CONN on the wire end, VERTICAL
  state, its TEXT_H set empty). Wires inside a section (fuse to its meter) have none.
**Reason:** Sammy, 2026-10-23.
**Status:** Approved; built

### 2026-10-23 — Device names hold their section; device pages: wires inside a section
*Naming replaced 2026-11-10: the section number is dropped from device names (FA-3-12 becomes
FA-12), except for terminal blocks and shipping splits.*
**Decision:**
- **Naming (every device):** the name holds the section the device lives in: fuse 12 in
  section 3 is **FA-3-12**. The number counts through the whole lineup. The block holds the
  prefix ("FA-", "PM-", "STB-", "CT"); the program fills the rest ("3-12"). Applies to fuses
  (FA), power meters (PM), shorting kits (STB) and the CTs themselves (set 1 in section 2:
  CTs 2-1, 2-2, 2-3, STB-2-1).
- **Where devices live:** a meter in the section it's mounted in; CTs and their shorting kit
  where the CTs are drawn; a voltage tap's fuse in the **tap's** section.
- **Device pages, connections:** devices in the same section are joined by **lines drawn by the
  program** (no block), on the layers of the wires they carry (voltage: WIRE - 480A-BRN /
  480B-ORG / 480C-YEL; current: CT+ white / CT- black). Only where a connection leaves the
  section does it get TO/FROM (and always for a tap or shorting block shown on the 3-line).
  E.g. a fuse and its meter in the same section are wired (no voltage input block); in
  different sections the fuse's load side says "TO PM-..." and the meter's voltage input block
  says "FROM FA-... SHEET #".
- **Fuse block:** `3P_2P_FUSE_DISCONECT` (CONN_A/B/C_LINE/LOAD_H/V markers, 3- and 2-pole
  states). The engineer fills its rating (CURRENT); the program fills the number
  (FUSE_DWG_NUM).
- **Fuse line side** (from the tap on the 3-line): wire stubs on the 480A/B/C layers ending in
  BRACKET_TEXT_R0 "FROM ES_0n".
- **Page layout:** grouped by section ("SECTION n" heading), as many as fit; Sammy approves on
  seeing it.
- **As built (2026-10-23, for review):** device pages follow the 3-line pages (ES_nn). Each
  meter is a "unit" with its CT inputs under it and, when its fuse is in the same section, the
  fuse above it, wired (levels `wire_spacing` apart, picked so no two wires run on top of each
  other); a fuse whose meter is elsewhere is a unit on its own (FROM above, "TO PM-s-n SHEET n"
  below). Each section is a column running the full height of the page with its label at the
  top (Sammy, 2026-10-23: uses the empty space below, better as devices are added); its units
  stack down it and carry on in another column beside it, then on the next page (label
  repeated); sections sit side by side; clear of the title block. One voltage tap per meter is connected; more get a warning and are
  drawn on their own. A meter takes as many CT sets as its model has current inputs (UMG 801:
  2); more get a warning. A meter whose block isn't built yet (PM8000) is a labelled box.
  Spacing in config `device_pages`. Sheet numbers are the page numbers ("{page}"); the 3-line
  CT SHEET# and tap TO_SHEET are filled from the device pages, and the device pages' CT input
  and voltage input sheets from the 3-line.
**Reason:** Sammy, 2026-10-23.
**Status:** Approved (naming built 2026-10-23); device pages built, for Sammy's review

### 2026-10-22 — Bus-break blocks: which flip, and flipped on a vertical bus's bottom end
**Decision:**
- Tested on the blocks: on both 3P_TIDE_R0 and BRACKET_TEXT_R0, **Flip state1** mirrors
  left-right (horizontal bus) and **Flip state2** up-down (vertical bus). The program only
  ever turns on the one named in config (`bus_break.*_flip_*`). Before, an incoming page
  break's bracket got every flip setting at once.
- A vertical bus cut or continued with its bracket **below** the end (e.g. the bottom of a
  too-tall column below the main bus) has its tilde and bracket flipped up-down. Replaces the
  earlier "neither is flipped (as in ES_11 and ES_12)".
- Known, in the block (not the program): BRACKET_TEXT_R0's label keeps its middle-left
  justification when flipped left-right, so "FROM ES_nn" runs back over the bracket and the
  bus. Same whether flipped by hand or by the program (checked 2026-10-22).
**Reason:** Sammy, 2026-10-22 (section 6 of the showcase drawing).
**Status:** Approved (flip rule); bracket label: Sammy to decide

### 2026-10-22 — Less room between breakers and their feeds
**Decision:** `main_breaker.gap_breaker_to_input` 30 -> **12** (main breaker to its
termination, single breaker to its output; also the starting length of a crossing feed's run
and of a main-lugs riser, 15 + 12); `line_side_breakers.gap_breaker_to_output` 25 -> **15**;
the placeholder heights the bus planner reserves for main and single breaker risers
75 -> **57** (down by the same 18 as the gap). Voltage taps still lengthen the run when there
are any.
**Reason:** Sammy, 2026-10-22: that much space isn't needed, and less fits more on a section
vertically (a single breaker under a main with CTs and a crossing feed now fits).
**Status:** Approved

### 2026-10-22 — Incoming feed and main breaker split (option B); voltage taps on the feed
**Decision:**
- **Option B:** the incoming feed and the main breaker are separate things in the data.
  `IncomingFeed` = the termination (input block attributes, termination feed direction) and
  its line side (voltage taps now; CPTs, relays, load-bank ties later), with a stable id.
  `MainBreaker` = breaker, mounting, breaker feed direction, comms, CTs, and its feed.
  Reason: a feed can be in a different section from the breaker it feeds (Sammy has seen an
  input in section 1 crossing into section 2's main), and the load-bank breaker ties into a
  feed, so the feed must stand on its own.
- **Parts (approved shape):** Main breaker (feed "in this riser", or a standalone feed picked
  from another section); Incoming feed on its own (to a main breaker that picks it, or straight
  to the main bus = main lugs only); Line-side breaker (load bank, tied into a feed's line
  side); Single breaker and Group mounted unchanged.
- **Cross-section runs:** neighbouring sections only to start; the two sections are kept on the
  same page automatically; anything else gets a warning. The run crosses horizontally into the
  breaker's line-side run where the input normally sits (staggered corners, no dots). First case
  to draw: a feed above the bus crossing into a top-fed main.
- **Voltage taps** (Sammy's `3P_Voltage_Tap`, FROM_LEFT state on a riser, markers LA/LB/LC): on
  the straight run between the main breaker and its termination, nearest the breaker first,
  `clearance` 5 apart; the run (30) grows to fit them. Each tap picks the power meter it feeds;
  fuses FA-1, FA-2, ... through the lineup fill FUSE_DRW_NUM; TO_SHEET keeps its default until
  device pages exist. Not yet on a U-turned or bus-side-fed feed (warning).
- **Editor:** the main breaker page shows the breaker, then an "Incoming feed" box (termination
  feed direction, input block attributes, voltage taps); a single breaker's box is "Output".
- **Files:** format 2 saves the main's "feed"; format 1 files are read into a feed.
- **Build order:** (1) split + taps (built 2026-10-22, tested by Sammy: "good on drawing");
  (2) standalone feeds (built 2026-10-22, below); (3) line-side breaker (load bank).
- **Step 2 as built:**
  - An "Incoming feed" part. A main breaker's "Feed" is "In this riser" or an Incoming feed
    part; the feed part shows what it goes to. Nothing points at it = main lugs only.
  - Main lugs only: riser from the main bus straight to the termination, at least
    `gap_bus_to_breaker` + `gap_breaker_to_input` (45) long, growing to fit its taps (nearest
    the bus first). Tees in with dots, or bends where the main bus starts / ends.
  - Crossing: the main's line side runs `gap_breaker_to_input` to where its input would sit,
    turns across into the feed's section (A on top, staggered corners, no dots), and runs at
    least `gap_breaker_to_input` to the feed's termination, growing to fit the feed's taps
    (nearest the crossing first). The two sections are linked onto one page.
  - A section holding only a crossing feed doesn't carry the main bus (the bus only exists
    where it is used), so a feed in section 1 starts the main bus at section 2's main.
  - Not drawn yet, with a warning (and a placeholder): a feed not in the next section, on the
    other side of the bus, already feeding another main, or a main with no feed chosen; a main
    fed from another section must be fed on the side away from the bus. A feed a main points
    at but that can't be drawn is never drawn as main lugs only. A U-turned standalone feed is
    drawn straight, with a warning.
- **Step 3 as built (line-side / load-bank breaker), measured from Sabey-011475 (52-LBBA):**
  - A "Line-side breaker" part: label, comms, mounting (main breaker blocks), breaker and output
    block attributes, and "Fed from" (any incoming feed in the lineup).
  - The tie leaves the main's line side nearest the breaker: `tie_gap` 11.2 from the main
    breaker's line-side terminals to the tie's nearest phase; A on top, staggered, a dot where
    each phase tees into the riser. The main's voltage taps go beyond the tie, then its
    termination; the run (30 minimum) grows to fit.
  - The line-side breaker's line-side terminals are `gap_to_breaker` 16.0 beyond the tie's outer
    phase; its output termination `gap_breaker_to_output` 25.0 beyond its other end (config
    `line_side_breakers`). Its section doesn't carry the main bus unless something else in it
    does; the two sections stay on one page.
  - For now (warning otherwise): fed from a main breaker's own feed (not a feed by itself), in
    the next section, same side of the bus, that main fed straight; one per feed. No CTs or
    feed-direction choices on the line-side breaker yet.
  - 011475 also has a set of staggered dots part-way along the tie in section 1 joined to
    nothing; taken as leftovers and not drawn.
- **Fixes found in the stage 2/3 test drawing (2026-10-22):**
  - A feed crossing into a main, or a line-side breaker, is drawn from the main's bus height,
    so the main's section now keeps room for it when the bus is placed (section 1's feed ran
    off the top of the page).
  - Where the main bus begins it bends into the section's LEFTMOST riser, and where it ends
    into the RIGHTMOST; the other part tees in with dots. (A main's CTs move its riser right,
    which left a single breaker below it teeing into bus that wasn't there.)
**Reason:** Sammy, 2026-10-22 ("go with yes for all those questions"; "lets go stage 3").
**Status:** Approved; steps 1-3 built (2 and 3 for review). Sammy will re-assess the editor
layout and how the engineer works with it once more is built.

### 2026-10-22 — Meter blocks: inputs are separate blocks, paired in config; devices by section
**Decision:**
- A meter's inputs are **separate library blocks**, not visibility states: `Janitza_UMG801`
  with `Voltage_UMG801_Input` (above it, "FROM FA-# SHEET #") and `CT_Current_Input` (below
  it, "FROM STB-# SHEET #"). A power supply block (24V+/24V-) comes later. Every terminal of
  the meter has a named marker; not all are used.
- **How inputs connect lives in `config/devices.json`**, one entry per meter model: its block,
  and for each input block the meter marker each of its markers lands on. A device's own
  quirks are written there once, when its block is built (the UMG 801: B to VN, C to V3,
  V2 unused). A new meter = a block + one config entry, no code.
- First CT set on a meter: I1-I3; second: I5-I7 (Sabey-011510: STB-1 and STB-2 into PM-1).
- **Audit Blocks** reads every named marker of these blocks and checks each pair exists and
  lines up (placing each input by its first pair), naming a misnamed marker when one sits
  where the expected one should be.
- **Direction (details later):** devices are shown **grouped by section**. A voltage tap and
  CT shorting block in section 2 show on the 3-line in section 2; if the fuses and meter live
  in section 3, they show on the device pages under section 3, referring back to section 2
  (or its sheet; wording to decide). Later: shipping-split connections between sections,
  which this grouping should make straightforward. Standards are expected to come out of
  these development sessions.
**Reason:** Sammy, 2026-10-22 (testing how well blocks can describe themselves to the program).
**Status:** Approved (pairing + audit built); device-page layout to design in step 4

### 2026-10-21 — CTs on the 3-line and power meters (step 1 + 2, built for review)
**Decision:**
- **Editor:** mains, single breakers and ties get a "Current transformers" box (tick to add a
  set: power meter it feeds, current ratio, the CT block's other attributes). Group-mounted
  parts get "Current transformers at the base of the vertical bus". Mains also get "On the
  main bus after the mains join" (Sammy's option b, kept as a choice; not drawn there yet:
  it is drawn on the riser with a warning). Each section gets "Devices in this section" with
  its power meters (model from `config/devices.json`).
- **Names and numbers (program):** meters PM-1, PM-2, ... in lineup order. CT sets numbered
  in lineup order (per section: above, below, tie): set k gets CT numbers 3k-2..3k
  (CT_A/B/C_DWG#), shorting kit k (STB#), LOCATION = its meter, CURRENT_RATIO = the ratio.
  CTs keep pointing at the right meter when meters are added or removed (each meter has a
  hidden id). SHEET# keeps its default until device pages exist.
- **Placement (program):** CT LEFT states on a vertical run, markers A_L/B_L/C_L on the phases.
  - Main / single breaker: on the riser between the main bus and the breaker, centred; the
    riser lengthens to the CT block + `clearance` (5) at each end + the breaker's overhang,
    and moves right so the CTs clear the section edge. The section widens to the CT block.
  - Group-mounted: on column 1 between the main bus and level 1, which moves out to make room.
  - Tie: on the entry side of the tie's vertical run; the tie's step grows (about 70 -> 103)
    so the breaker keeps its usual room on the exit side.
  - Polarity toward the source: main above the bus -> POLARITY TOP, below -> BOTTOM; single
    breakers and group-mounted -> toward the main bus; tie -> toward the side it enters on.
  - Not drawn yet (with a warning): CTs on a breaker fed on the bus side.
- **Warnings:** CTs without a meter, CTs feeding a removed meter, a meter without a model, the
  CT block missing from the catalog.
- Power meters are not drawn on the 3-line (they go on device pages, step 4).
**Reason:** Sammy, 2026-10-21 ("Go for 1 and 2").
**Status:** Built for Sammy's review (placement details are the program's proposal)

### 2026-10-21 — Comms module choice; CTs and power meters (rules so far)
**Decision:**
- **Comms:** the breaker's comms checkbox becomes a drop-down of communication modules:
  None, Siemens COM190, Siemens COM800 (list in `config/devices.json`). The engineer chooses
  for now. Background for the comms logic: COM190 goes on the larger **3WA** breakers and
  connects directly (Ethernet); the smaller **3VA** breakers each get a small module
  (COM060; written "COM60" in the references) chained to a **COM800** gateway.
- **Power meters** are labelled with their brand: Schneider PM8000, Janitza UMG 801 (blocks
  exist; Sammy is finishing edits). A power meter can live in a different section from the
  CTs that feed it; the engineer decides both from the one-line.
- **CTs** (`3_CTS_3L_R1`; markers per state, tags ending _L / _T / _B for left / top /
  bottom): can go on mains, single breakers, ties, or at the base of a group-mounted
  vertical bus. The engineer picks the breaker; **the program places them wherever they fit**,
  always on a stretch that carries the full current with no fork between the CTs and what
  they measure (e.g. after two sources have met). Without forking, line or load side doesn't
  matter. **Polarity always points toward the source.** The block's visibility state is
  chosen from that.
- The CT block's SHEET# keeps its default for now, but the program should fill in the sheet
  the meter is on once that page exists.
- **Voltage taps** for the meters are part of this work. Fuses are moving off the 3-line onto
  their own device pages (being workshopped; may become the new standard). Tap lines go on
  the correct wire layers; Sammy can make a tap block if needed.
**Reason:** Sammy, 2026-10-21.
**Status:** Approved (comms drop-down built); CT / meter / tap drawing details to confirm

### 2026-10-20 — Drawing Information cut down; HYPER_A template; only layouts with content
**Decision:**
- **Drawing Information holds only the job number and the item name.** The job number is
  required: a warning shows until it is entered and no drawing is made without it (it will
  also be the key for fetching from Arena). The item name comes from Arena, pasted in for now
  ("Fetch from Arena" comes later). The System fields, approvals, drop-down lists and the
  generated breaker count from 2026-10-19 are removed.
- **Template: HYPER_A** (the team's template, `CAD BLOCKS\TEMPLATE\HYPER_A.dwt`) replaces the
  old EW_SWBD_TEMPLATE copy. Its location is in config (`template_source`), like the symbol
  library. The configurator draws from its own copy, `templates/HYPER_A.dwt`, refreshed by
  every release (and by `tools/update_template.py`); reading the shared file directly comes
  much later, with similar changes.
- **Title block:** HYPER_A's title block shows drawing properties through fields, so the
  configurator only sets drawing properties: FG NUMBER = job number (the template's own fields
  make FGD 900-<job> and each row's drawing number: one-line EO-, schematic ES-, wiring EW-),
  FG DESCRIPTION / NUMBER OF BREAKERS = the item name on two lines (split at the comma nearest
  the middle when it's long), TOTAL PAGES ES = the number of 3-line pages. It fills every sheet. *(2026-11-11: TOTAL PAGES ES is now
  every page of the drawing, TOC to the last ES page: see 2026-11-11.)*
- **Layouts:** a generated drawing keeps only these layouts, with tabs in this order: the
  legend (LEG_ES), the BOM page (BOM_ES; not used yet), then the 3-line pages drawn (ES_01 ...).
  Template pages kept are listed in config (`keep_layouts`). All other (empty) layouts are
  deleted; the drawing opens on ES_01.
- **Sheet numbers** ("08 OF 02" on ES_01: the template's frames carry fixed page numbers) are
  a template update for Sammy, not a program change. **Arena** fetching is on hold for now.
  *Updated 2026-11-10: the table of contents (TOC_ES) is kept as page 1, before the legend;
  page numbers are to be filled in by the program, using an engineer's LISP as the model.*
**Reason:** Sammy, 2026-10-20.
**Status:** Approved

### 2026-10-19 — General Drawing Information (first version, for review)
**Decision:**
- "Drawing Information" is the first entry in the section list; selecting it shows a page
  with Job (job number, revision), System (board type, designation, bus rating + material,
  voltage, system, short circuit rating, enclosure), Approvals (initials + dates), a live
  title-block preview, and a greyed-out "Fetch from Arena" button (Arena: later).
- Drop-downs for every choice-type field, lists in `config/drawing_info.json` (placeholders
  until Sammy's lead reviews them).
- ITEM NAME line 2 counts **every** breaker (mains, ties, single and group-mounted), by trip
  rating, largest first. Interim: the trip rating is read from the breaker's attribute text
  ("...1600AT..."); without one it counts as "?A". To be settled with the lead.
- FGD = "900-" + job number, DWG = "ES-" + job number (formats in config).
- Generated drawings are **named after the job number** (replacing the previous drawing of
  the job, after asking); without a job number, project name + date as before.
- The title block is filled through attributes on the template's MAIN_BLOCK (tags
  ITEM_NAME_1, ITEM_NAME_2, FGD, DWG_NO, REV); Sammy is adding them. Until then generating
  reports that the title block was not filled. The block's own contents are never edited.
- Every breaker (main, single, group-mounted, tie) has a **Comms** checkbox, saved with the
  project; what it draws is worked out later.
**Reason:** Sammy, 2026-10-19 (to show the lead on 2026-10-20 before release as 2.1.0).
**Status:** Approved for review (lists, line 2 rule and attribute tags may change)

### 2026-10-19 — "Updates since your last session" pop-up, and SPACE slots
**Decision:**
- When someone opens a version newer than the one they last used, the app shows a pop-up
  titled "Updates since your last session": every version since their last one, newest
  first, each with its version number and short notes, ending (after some space) with
  "Go try it out :)". Shown once per version. The very first start shows the current
  version's notes.
- Release notes are short descriptors, one per change, worked out together at each release
  (Sammy also presents them at the weekly meeting). They live in CHANGELOG.md, ship inside the
  app, and are written by the release command (`--note`, once per change).
- **SPACE** is a choice for any empty slot (twin and single levels), next to Breaker and
  Provision: drawn like a Provision (solid bus taps to where the breaker would connect) with
  just the word "SPACE" (config `feeder.space_text`).
- This goes out as **2.0.1**.
**Reason:** Sammy, 2026-10-19.
**Status:** Approved

### 2026-10-19 — Answers from the six Sabey reference jobs
**Decision:**
1. **Single section switchboards** (what the references call panelboards: one vertical bus, no
   horizontal main bus, mains as levels fed from the side) are in scope. This is the name from
   now on. Possibly chosen in the General Drawing Information tab if it doesn't fit the
   section editor. Design to come.
2. **Load-bank / line-side output breakers are in scope** (a breaker fed from a main's line
   side, as in 011475/011484/011486). Idea to explore: enter the input feed and the input
   breaker as two separate parts, which may also handle line-side output breakers. Design to come.
3. **Riser length grows with its devices:** a main breaker's 15 (to the bus) and 30 (to the
   input) become minimums; CTs, shorting blocks, fused taps, CPT, relays etc. on the riser push
   the breaker and the input further out. Applies when those devices are built.
4. **Tie breakers: no change.** Where the tie sits in its section doesn't matter as long as its
   feed direction is right; the current logic (right edge, step) stands, and the tie's section
   adapts to the drawing.
5. **First 3-line page stays ES_01** (page N -> ES_0N). Which drawing holds what is still being
   worked out; the existing rule is what's in scope.
6. **"SPACE" becomes an option on twin levels**, beside breaker and Provision (style details
   below, to confirm).
7. **Side-jog ("centre-fed") vertical buses:** unknown whether Hyper builds them; on the watch
   list for Sammy's team meeting. Not built.
8. **Communications page is in scope.** The comms rules from the studies are correct (3WA:
   COM190 + CAT6 home run to the Ethernet switch; 3VA: COM060 on a COM800 chain through
   T-connectors, 0.4 m drops, 1 m between tees, EOL terminator). The editor gets a **comms
   checkbox on each breaker**; the logic behind it is worked out later.
9. **Title block content comes from Arena** (PLM). There is a request to fetch it from Arena by
   job number; feasibility to be looked into. Which fields go in the title block is not known yet.
10. **The main-to-main interlock is always drawn** on the 3-line (dashed "MECHANICAL AND
    ELECTRICAL INTERLOCK" line between the mains). Jobs that leave it out are mistakes.
    *Corrected 2026-10-26: only mains the engineer marks as interlocked get the line; see
    "Interlocks are chosen by the engineer".*
11. Sabey-011485's printed set (one-line printed, blank pages) is a mistake; Sammy will fix it.
**Reason:** Sammy, 2026-10-19, on the 2026-10-19 study report.
**Status:** Approved (items 1, 2, 6 and 8: designs to come)

### 2026-10-16 — Installer is published zipped
**Decision:** The installer goes in SharePoint as `Install Switchboard Configurator.zip`
(holding the .exe), never as a loose .exe. People open the zip and run the installer from
it (or extract it first); it copies itself to their PC, so nothing else changes. Updates
were already zip-only (`Releases/X.Y.Z/*.zip` + `latest.txt`). Windows and IT have no
problem with the .exe itself.
**Reason:** Sammy, 2026-10-16: SharePoint won't sync a loose .exe file.
**Status:** Approved (release command changed; the live 2.0.0 folder fixed the same day)

### 2026-10-15 — Ready for release 2.0.0
**Decision:**
- **Drawings** are saved in a folder each person picks; the app remembers it (per person,
  on their PC) and it can be changed.
- **One person edits a project at a time.** Opening a project someone else has open gives
  a read-only copy (Save As still works).
- **Icon:** the letters "SWBD" for now (a picture comes in a later update).
- **Testing:** Sammy installs from SharePoint like a teammate (also to use and show the
  app outside the development space), then one teammate tests before the team gets 2.0.0.
- Feeder block prompts are left as they are for this release.
**How it was built (2026-10-15):**
- The app is zipped per version (`Releases/X.Y.Z/Switchboard Configurator X.Y.Z.zip`): one
  file syncs through OneDrive far better than thousands. The launcher unzips it into
  `%LOCALAPPDATA%\Hyper Configurators\Switchboard Configurator\versions\X.Y.Z\` and keeps one
  older version. Offline, it starts the newest version already on the PC.
- One .exe is both installer and launcher. Run from SharePoint it installs itself and the
  shortcuts; run from the shortcut or the ribbon it launches. It logs each run
  (`launcher.log`).
- The AutoCAD add-in (bundle with a .cuix and a LISP command HYPERSWBD) ships inside each
  version and is refreshed by the launcher; it loads only in plain AutoCAD 2026 (R25.1).
- Builds are made outside OneDrive (OneDrive locks files mid-build).
- The released app checks for updates on start and every 30 minutes; Help > About shows the
  version and where things are.
- Tested end to end in a sandbox (install, launch, update offer, restart into the new
  version). The ribbon tab inside real AutoCAD and Generate from the installed app are
  checked by Sammy's own install.
**Reason:** Sammy, 2026-10-15.
**Status:** Approved

### 2026-10-15 — Version numbers
**Decision:** Releases are numbered X.Y.Z. Z = routine changes and small fixes; Y = something
changed but not huge; X = a milestone. The first release to the team, once the app
interface changes are settled, is **2.0.0**.
**Reason:** Sammy, 2026-10-15.
**Status:** Approved

### 2026-10-13 — Fixes from the first full test drawing (115535)
**Decision:**
- **Tie breaker attributes:** the tie breaker gets one editor field per attribute of its
  block (fixed or draw-out), like a main breaker; its Label fills the breaker-name attribute.
- **Bus entering a new page:** the bus enters a new page at the height the first section
  on it needs. That section does not step the bus and does not pay for a step zone. Page 1's
  bus leaves at its own height; the break blocks and labels sit at each page's height.
- **U-turn to a termination (main and single breakers):** coming out of the U-turn the bus
  runs `u_turn_termination_rise` (5), then the termination block. The U goes only as far as
  needed for the termination's text (which faces back toward the breaker) to stay
  `u_turn_text_clearance` (5) clear of the breaker and its text. Sizes come from the catalog;
  each line break typed in the termination's attributes adds text height x
  `line_spacing_factor` (1.667, AutoCAD's MText spacing). Replaces the fixed depth 28.43 for
  this U; `u_turn_depth` still sets the U-turns of a breaker fed on the bus side.
- **Tilde where the bus arrives on a page:** mirrored like the bracket, using only its
  left-right flip setting (`bus_break.tilde_flip_horizontal_bus`, "Flip state1"; tested on
  the block: Flip state2 belongs to its vertical state), so its A/B/C letters sit on the
  incoming side instead of over the bus.
**Reason:** Sammy's review of `output/New switchboard 2026-10-13 115535.dwg` (sections 1
and 6: termination text ran into the main bus; page 2: the bus bent right after entering;
the incoming tilde was not flipped).
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
