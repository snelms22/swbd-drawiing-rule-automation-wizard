# Switchboard Configurator: release history

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

