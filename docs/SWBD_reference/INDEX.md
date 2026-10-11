# SWBD Reference Index

Finished switchboard jobs used as "what correct looks like." Claude keeps this file up to
date: any job in this folder that is not listed here gets studied and added at the start of
the next session (see CLAUDE.md). Sammy only needs to drop the files in.

Each job should have a `.dxf` (exact geometry) and a `.pdf` (visual check) with the same
base name. `.dwg` files cannot be read directly; they are kept only as originals.

Entry format:

```
## <JOB NAME>
**Files:** which of .dxf / .pdf / .dwg are present
**Studied:** YYYY-MM-DD (or "not yet" with the reason)
**Contents:** sections, mains, ties, feeders, other devices, number of pages
**Measurements:** margins, spacing, title block size, etc. (drawing units)
**Proposed rules (pending approval):** patterns seen here that the configurator may need
**Questions for Sammy:** anything unclear
**Sammy's notes:** anything Sammy said about this job (optional)
```

---

## Cross-reference summary (8 jobs, updated 2026-10-08)

**Same in every job:**
- Frame `TITLE_BLOCK_MODEL`: drawable 419.04 x 269.49, title block 82.41 x 70.96,
  grid pitch 633.57 x 413.07, viewport scale 0.0375. Model space 1:1.
- Bus phase spacing 5; A on top (horizontal) / A on the left (vertical).
- Layers: BUS, GROUND, TEXT, phase wire layers `WIRE - 480A-BRN / 480B-ORG / 480C-YEL`.
- Junction dot: filled, diameter 1.5, layer BUS (usually block `BUS_NODE`).
- Ground bus: horizontal line near the bottom, labelled "GROUND BUS", stops before the
  title block.
- Page title "THREE LINE DIAGRAM 0n" just left of the title block.
- Nothing ever enters the title block keep-out.
- Sections stay in order; a 2-page 3-line splits between whole sections.
- None of our `SCHEM_*` / `SCHEME_*` blocks appear in any job.

**Newer jobs (all 7 NTT/NTC/PRIME), differs from ES-011511:**
- 3-line lives in `ES_nn` frames shown by `ES_nn` layouts. `EO_01` is a separate one-line
  drawing (its own number EO-xxxxxx). ES-011511 (older) had the 3-line in frame EO_02.
- Title block content comes from one shared `MAIN_BLOCK` via a second small viewport.
- Block library: `BREAKER_FIXED_SCH_R0` / `BREAKER_DRAWOUT_SCH_R0` (one pole each, 10 long,
  3 per breaker), `SIE_BKR_3P_3L_R0` (3-pole, ratings as attributes), `SIE_LUGS_3P_3L_R0`,
  `CDP_BUS_HORIZ_3PH_3W_3L` (feeder tap, left/right/both visibility),
  `BUSSING_3PH_3W_3L` (bus corners/runs, dynamic), `ITEM#_BOM_R0` (BOM balloon),
  `KIRK_KEY_BLK`, `TERMINAL_BLOCK_BLK`. Right-side feeders mirrored (xscale -1).

**Varies between jobs (no consistent rule yet):**
- Divider layer: BYOTHERS + ISO02 (4 jobs) vs DEVIDER + ISO04 (3 jobs). Outer dividers:
  usually none on the left; right edge inconsistent. Clearance to text 1–14 (typ. 2–10).
  NTT-013631 used fixed quarter-page dividers; NTT-013630 used stepped dividers.
- Side margins: ~2.5 to ~84. Small jobs float left of centre.
- Feeder row pitch: 25 (3 jobs), 30 (1), 50 (2). Gap main bus → first row: 10–15.
- Section labels: bottom under the ground bus (most) or top (2 jobs); h 1.25 or 2.0.
- Page break: squiggle + bracket + A/B/C (PRIME-014032), bracket block "XXX" + A/B/C
  (PRIME-014034), or nothing (NTT-013630). Bus height can change between pages.

