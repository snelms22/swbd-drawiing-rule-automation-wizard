# Build Resources Index

Claude's notes on the files Sammy puts in `docs/AI_resources/` (decision 2026-11-10). That
folder holds the team's existing tools. Each tool's logic is to be taken and built into the
configurator, so it becomes one tool that integrates all of them (Sammy, 2026-11-10). The
folder is read only for Claude: its files are never edited, renamed, moved or deleted. These
notes say what each file is, what it does, and where its logic goes in the program.

Entry format:

```
## <file name>
**Added / read:** <date>
**What it is:** ...
**What it does:** ... (the logic, in plain words)
**For the program:** take its logic as is / suggest something different / information only
**Status:** pending approval / approved (DECISIONS date) / built
```

## Expected (Sammy, 2026-11-10)
- The wire label LISP (may not help: wire labels are to be discussed first).

## Files read

## NumberByLayout.lsp
**Added / read:** 2026-11-10
**What it is:** The engineers' page number routine (command `NumberByLayoutModelTag`). Loading
it also turns on `EnableAutoPage`, so it runs again after every SAVE, PLOT, PUBLISH, LAYOUT,
MVIEW, VPORTS or PAGESETUP command. `DisableAutoPage` turns that off.
**What it does:** It goes through the layout tabs in tab order and numbers them 01, 02, 03...
For each layout it takes the largest viewport that is not the sheet itself (viewport number
1), reads the model-space point that viewport looks at, and finds the nearest
`TITLE_BLOCK_MODEL` insert. The nearest insert is judged by its insertion point, the frame's
bottom-left corner. Its `PAGE` attribute gets the number. Layouts it can't match are listed
at the end.
**Checked on a generated drawing (2026-11-10, simulated on the DXF of a 014034 copy):**
- Every layout finds its own frame: TOC_ES → TOC_01, LEG_ES → LEG_01, BOM_ES → BOM_01,
  ES_n → ES_n.
- The numbers it would write are 01, 02, 03, 04, 05, 06. These match the overall sheet
  numbers the program already writes in SHEET references (ES_01 = sheet 4).
- Not yet run live (AutoCAD was in use).
- One doubt: the DXF gave viewport number 0 to every layout that had not been opened, and
  only the open one had 1, 2, 3. If live AutoCAD does the same, the LISP's "skip viewport 1"
  test could fail on tabs nobody has opened yet. The sheet's own viewport would then win as
  the largest and the wrong frame would get the number.
**For the program:** take its rule as is (number = position in tab order), but done by the
program at Generate. The program knows which frame each page is drawn in, so it doesn't need
the viewport search. The LISP keeps working on the drawing afterwards for pages added or
removed by hand, because it uses the same rule.
**Status:** approved 2026-11-10 (Sammy: "option 1"); built 2026-11-10. Settings are in
config/autocad_settings.json: `keep_layout_frames`, `page_number_attribute` and
`page_number_format`.

## 24VDC Power Supply.xlsx
**Added / read:** 2026-11-10
**What it is:** "24VDC PS SELECTION TOOL": picks a Phoenix Contact QUINT4 24 V supply for a load.
**What it does:**
- Inputs:
  - total continuous load [A], with a margin (1.25);
  - the largest total inrush (<1 s) [A], with its own margin (1.25).
- Requirements:
  - continuous = load × 1.25;
  - peak = continuous + inrush × 1.25.
- Suggests the smallest "Basic / Class 2" supply (30 W 1.25 A, 60 W 2.5 A, 90 W 3.75 A) and
  the smallest "Advanced" one (5, 10, 20, 40 A) that meet them.
- The engineer then picks a supply. The sheet looks up its:
  - part number;
  - nominal, maximum continuous and peak current;
  - input protection (LP-CC-3 up to LP-CC-15);
  - maximum recommended downstream (branch) protection;
  - matched UPS and diode;
  - input-side load = current × 24 / efficiency (0.85).
**Things found in it:**
- The Basic suggestion matches the peak requirement against the nominal currents one row
  down (D25:D27 against models A24:A26). It can suggest one size too big: 2.5 A asks for the
  90 W where the 60 W would do.
- The input-side load is labelled VA but computed as watts (no power factor).
- The maximum recommended branch protection is small:
  - 5 A supply: LP-CC-1;
  - 10 A: LP-CC-3;
  - 20 A: LP-CC-6;
  - the Class 2 supplies: N/A.
  This bears on the team's 24 V rule (each device fused at 1–6 A). A 6 A device fuse is
  above what the sheet recommends for supplies under 20 A.
**For the program:** take its logic. The supply table goes in config. The program sums the
24 V devices' current draws (from the device list the team is to build), applies the
margins, and suggests the supply. The supply's input load then feeds the CPT sizing below.
**Status:** pending approval; needs the device current draws (docket workshop).

## CPT tool 1.xlsx
**Added / read:** 2026-11-10
**What it is:** "Control Power Transformer Selection Tool": sizes the 480/240 V → 120/240 V
control power transformer and picks its protection, wiring and throwover contactor.
**What it does:**
- Inputs:
  - the configuration (one of six, e.g. "480V to 120V-1Φ-2W");
  - per load connection (1 to 3 legs): sealed VA with a margin (1.2–1.25), and inrush VA
    (<200 ms) with a margin.
- Sizing ("AB Method I", Allen-Bradley's CPT method):
  - step 2 = sealed × margin × 1.25;
  - step 5 = (inrush × margin + step 2) / 4;
  - per leg, the larger of the two;
  - overall = leg 1 + 2 × the larger of legs 2 and 3.
  - The next standard size up (150 VA to 15 kVA) is suggested. The engineer enters the size
    actually used.
- Looks up, for the size and configuration:
  - part number (9070T… / C1F…);
  - primary and secondary protection (by voltage column);
  - maximum recommended branch protection;
  - throwover contactor (switches between control power sources);
  - minimum primary and distribution wire sizes;
  - nominal currents;
  - approximate secondary fault current (VA / V / %Z).
**Things found in it:**
- The configuration row (Data!B27) is looked up in an external workbook ("[1]Data"). It
  shows the cached answer but can break when recalculated without that file.
- Column E of the calculator holds scratch sums (1010 VA sealed, 2170 VA inrush) not used
  by any result.
**For the program:** take its logic for the 120 V control power circuit. The sealed and inrush
VA would come from the 120 V devices plus the power supplies' input loads. The tables go in
config. The program suggests the size and the engineer can override it. The throwover
contactor ties in with the source priority (Customer, Critical, Generator, Utility).
**Status:** pending approval; waits for the 120 V block and the device list.
