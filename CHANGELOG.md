# Switchboard Configurator: release history

## 2.3.0 (2026-11-12)
- New: 24 V power supply in a section's Devices box, fed by a voltage tap, drawn on the device pages with its fuse beside it
- Device pages: one page per section ("ELECTRICAL SCHEMATIC SECTION n"); every page has its title, including "THREE-LINE DIAGRAM 01"
- Wire labels on every wire on the device pages (4A001, 2+001 ...), on layer 0; the same wire keeps the same label on both sides of a jump
- Breakers by position (3WA / 3VA): comms offered by family (COM190 / COM060), and every 3WA gets its MMS automatically
- Ethernet switch: choose the section it goes in
- Ethernet switch and comms modules shown as boxes on the device pages until their blocks exist
- First 24 V wiring: one power supply per lineup feeds + and - to the comms modules and Ethernet switch
- Shipping splits: males at the ends of each section's page, females (the cables) on a SHIPPING SPLITS page at the end; wires passing through a section run straight across; a fuse feeding another section lies down and runs straight into its split
- Device names no longer include the section (PM-1, FA-12, STB-1); shipping splits keep it (5SSM-3)
- Table of contents is page 1; pages are numbered in their title blocks (01 OF 10 ...), and SHEET references and TO/FROM labels use those numbers
- Block catalog refreshed for the smaller tildes and the shipping splits
- Note: terminal blocks do not follow the new hybrid standards yet

## 2.2.1 (2026-10-26)
- New: interlocks between main breakers (mechanical, electrical or both), set in the main breaker's Interlock box and drawn between the two mains
- Scrolling the editor no longer changes drop-downs
- The Model tab shows the new drawing straight away (no REGEN needed)
- Uses the updated HYPER_A template (DEVIDER, GROUND and INTERLOCK layers)

## 2.2.0 (2026-10-23)
- New: CTs, power meters, voltage taps and device pages, with device names that include their section (PM-3-1, FA-3-12)
- Incoming feeds as their own part, plus load-bank breakers
- Single breakers can be fixed or draw-out
- Comms is now a drop-down for the module; projects saved in 2.1.0 need it picked again
- Tighter spacing and page-break fixes
- Known issue: the Schneider PM8000 is drawn as a box until its block is built

## 2.1.0 (2026-10-20)
- Drawing Information: a new page at the top of the section list for the job number (required) and the item name
- The title block fills itself on every sheet: item name, FGD 900-, and the EO-/ES-/EW- drawing numbers from the job number
- Drawings are saved under the job number, and generating again asks before replacing
- The drawing only keeps pages with something in them: legend, BOM, then the 3-line pages
- New template: the team's HYPER_A
- Comms checkbox on every breaker (for the communications page coming later)
- Known bug: page number issue

## 2.0.1 (2026-10-19)
- Updates since your last session: a pop-up that shows what changed in each new version
- SPACE: a new choice for an empty breaker position (twin or single levels), drawn with bus and the word SPACE
- AutoCAD's "not installed" message now points to the zipped installer

## 2.0.0 (2026-10-15)
First release to the team: configure switchboards (mains, single breakers, group-mounted feeders, ties, feed directions), save and open projects (.swbd), and generate the 3-line drawing in AutoCAD 2026.

