# 3-Line Diagram: Parts Checklist

The 3-line page broken into small parts. Each part gets a rule (what it looks like, where it
goes, which layer/block, and the numbers). Once a part's rule is approved it moves to
`docs/DECISIONS.md` and its numbers go into config.

Status: **Approved** = rule decided. **Proposed** = drafted from the references, waiting for
Sammy. **Open** = needs a decision first. **Later** = not needed for the first master drawing.

Coordinates are frame-relative drawing units (frame drawable area 419.04 x 269.49).

## Page parts

| # | Part | Status | Rule / notes | Source |
|---|---|---|---|---|
| P1 | Page frame | Approved | 3-line goes in ES frames, page origin = frame insertion point | DECISIONS |
| P2 | Section dividers | **Built** | Layer DEVIDER, between sections only, y 8.44–256.33; end-of-page divider (next page if it would hit the title block) | Sammy's ES_01 |
| P3 | Ground bus + symbol + label | **Built** | Layer GROUND, y 20.94, x 7.54 to 8.91 before title block (last page: to end of last section); symbol at left end; "GROUND BUS" text above | Sammy's ES_01 |
| P4 | Section labels | **Built** | "SECTION n", layer 0, h 1.25, no underline, below ground bus, centred under section | Sammy's ES_01 |
| P5 | Page title | Proposed | "THREE LINE DIAGRAM 0n" bottom-right, just left of title block | all refs |
| P6 | Page break | Open | Style to pick (squiggle+bracket+A/B/C, bracket block, or none) | PRIME-014032 / 014034 |

## Bus parts

| # | Part | Status | Rule / notes | Source |
|---|---|---|---|---|
| B1 | Main bus | **Built** (preview) | Horizontal, phases 5 apart, A on top. Starts as low as possible, stays level, steps only in the section that needs it (+10 width) | DECISIONS |
| B2 | Corners and tees | Proposed | BUSSING_3PH_3W_3L. Bus end = staggered corner, no dots. Mid-bus = tee with BUS_NODE dots | all refs |
| B3 | Bus at two heights | Proposed | Joined by a vertical riser or tie breaker | NTT-013631, PRIME-014034, NTT-013630 |
| B4 | Bus end / rating label | Proposed | A/B/C letters + "nnnnA CU" at vertical bus foot; main bus run-out after last section | NTT-013627 |
| B5 | Junction dots | Proposed | BUS_NODE, dia 1.5, layer BUS | all refs |

## Source parts

| # | Part | Status | Rule / notes | Source |
|---|---|---|---|---|
| S1 | Main breaker | **Built** (real block 3P_CB_FM_1) | Input end -> bus -> breaker -> bus -> bends into the main bus at lineup start, tees in with BUS_NODE dots elsewhere; breaker 15 from the bus, input 30 beyond | DECISIONS, refs |
| S2 | Input / output block | **Built** for main breakers (PHASE_LUGS_3L_R0) | State INPUT; flipped for top-fed, as is for bottom-fed; CONN_A on the bus end. Output (feeders) and neutral come later | DECISIONS |
| S5 | Feed directions + U-turn | **Built** | Breaker Feed Direction / Termination Feed Direction (top / bottom) on main and single breakers; when they differ the bus U-turns to the right (depth 28.43, width 35) into the termination; bus-side feeding: bus U-turns over the breaker on the right, cables straight or U-turn left (warning kept); each U adds 35 to section width | NTT-013630, DECISIONS 2026-10-13 |
| S3 | Tie breaker | **Built** (placeholder size) | Vertical, at the section's right edge, any section; bus steps up/down 70 | DECISIONS |
| S4 | Main–main interlock | Approved (not built) | Always drawn: dashed line between the mains, "MECHANICAL AND ELECTRICAL INTERLOCK" | NTT-013631, Sabey-011486, DECISIONS 2026-10-19 |

## Feeder parts

| # | Part | Status | Rule / notes | Source |
|---|---|---|---|---|
| F1 | Single breaker | **Built** | Fixed-mount breaker on a riser off the main bus, up or down, with the output block (OUTPUT); editor fields for both blocks | DECISIONS 2026-10-13 |
| F2 | Group Mounted Distribution | **Built** | SIE_BKR_3P_3L_ASSY_R0 on a vertical bus; levels outward from bus, gap 15, pitch 25, overhang 10, nearest tap 10; editor fields per breaker | NTT-013627, ES_12 |
| F3 | Twin mount | Approved | Two breakers on one level, right one flipped | DECISIONS |
| F4 | Single mount | Approved | One breaker per level, alternating sides | DECISIONS |
| F5 | Mixed twin + single | Approved | Allowed on one vertical bus | DECISIONS, ES_12 |
| F6 | Combination | Approved | Above-bus and below-bus parts of a section can differ | DECISIONS |
| F7 | Provision slot | **Built** | Taps out to where a breaker would connect + note "PROVISION FOR" / engineer's line | IMS-REFERENCE, DECISIONS 2026-10-13 |
| F9 | Too-tall split | **Built** | Below part split first: column 1 cut (tilde + bracket), continues in a column beside it starting 15.5 from the bus; above split only if it alone is too tall; column pitch 103.22 | CORRECTED_FIXED_011511 ES_11, DECISIONS 2026-10-13 |
| F8 | Load-end lugs + text | Proposed | SIE_LUGS_3P_3L_R0 with wire-range text | NTT-013627, ES_12 |

## Annotation parts

| # | Part | Status | Rule / notes | Source |
|---|---|---|---|---|
| A1 | Breaker label | Later | Attributes on SIE_BKR blocks (labels being reworked by Sammy) | ES_11 |
| A2 | BOM balloon | Proposed | ITEM#_BOM_R0 above each device | all refs |

## Other devices (later)

SPD (SPD_EATON_3L_R0), CTs (3_CTS_3L_R1) + shorting block, CPT (CPT_1), fused voltage taps,
Kirk keys, "TO X SHEET n" references, neutral sensor.