**Patterns not covered by current rules (seen in 2+ jobs):**
- Main/feeder on a vertical riser; riser turns into the bus with a staggered corner (no
  dots) at a bus end, or tees in with dots mid-bus.
- Two feeder styles: (a) one breaker in line on a vertical riser off the main bus;
  (b) horizontal breakers tapping a vertical distribution bus (alternating singles or pairs).
- Main bus at two elevations joined by a vertical breaker (tie / bypass coupler). No job
  draws a tie inline in the horizontal bus.
- Two mains (utility + gen) with an interlock line, no tie.
- Incoming block above/below each main: lug symbol, A/B/C letters, "PROVISIONS FOR…" and
  rating text. Load-end lug symbol + lug text on every feeder.
- Metering and control on the 3-line: CTs on the bus, fused voltage taps, CPTs, SPD via its
  own breaker, shorting terminal blocks, "TO X SHEET n" references.
- BOM balloon on every device. Vertical bus end overhang with A/B/C + rating label.

**Seen once:** two-column vertical bus with "BUS CONTINUATION" (ES-011511); pull section
with no breaker (PRIME-014032); separate UPS/critical/main buses (NTT-013630).

---

## ES-011511_A_REFERENCE
**Files:** .dxf, .pdf (original .dwg is in the V4.12.2 `templates/` folder)
**Studied:** 2026-10-07

**Contents:**
- SWBD BC-HDP-1, 2000A, 480V 3P3W, 65kAIC. 2 sections. 1 main (52-MCB-01, 2000A),
  17 feeders (52-F2 to 52-F18), SPD, fuses FA-1/FA-2, 3 CTs + shorting block, power meter.
- 6 PDF pages: 01 table of contents, 02 plan + front elevation, **03 power schematic**
  (the page the configurator produces), 04 control power, 05 thermal sensors (ITSI),
  06 communications.
- Hand-drafted: breakers are exploded geometry, not blocks. None of our `SCHEM_*` blocks
  appear. Useful for spacing and page structure, not for block connection points.

**Drawing structure (how pages map to AutoCAD):**
- All drawing is in model space at 1:1. Each page is a `TITLE_BLOCK_MODEL` block insert
  (scale 1.0, layer GRID) with attributes `NAME` (e.g. EO_02) and `PAGE` (e.g. 03).
- Frames sit on a grid: column pitch 633.57, row pitch 413.07. Rows: TOC, EO_01–EO_06,
  ES_01–ES_10, ES_11–ES_20, ES_21–ES_30. Only TOC_01 and EO_01–EO_05 hold content.
- Paper-space layouts (11x17) each have one viewport onto a frame at scale 0.0375 (1:26.67).
  Layout names don't match frame names: layout `ES_01` shows frame `EO_01`, etc.
- Page 03 (power schematic) is frame `EO_02`, inserted at (-1205.35, -432.29).

