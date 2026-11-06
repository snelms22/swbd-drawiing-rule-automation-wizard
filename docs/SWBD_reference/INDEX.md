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

## Power supplies and 24 VDC control power (across jobs, 2026-11-05)

**Seen:** PS-1 "480VAC/24VDC" (5A, or 240W/10A) fed from its own fused 480 V tap (FA, e.g.
3A) in NTC-013632, NTT-013627 (block `PWR_SUP_1`), PRIME-014034 and CORRECTED_FIXED_011511;
PS-1 "120VAC-24VDC 480W-20A" in Sabey-011486. The 24 V side goes through single-pole DC
fuses FD-1..FD-n (2A-6A/1P LP-CC), one per load: comms gateways (GW-1, GW-2), the Ethernet
switch (ES-1), "CONTROL POWER & MMS FOR CB1, CB2, ..." (breaker control power), a UPS
terminal block (TB-UPS). Each load's end is labelled "FROM FD-n SHEET n" / "<load> CONTROL
POWER SHEET n". Wires on `WIRE - 24+_RED` and `WIRE - 24-_BLK`; legend text "24 VDC PHASE
"+" - RED", "24 VDC PHASE "G/-" - BLACK".
**Proposed rules (pending approval):** a 24 V power supply always comes with its DC fuses
(FD-s-n), one per 24 V load; the loads come from the devices that need control power
(comms, breakers with MMS/electrical operation, Ethernet switch, ATC).

---

## Device page layout (across jobs, 2026-11-05)

**Seen (label positions, frame-relative x, y):**
- NTT-013627 ES_01: FA-1 (44) -> PS-1 (78) -> FD1/FD2/FD3 stacked in one column (117; y 189,
  170, 150) -> COM190 (164). Power flows left to right.
- PRIME-014034 ES_03 (control power page): "FROM FA-4" (55) -> PS-1 top left (74, 259) ->
  FD-1..FD-6 stacked in one column (174; y 251 down to 113) -> one load level with each
  fuse (198+: GW-1, GW-2, ES-1 "CONTROL POWER SHEET n", TB-UPS, SKRU) -> PM-1 far right
  (333, 194).
- PRIME-014034 ES_05 (comms page): Ethernet switch ES-1 on the left (120), COM190s and PM-1
  to its right, the COM800 / COM60 chain below.
- Pages are by function (control power, metering, comms), not by section.

**Proposed rules (pending approval):**
1. Devices are placed in tiers, left to right, along the flow: the source (FROM brackets or
   a fuse) -> the device it feeds (power supply) -> its distribution (FD fuses, stacked) ->
   the loads, each level with the fuse or wire that feeds it, so most wires run straight.
2. When a tier gets too tall for the page, the chain carries on on the next page with TO /
   FROM brackets.
