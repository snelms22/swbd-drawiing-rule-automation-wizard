# Block Library Standard (draft)

How to add or change blocks in Hyper's block library so the configurator can use them.

**Library:** `Symbols-blocks.dwg` in *Hyper Document Library - Engineering / Electrical Team /
CAD BLOCKS*. The path is in `config/autocad_settings.json`. The configurator reads it in the
background and copies the block definitions it needs into each new drawing. It never opens
the library in AutoCAD's window and never changes it.

Items marked **(proposed)** still need Sammy's approval; the rest are already decided
(`docs/DECISIONS.md`).

## Rules the configurator relies on

1. **Scale 1.** Blocks are drawn at the drawings' own scale (bus phases 5 apart) and are
   always inserted at scale 1.0. Flipping (X scale -1) is allowed; text and attributes must
   still read normally after flipping.
2. **Never exploded.** The configurator never explodes or redraws a block. What is in the
   block is what appears on the drawing.
3. **One definition per block, unique name.** Use UPPERCASE with underscores, and a revision
   suffix when a block changes in a way that matters (`_R0`, `_R1`, ...), like the existing
   library.
4. **Don't rename or delete a block the configurator uses** without updating config. The
   ones in use today: `3P_CB_FM_1` (main breaker, `config/layout_settings.json`
   → `main_breaker.block`), `BUS_NODE` (junction dots, `main_bus.junction_dot_block`),
   `TITLE_BLOCK_MODEL` (page frames).
5. **Keep attribute tags and visibility state names stable.** The configurator fills
   attributes by tag (e.g. `BREAKER_NAME`) and picks visibility states by name (e.g.
   `1 BOM`). Renaming one breaks the configurator until config is updated. (Existing tags
   such as `RAITING` and `SIZE/POLLS` are spelled as they are in the library on purpose.)
6. **Dynamic blocks are welcome.** The configurator can set visibility states, flip
   states, and distance/stretch values, and fill attributes. Name the visibility parameter
   `Visibility1` (as the library does today). **(proposed)**

## Base point and connection points

7. **3-phase devices: base point on the A-phase top terminal, poles vertical, A on the
   left, B and C at +5 and +10.** This is how `3P_CB_FM_1` and `3P_CB_DO` are built.
8. **Connection markers.** Put a POINT on every terminal (where the bus attaches), on a
   non-plotting layer named `HS_CONN`. The configurator will read terminals from these
   markers instead of from measurements. In a dynamic block, include the markers in the
   actions (stretch/move/flip) so they move with the terminals. **(proposed; Sammy is
   looking into markers for his blocks. Until then terminals are measured once and stored
   in `catalog/blocks.json`)**
9. **Layers inside blocks are part of the block's design.** Each part goes on its proper
   layer: attributes on `TEXT` or `TXT`, bus bars on `BUS`, and so on. The configurator
   never changes the layers inside a block; it only chooses the layer the block itself is
   inserted on.

## Checklist when adding or changing a block

- [ ] Drawn at scale 1, units match the drawings (bus phases 5 apart).
- [ ] Unique UPPERCASE name, revision suffix if it replaces an older version.
- [ ] Base point and pole layout as in rule 7 (for 3-phase devices).
- [ ] `HS_CONN` marker POINT on each terminal (rule 8).
- [ ] Attribute tags and visibility names chosen (and not changed later).
- [ ] Library saved.
- [ ] Tell Claude, so `catalog/blocks.json` is updated and the block is checked in a
      generated drawing.