**Measurements** (drawing units, relative to the frame's insertion point):
- Drawable border: x 0 – 419.04, y 0.05 – 269.54 → **419.04 W x 269.49 H**.
- Title block keep-out: x 336.63 – 419.04, y 0.05 – 71.01 → **82.41 W x 70.96 H**,
  bottom-right corner. Content over that x-range stays above y 100.8.
- Actual content extents: x 5.73 – 367.72, y 3.06 – 268.71. So the real margins are
  ~6 left, ~1 top, ~3 bottom, i.e. far tighter than our 10.
- Bus phase spacing: **5.0** (A, B, C). Confirms the 5-unit rule.
- Main bus: horizontal, y 170.34 / 165.34 / 160.34 (A/B/C), x 50.61 – 368.5. Runs past the
  last feeder column; does not go to the page edge.
- Incoming (section 1): lugs at the bottom-left; 3 risers come UP from y 36.91 to the main
  bus, then the main breaker sits inline on the main bus (x ~41.6 – 50.6).
- Section divider: one dashed line (layer BYOTHERS, linetype ACAD_ISO02W100) at x 136.05,
  from y 264.02 down to the ground bus (y 8.47). Only BETWEEN sections: none at the left
  edge or after the last section.
- Gap from divider to nearest component: section 2 side **~10.8** (to feeder cable text);
  section 1 side ~35 (section 1 just has spare room).
- Section labels: "SECTION 1", "SECTION 2", text height 1.25, centred under each section
  at y 3.83, below the ground bus.
- Ground bus: one horizontal line, layer GROUND, y 8.47, x 4.38 – 331.65, labelled
  "GROUND BUS".
- Vertical bus (section 2): drawn as **two columns**, at x 188.55/193.55/198.55 and
  x 316.02/321.02/326.02 (column pitch 127.47), each y 81.78 – 255.79. Column 1 ends with
  "BUS CONTINUATION TOP RIGHT"; column 2 starts with "BUS CONTINUATION BOTTOM LEFT".
- Feeder rows: pitch **30.0** vertically. Each feeder = 3 horizontal taps 5 apart.
  Above the main bus, top phase at y 251.6 / 221.6 / 191.6; below, y 142.24 / 112.24.
- First feeder row above the main bus: its lowest tap is 11.26 above the main bus's top
  phase. First row below: its top tap is 18.10 below the main bus's bottom phase.
- Feeder taps run 11.35 out from the outer bus line on each side (left pair and right pair
  are mirror images about the vertical bus).
- Vertical bus extends ~4.2 above the top tap and ~20.5 below the bottom tap (room for
  the continuation label).
- Junction dots: filled circle, diameter **1.5**, layer BUS.
- Layers in use: BUS, GROUND, TEXT, BYOTHERS, DEVICE, GRID, WIRE - 480A-BRN / 480B-ORG /
  480C-YEL, WIRE - CT+_WHT / CT- _BLK, cloud.

**Proposed rules (pending approval):**
1. Config: page drawable area 419.04 x 269.49; title block keep-out 82.41 x 70.96.
2. Page origin in AutoCAD = the `TITLE_BLOCK_MODEL` frame's insertion point. Page N is the
   next frame along the grid (pitch 633.57 / 413.07).
3. Section dividers are drawn only between sections (not at the outer edges), as one
   dashed line from near the top border down to the ground bus.
4. A ground bus runs along the bottom of the power schematic, with section labels below it.
5. Feeder row pitch 30 and junction dot diameter 1.5 go into config.
6. A section whose vertical bus is too tall for the page wraps into a second column,
   with "BUS CONTINUATION" labels at the break.

**Questions for Sammy:**
1. The main breaker here is fed from the BOTTOM-left, with risers up to an inline breaker
   on the main bus. DECISIONS says "main breakers come in from the top." Which is right,
   or are both needed (top-fed and bottom-fed)?
2. Margins: this drawing uses ~1–6 units, not 10. Keep 10 / 5, or change?
3. Divider clearance: closest component is ~10.8 from the divider, not 5. Does "component"
   include its text labels? Keep 5, or change?
4. Two-column vertical bus (rule 6): is this how you want tall sections handled? It is a
   new layout rule not in DECISIONS.
5. Is the configurator only producing the power schematic page (page 03), or also the
   other pages (TOC, elevation, control, ITSI, comms)?
6. Layout names (`ES_01`…) don't match frame names (`EO_01`…). Is that intentional?
7. Should the configurator use these exact layers (BUS, GROUND, TEXT, BYOTHERS…)?

**Sammy's notes (2026-10-08):**
- Q1: Any breaker (main or feeder) can be above or below the main bus. Engineer chooses,
  matching the physical design. → DECISIONS "Breaker direction is the engineer's choice".
- Q2/Q3: Margins 5 / 2.5. Divider clearance 10; text counts as part of a component.
- Q4: Two-column vertical bus needs more study before it becomes a rule.
- Q5: Focus on the 3-line diagram first; other pages later.
- Q6: Drawings go in model space inside the EO frames, shown by the EO layout views.
- Q7: Yes, draw on the correct layers automatically (set in config, hidden from the user).
- Proposed rules 1 and 2 approved (page size, title block, frame = page origin).
  Rules 3–6 still pending; checking them against the other references.

---

## NTC-013632-REFERENCE
**Files:** .dxf, .pdf  **Studied:** 2026-10-08 (PDF not viewed; page list from DXF)
**Contents:** 3000A 480V 3P3W 65kAIC, 3 sections. Main 52-DP-401D-3-MB 3000A top-fed (S1);
S2 one 1600A feeder up; S3 one 1600A up + one down in the same column. FA-1 control-power
fuse tap on the line side → "TO PS-1 SHEET 2". 6 pages; 3-line = frame/layout ES_01, 1 page.
**Measurements:** Geometry is identical to NTT-013628 (same template, 401D vs 301D names).
Main bus y 145.10/140.10/135.10, x 88.4–283.17. Dividers x 164.79, 234.56 (BYOTHERS, ISO02).
Divider-to-text 11.8–24.5. Margins L 83.8, R 135.9 (content floats left of centre).
Feeders: breaker in line on a short riser off the main bus, 12–15 from the bus, no vertical
distribution bus. Ground bus y 71.40. Section labels "SECTION# n" h2.0 at top (y 233.6).
**Notable:** no vertical buses at all; up + down feeder share one column and tap dots.

## NTT-013627-REFERENCE
**Files:** .dxf, .pdf  **Studied:** 2026-10-08
**Contents:** 1600A 480V, 2 sections, 1 main (top-fed, 3WA 2000AF/1600AT) in S1; S2 has a
vertical distribution bus with 10 feeders + 1 provision slot. FA-1/PS-1, MMS, COM190 on
the 3-line. 6 pages; 3-line = ES_01, 1 page.
**Measurements:** Main riser x 10.39/15.39/20.39 turns (staggered corner) into the main bus
y 125.61/120.61/115.61, which runs to the S2 vertical bus (x 273.09/278.09/283.09,
y 21.2–260.6). Feeders horizontal, row pitch 25, alternating left/right singles + 3 pairs,
row slot skipped where the main bus enters, 15 gap above/below the bus, taps 10 from the
nearest phase. One divider x 212.58 (DEVIDER, ISO04), clearance 10.35 / 14.0. No section
labels on the 3-line. Uses SIE_BKR_3P_3L_R0, SIE_LUGS_3P_3L_R0, CDP_BUS_HORIZ, BUSSING.
**Notable:** most block-based job; "1600A CU" label at the vertical bus foot.

## NTT-013628-REFERENCE
**Files:** .dxf, .pdf  **Studied:** 2026-10-08
**Contents:** 3000A 480V, 3 sections, 1 main top-fed (S1); S2 1600A up + 450AT STS down
(cable-connected, lugs both sides); S3 1600A up + down. 6 pages; 3-line = ES_01.
**Measurements:** Same template as NTC-013632 (see above). Up-feeder breakers at different
heights (160.21 vs 157.21) with no visible reason.
**Notable:** cable-connected breaker drawn on layer "Wire"; data mismatches between pages
(STS ratings, 301D vs 401D, "SHEET 2" vs sheet 05).

## NTT-013630-REFERENCE
**Files:** .dxf, .pdf  **Studied:** 2026-10-08
**Contents:** 4000A 480V, 8 sections, Rev B. Utility + gen mains (4000A, bottom-fed, S7/S8,
interlock + ATC). UPS bypass: UIB (N.C.) and MBB (N.O.) 3000A couplers with Kirk keys
linking UPS-output, critical and main buses. 17 breakers, SPD, 2 CT sets, 3 CPTs, PM-1/2.
14 pages; 3-line = ES_01 (S1–5) + ES_02 (S6–8).
**Measurements:** Three horizontal buses at two elevations (y 97–107 and 187–197) joined by
vertical couplers exactly 35 from each bus. Bus elevation changes between pages (97–107 →
172.6–182.6). Dividers DEVIDER/ISO04, several stepped around content; clearance 0.35–9.6.
S6 distribution bus fed from below via a jog; feeder rows pitch 50. Margins L 16.7, R 12–32.
Section labels underlined h1.25 at y 29.5. No page-break symbol.
**Notable:** most complex job; multi-bus UPS arrangement; stepped dividers.

## NTT-013631-REFERENCE
**Files:** .dxf, .pdf  **Studied:** 2026-10-08
**Contents:** 2000A 480V, 4 sections. Gen main (S1) + utility main (S2), both top-fed,
electrical interlock, DTSC-200. 11 feeders + CB-1 → SPD-1; CPT-1/2, voltage fuses, CTs,
STB-1, PM-1. 9 pages; 3-line = ES_01, 1 page.
**Measurements:** Main bus at two levels (y 79–89 across S1–S2, y 166–177 across S3–S4)
joined by a riser carrying CTs and PT fuses. Dividers at exact quarter-page x 104.76,
209.52, 314.28 (BYOTHERS), full border height; clearance 2–10. S3 feeders zig-zag
left/right, pitch 50 per side, 25 stagger, numbered bottom-up. Section labels at top,
centred, y 261.9. Margins L 2.6, R 4.3.
**Notable:** equal-width sections not sized to content; riser between bus levels.

## PRIME-014032-REFERENCE
**Files:** .dxf, .pdf  **Studied:** 2026-10-08 (PDF not viewed)
**Contents:** 4000A 480V, 6 sections. S1 pull/incoming section (no breaker). Utility main
MCB01 (top-fed, N.C., S2) + gen main MCB02 (bottom-fed, N.O., S3), interlock + ATC.
10 feeders (S4, S5 risers up; S6 distribution bus up + down) + SPD. CTs, CPTs, PM-1.
11 pages; 3-line = ES_01 (S1–5) + ES_02 (S6).
**Measurements:** Main bus y 159.14/154.14/149.14. Page break: per-phase squiggle + bracket
+ A/B/C on both pages; divider repeated at both page edges. Dividers BYOTHERS/ISO02,
clearance 1.1–9.8; one divider stops exactly at the title block top. S6 feeder pitch 25,
gap 10 from the bus, 3 pairs + 1 single. S5 label moved up to avoid the title block.
**Notable:** top-fed and bottom-fed mains on the same bus; the only clean page-break symbol.

## PRIME-014034-REFERENCE
**Files:** .dxf, .pdf  **Studied:** 2026-10-08
**Contents:** 4000A 480V, 6 sections. MCB01 main, LB01 (load bank?), TB02 tie, MCB03 main,
all 3000AF drawout top-fed, Kirk keys. 8 feeders + 1 SPACE on two distribution buses (S5,
S6). CTs, STB-1, FA-1/FA-2. 9 pages; 3-line = ES_01 (S1–4) + ES_02 (S5–6).
**Measurements:** Main bus at two elevations (A 180.58 and 110.58) joined by tie TB02 drawn
as a vertical breaker. Bus height differs on page 2 (A 163.94). Feeders alternate
left/right singles, pitch 25, 15 from the bus; tap lengths 10/15/20 by phase. Dividers
DEVIDER/ISO04, clearance 3.3–60.8. Page break: bus overrun + A/B/C + BRACKET_TEXT_R0 with
placeholder "XXX". KIRK_KEY_BLK at scale 0.937.
**Notable:** tie drawn vertically between bus levels, not inline.

## GND_Section_Devider_REFERENCE  (Sammy's style reference, not a real job)
**Files:** .dxf only (no PDF)  **Studied:** 2026-10-09
**Contents:** Built from PRIME-014034. The layouts show grid frames ES_01/ES_02 (PRIME-014034
3-line). Sammy restyled **ES_01** (section labels, ground bus, dividers). Extra copies of
3-line pages from NTT-013631, NTT-013627, PRIME-014032 and NTT-013630 (2 copies) are pasted
off-grid to the left (duplicate frame names ES_01 x6, ES_02 x4; unchanged from originals).
**ES_11 = block palette** (true names of the dynamic blocks): CDP_CHASSIS_BUS_3PH_3W_3L_ASSY,
CDP_CHASSIS_BUS_3PH_4W_3L_ASSY, BUSSING_3PH_3W_3L, BUSSING_3PH_4W_3L, PHASE_LUGS_3L_R0,
CIRCUIT_BREAKERS_2P_3L_R0, 3P_CB_FM_1, 3P_CB_DO, SIE_BKR_1P_3L_ASSY_R0, SIE_BKR_3P_3L_ASSY_R0,
NEUTRAL_CURRENT_SENSOR_BLK_2, 3_CTS_3L_R1, SPD_EATON_3L_R0, CPT_1. Two are being re-labelled
by Sammy (block editing deferred).
**ES_12 = Group Mounted Distribution example** mixing single mount and twin mount on one
vertical bus (copy of NTT-013627 section 2). Tap blocks CDP_BUS_HORIZ_3PH_3W_3L every 25;
rows from top: single L, single R, single L, single R + provision L, twin, [main bus], twin,
twin. Right-hand breakers mirrored (X scale -1).
**Sammy's restyled ES_01 (frame-relative):**
- Dividers: layer DEVIDER (BYLAYER: red, ACAD_ISO04W100), only between sections
  (x 49.96 / 92.17 / 135.00 / 318.33), y **8.44 – 256.33** (was 68.89 – 256.33).
- Ground bus: layer GROUND, y **20.94**, x 7.54 – 327.72 (ends 8.91 before the title block).
- Ground symbol at the left end (x 13.40), layer GROUND: stem 1.98 down, bars 4.92 / 3.69 /
  2.46 wide, 1.23 apart.
- "GROUND BUS" text: layer 0, style Hyper_Text, h 1.17, above the bus line (y 22.28), x 8.2.
- Section labels "SECTION n": layer 0, style Hyper_Text, h 1.25, **not underlined**, below
  the ground bus (y 15.97 – 17.28), roughly under each section.
- ES_02 (page 2) was not restyled: ground bus still y 50.23, dividers 36.35 – 256.33.

## IMS-REFERENCE
**Files:** .dxf, .pdf  **Studied:** 2026-10-09
**Contents:** ES-008672, 5000A 480V MSB with UPS isolation / maintenance bypass. 10 sections.
Utility main 52-U and gen main 52-G (5000A, both bottom-fed), 3000A UPS output bus, bypass
breakers MBB / MIB / UIB1-2 / UOB1-2, group-mounted feeders CB01-CB13. 15 PDF pages;
3-line = pages 3-5, in **EO_04 / EO_05 / EO_06 frames** (not ES, unlike the newer jobs).
**Measurements:** Bus phases 5 apart, A on top. Bus height changes at page breaks (-40,
-14.2), not inside sections. Two main buses (5000A, 3000A) joined by MBB, which loops
below the bus mid-section; a separate upper UPS output bus; a riser that crosses the main
bus without connecting (break marks). Dividers DEVIDER/ISO04, clearance often under 10
(0.5-8.4). The whole diagram sits above the title block: ground bus at y 74-77 running the
full width, no ground symbol, "GROUND BUS" on layer TEXT. Section labels underlined, not
reliably centred. Section 5 is split across pages 3-4 with an L-shaped divider. Group
mounted spacing irregular (gap 18.7-33.5, pitch 17.2-33.3). **All power devices are
exploded geometry**; only annotation blocks (BOM balloons, wire tags, bracket) are inserted.
**Proposed rules (pending approval):** none adopted; mostly older drafting style. Useful as
the most complex lineup seen (multiple buses, bypass loops, crossovers, UPS sources).
**Questions for Sammy:** see the 2026-10-09 chat summary (scope of multi-bus / bypass
lineups; page-start divider; split sections; bus height change at a page break).