3. ~~Pages by function~~: withdrawn 2026-11-05. Hyper is moving to a hybrid schematic +
   wiring diagram (Sammy's recreated NTT-013628, to come), which puts devices on pages by
   section, with every connection to the shipping splits, terminal blocks that split wires,
   and how fuses connect. Judge these rules against that drawing, not the older references
   (all schematic-only).

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

## FIXED_011511  (Sammy's corrected ES-011511)
**Files:** .dxf only  **Studied:** 2026-10-12
**Contents:** ES-011511 with Sammy's corrections. **ES_12** shows the corrected "too tall"
group-mounted bus and how breaks in a bus are drawn.
**Measurements (ES_12, frame-relative):**
- Main bus A/B/C at y 169.05 / 164.05 / 159.05, x 51.18 – 392.85.
- Column 1 vertical bus x 189.13 / 194.13 / 199.13, from y 13.44 (bottom) to 254.31 (top).
  Feeder levels on it every 30 (taps 177.78 – 210.47).
- At its top end: `TILDE_R0` inserted at (189.13, 254.31) = the A-phase end, and
  `BRACKET_TEXT_R0` at (194.13, 256.56) = over the B phase, 2.25 beyond the end.
- Column 2 (the continuation) x 292.35 / 297.35 / 302.35, column pitch 103.22. It starts
  at y 184.56 (15.5 above the main bus's top phase) with `TILDE_R0` at (292.35, 184.56)
  and `BRACKET_TEXT_R0` at (297.35, 182.44), 2.12 before the start, and runs up to 237.19
  (A/B/C letters at 238.94). Not connected to the main bus.
- Both blocks at scale 1, rotation 0, not flipped.
**Block facts (library, 2026-10-12):** `TILDE_R0` dynamic (HORIZONTAL / VERTICAL, two flips,
Distance1/2 = 5); `BRACKET_TEXT_R0` dynamic (VERTICAL / HORIZONTAL BRACKET, Distance1/2 =
10 = A to C, two flips). The bracket's "XXX" label is plain text, not an attribute. Neither
block has CONN_ markers yet.
**Proposed rules (pending approval):** see the 2026-10-12 chat: a too-tall vertical bus is
cut after the last level that fits, marked with tilde + bracket, and continued in a new
column beside it that starts with tilde + bracket.

## CORRECTED_FIXED_011511  (Sammy's further-corrected ES-011511)
**Files:** .dxf only (no PDF)  **Studied:** 2026-10-13
**Contents:** Same as FIXED_011511 plus one new page: **ES_11** (was empty) now holds a full
2-section 3-line page. ES_12 and everything else are unchanged (only AutoCAD's anonymous
block names were renumbered).
- **Section 1** (x 5.9 – 113.9): bottom-fed main 52-MCB-01 (2000AF/2000AT, 3P LSIG). Input
  lugs at the foot of a vertical incoming bus (x 25.21 / 30.21 / 35.21, from y 37.78), "LUGS
  (6) 600KCMIL PER PH", A/B/C letters, "480VAC, 3PH, 3W+G / 2,000A", "(BY OTHERS)". The bus
  turns right at y 171.21 / 166.21 / 161.21 into the main breaker (bus gap x 43.15 – 52.15),
  runs to x ~124–134, then steps down with a `BUSSING_3PH_3W_3L` corner (rot 90) to the main
  bus at y 120.44 / 115.44 / 110.44. On the incoming bus: CT1–3 (2,000:5A) with shorting block
  STB-1, fused taps FA-1 (3A, to PS-1) and FA-2 (1A, to PM-1), SPD1 on 52-SPD (125AF/30AT).
  These devices are exploded geometry; BOM balloons and WIRE_TAG_R0 are blocks.
- **Section 2** (x 113.9 – 342.7): group-mounted twin feeders on a vertical bus at
  x 183.92 / 188.92 / 193.92, breakers at x 168.07 (L) / 209.77 (R). Above the main bus:
  52-F2 … F7 (250AF), up to y 258.32 (A/B/C letters at 260.07). Below the main bus: 52-F11 …
  F16 (600AF), levels every 30, down to the cut at y 20.94.
**Measurements (ES_11, frame-relative), the "too tall" case going DOWN:**
- Column 1 is cut at its **bottom** end: `TILDE_R0` at (183.92, 20.94) = A-phase end;
  `BRACKET_TEXT_R0` at (188.92, 18.44) = over B, 2.5 beyond the end.
- Continuation column at x 278.92 / 283.92 / 288.92 (column pitch **95.0**; ES_12 was
  103.22). It starts at its **top** y 89.94 (20.5 below the main bus's bottom phase 110.44)
  with `TILDE_R0` at (278.92, 89.94) and `BRACKET_TEXT_R0` at (283.92, 92.44), 2.5 before
  the start, and runs down to 44.10. It holds 52-F17 (left) and 52-F18 (right), single mount
  (800AF, 2-hole lugs).
- All tilde/bracket blocks at scale 1, rotation 0, not flipped (same as ES_12).
- Page style (ground bus height, underlined labels) is the old style; the approved ES_01
  style stays.
**Rules adopted (2026-10-13):** bracket 2.5 beyond the tilde, over B, at both cut and
continuation (ES_12 had 2.25 / 2.12); the too-tall split (DECISIONS 2026-10-13).
**Sammy's notes (2026-10-13):** ES_11 is the typical "too tall" case: the part BELOW the
main bus is the one that gets split (see DECISIONS 2026-10-13). The sideways main breaker in
section 1 is a drafting error; that arrangement is not needed.

## Sabey-011475
**Files:** .dxf, .pdf  **Studied:** 2026-10-19
**Contents:** SWBD 5000A 480V 100kAIC, MA-HDP-X, 7 sections, Rev A. S1 load-bank breaker 52-LBBA
fed from a bus duct termination, tied into the LINE side of the gen main's riser in S2 (not the
main bus). S2 gen main + SPD breaker below; S3 utility main (tees in with dots); S4, S5, S7
group-mounted; S6 single breaker 2500A below the bus. No tie. 14 sheets: TOC, legend, BOM,
**ES_01 = elevation**, **3-line = ES_02 + ES_03**, control/ATC/lights/breaker-control pages,
**ES_11 = network/communication**. One-line in EO_01 (separate drawing).
**Measurements:** mains: breaker ~68-70 above the bus, input ~77-79 beyond it; the riser holds
CTs + shorting block (load side) and fused taps, CPT, voltage-monitor relay, ATC/PM taps (line
side). S4/S5/S7 vertical buses are fed by a riser that rises from the main bus and jogs 33.23
sideways into the vertical bus at mid-height ("centre-fed"). Bus 13.0 higher on page 2.
**Proposed rules (pending approval):** main-breaker distances (15 / 30) become minimums that
grow with the devices on the riser; "centre-fed" vertical bus as an option; first 3-line frame
configurable (ES_01 can be the elevation); comms page rules (see 2026-10-19 report).
**Questions for Sammy:** see the 2026-10-19 report.

## Sabey-011484
**Files:** .dxf, .pdf  **Studied:** 2026-10-19
**Contents:** SWBD 5000A 480V 100kAIC NEMA 3R, MA-HDP-E, 6 sections (sister job of 011475,
same layout and devices): load-bank breaker on the gen main's line side, gen + utility mains
with CTs/CPT/fused taps/voltage relays/PM taps, SPD, two centre-fed group-mounted sections, a
2500A single breaker below the bus. **ES_01 = elevation, 3-line = ES_02 + ES_03**, network page
ES_11, RS-485 thermal sensors on ES_06.
**Measurements:** as 011475. S6 has both a dashed "SPACE" level (CDP_BUS_HORIZ in its HIDDEN
state, unbussed) and a solid-tap "SPACE" (bussed, = our Provision). S3|S4 divider moved to the
start of page 2 because it would hit the title block (matches our rule).
**Proposed rules (pending approval):** as 011475, plus: a "Space" (unbussed, dashed) slot next to
"Provision" (bussed).
**Questions for Sammy:** see the 2026-10-19 report.

## Sabey-011485
**Files:** .dxf, .pdf  **Studied:** 2026-10-19
**Contents:** SWBD MA-LBDP (load-bank docking panel) 5000A 480V 100kAIC Type 3R, 3 sections.
Incoming bus duct with NO main breaker (main lugs only) on a riser that passes THROUGH the main
bus (tee with dots) into breaker 52-LB-LB below, to load-bank lugs. 52-LB-GEN at the end of the
bus; its output runs into section 3 to a generator cam-lock bank (8 per phase + ground
cam-locks). Aux taps: fused tap to a power supply, 2-pole breaker to a 15kVA transformer;
receptacles, heaters, thermostat; Kirk keys / transfer blocks / SKRU; K6PM thermal sensors on
RS-485; Ethernet switch with COM190s on both breakers (ES_04).
**File problem:** the issued PDF prints the ONE-LINE (frame EO_01) as the power page and pages
3-6 are blank (layouts ES_02-05 look at empty EO frames); the real 3-line sits unprinted in
ES_01 (found by the study agent; not re-checked).
**Proposed rules (pending approval):** main-lugs-only source; riser passing through the main bus
(source above, breaker below on one riser); a feeder output running into a later section;
cam-lock termination; small 1-/2-/3-pole taps off the main bus with "TO/FROM X SECTION n" labels.
**Questions for Sammy:** see the 2026-10-19 report.
**Sammy's notes (2026-10-19):** the printed set (one-line printed, blank pages) is a mistake;
Sammy will fix the drawing.

## Sabey-011486
**Files:** .dxf, .pdf  **Studied:** 2026-10-19
**Contents:** SWBD MA-HDP/MBP-X 4000A 480V 65kAIC, Rev B, 12 sections, 17 breakers, maintenance
bypass with three bus levels joined by two vertical ties (52-MBB steps up, 52-MIB steps down),
each tie in a section of its own (MBB near the left of S6, MIB centred in S9). Gen + utility mains
with the dashed "MECHANICAL AND ELECTRICAL INTERLOCK" line between them, load-bank breaker on the
gen main's line side, UIB/UOB/CDP feeders, a single breaker above + group-mounted below in S8,
load-bank ULB. 3-line = ES_01 + ES_02; comms on ES_03 / ES_07 / ES_08. REV B triangles and clouds.
**Measurements:** tie rises 122.29 (MBB) and 64.76 (MIB), not a fixed 70. Single breakers
14.15-15.53 from the bus (matches 15). Page break label "TO SECTION 7 SHEET 3" (sheet numbers
wrong by one in this drawing).
**Proposed rules (pending approval):** ties placeable within their section (centred / own
section), step height set by what's on the next bus; UPS-bypass lineup = main bus + several ties
(3rd job: NTT-013630, IMS, this); page-break text "TO SECTION n SHEET m" generated by the program.
**Questions for Sammy:** see the 2026-10-19 report.

## Sabey-011509
**Files:** .dxf, .pdf  **Studied:** 2026-10-19
**Contents:** SWBD 600A 480V 65kAIC, MA-MPB-X (maintenance bypass), ONE section, **no horizontal
main bus**: one vertical bus with 7 levels; both mains (52-M1 top, 52-M2 bottom) are levels on it,
fed from the left (lugs facing in), with line-side voltage taps "TO FA-1/FA-2"; feeders and a
provision on the levels between. Kirk key under M2, Kirk key procedure notes box on the 3-line.
7 pages; frames named **EW_nn** (3-line = EW_01, comms = EW_04).
**Measurements:** levels pitch 25, gap 15, nearest tap 10, overhang 10 (matches our rules).
**Proposed rules (pending approval):** panelboard lineup (vertical bus only, mains as levels fed
from the side); line-side voltage tap with "TO FA-n"; Kirk key on any breaker; notes box on the
3-line page clear of the title block; frame prefix configurable (EW vs ES).
**Questions for Sammy:** see the 2026-10-19 report.

## Sabey-011510
**Files:** .dxf, .pdf  **Studied:** 2026-10-19
**Contents:** PNLB MA-MBP-E (maintenance bypass panel) 250A 480V 65kAIC, ONE section, no
horizontal main bus (same kind as 011509, in ES frames): mains M1/M2 as levels fed from the left
with "BY OTHERS" cables and CTs on the cables, Kirk keys KA/KB, 3 feeders, FA-3 fused tap off the
vertical bus to PM-1, shorting blocks. 6 pages: 3-line ES_01, control ES_02, comms ES_03.
**Measurements:** pitch 25, nearest tap 10, overhang 10 (matches). Bus foot label "A B C" +
"480VAC, 65KAIC / 3P-3W / 250A CU".
**Proposed rules (pending approval):** as 011509; bus-foot label with voltage, kAIC, phases/wires
and bus rating; accessory balloon (twin mounting kit) per level.
**Questions for Sammy:** see the 2026-10-19 report.
