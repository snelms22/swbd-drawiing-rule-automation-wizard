I # Block Library Standard (draft)

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
   ones in use today: `3P_CB_FM_1` and `3P_CB_DO` (fixed and draw-out main breakers,
   `config/layout_settings.json` → `main_breaker.blocks`), `BUS_NODE` (junction dots,
   `main_bus.junction_dot_block`), `PHASE_LUGS_3L_R0` and `PHASE_LUGS_3L_N_R0`
   (input/output, `input_output`), `SIE_BKR_3P_3L_ASSY_R0` (group-mounted feeder breaker,
   `feeder.block`), `3P_TIDE_R0` and `BRACKET_TEXT_R0` (bus breaks, `bus_break`),
   `TITLE_BLOCK_MODEL` (page frames).
5. **Keep attribute tags and visibility state names stable.** The configurator fills
   attributes by tag (e.g. `BREAKER_NAME`) and picks visibility states by name (e.g.
   `1 BOM`). Renaming one breaks the configurator until config is updated. (Existing tags
   such as `RAITING` and `SIZE/POLLS` are spelled as they are in the library on purpose.)
6. **Dynamic blocks are welcome.** The configurator can set visibility states, flip
   states, and distance/stretch values, and fill attributes. Visibility parameters can be
   named anything: the configurator picks a state by its name (e.g. `INPUT W/ NEUTRAL`),
   so keep state names stable once a block is in use.
   **Flip parameters** are found by name: anything starting with `Flip` (AutoCAD's
   default `Flip state1`, ...) or `MIRROR` (e.g. `MIRROR-3W` on the feeder breaker); the
   configurator sets all of them together, unless config names the one to use (the
   feeder breaker has one mirror per wiring state: `feeder.mirror_parameter`, MIRROR-3W for
   3 PHASE-3 WIRE). Put the connection markers and every attribute in the flip so they
   move with it; Audit Blocks reports markers left outside the block and text that
   doesn't move. Default (not flipped) and flipped must mean
   one consistent thing per block, e.g. for `PHASE_LUGS_3L_R0`: not flipped = from/to the
   bottom, flipped = from/to the top.

## Base point and connection points

7. **3-phase devices: base point on the A-phase top terminal, poles vertical, A on the
   left, B and C at +5 and +10.** This is how `3P_CB_FM_1` and `3P_CB_DO` are built.
   Exception accepted: `PHASE_LUGS_3L_R0` has its base point at the base of the A-phase
   triangle (5 from the connection); its markers give the exact connection points.
8. **Connection markers: point parameters named by phase.** Put a dynamic-block point
   parameter on each terminal (where the bus attaches), named `CONN_A`, `CONN_B`, `CONN_C`,
   `CONN_N`. One shared set is enough when all states connect at the same spots. Include
   them in the flip/stretch actions so they move with the terminals. The configurator reads
   them into `catalog/blocks.json` for every state and flip.
   Blocks with terminals at both ends (e.g. breakers) add `_TOP` / `_BOTTOM`:
   `CONN_A_TOP`, `CONN_A_BOTTOM`, and so on. Done in `PHASE_LUGS_3L_R0`, `3P_CB_FM_1` and
   `3P_CB_DO`.
9. **Layers inside blocks are part of the block's design.** Each part goes on its proper
   layer: attributes on `TEXT` or `TXT`, bus bars on `BUS`, and so on. The configurator
   never changes the layers inside a block; it only chooses the layer the block itself is
   inserted on.

## Device blocks: 24 V and terminals (Sammy, 2026-11-13 and 2026-11-16)

10. **24 V pins on device blocks:** + and - both on the block's **left edge**, marked `24V+`
    and `24V-`: **`24V+` at the top, `24V-` at the bottom** (Sammy, 2026-11-17, for the 24 V
    ladder: + comes down from the wires along the top, - comes up from those along the
    bottom, so they never cross). Devices are tall and skinny. A pin that takes **more than one wire** (daisy-chaining)
    gets **one marker per connection, numbered**: `24V+_1`, `24V+_2`, `24V-_1` ... The second
    may sit on the right edge: the configurator works out the side from where the marker is,
    so the name only says which pin it belongs to.
11. **Points that take a wire from several directions** (the terminal block): one marker
    per direction, `<point>_<SIDE>`: `1_LEFT`, `1_TOP`, `1_BOTTOM`, `3_RIGHT` ... always with
    an underscore. The configurator reads the points and their sides from the names alone.
12. **Blocks that stack and bridge** (terminal blocks): the next block goes 5 below the one
    before (`terminal_pitch` in config). The bridge runs between `BRIDGE_TOP` and
    `BRIDGE_BOTTOM` markers; the configurator draws it as a polyline 0.5 wide on the
    `BRIDGE` layer. On fixed fuses the bridge joins their line-side connection points.
13. **Fixed fuses** (`1P_FUSE_1`, `2P_FUSE`, `3P_FUSE_1`): a connection marker on each pole's
    line side (left) and load side (right), `<pole>_LINE` / `<pole>_LOAD`: `1_LINE`, `1_LOAD`,
    `2_LINE` ... (Sammy, 2026-11-16; the names are in `config/devices.json`). Keep one tag for
    the rating across the three (today: `CURRENT`, `RATING`, `RAITING`).
14. **Ground pins** (2026-11-17): a device's ground pin is a marker named `G`, `GND` or `PE`
    (the list is `ground.pin_markers` in `config/devices.json`; the UMG 801's `DIGITAL_GND`
    is on it for now). The configurator sends it to the ground strip 1TBG by reference.
15. **Ethernet switch ports** (2026-11-19): one marker per port, `PORT_1`, `PORT_2` ...
    (`ethernet_switch.port_marker` in config), plus its 24 V per rule 10. The customer's
    connection goes on port 1. A device's Ethernet port: a marker the configurator can run a
    short stub out from without crossing anything else on the block (the UMG 801's RJ45 ports
    sit under its remote display's USB line; to fix in the block).

Blocks are never final (Sammy, 2026-11-13): any block can change to adjust the look or flow
of a drawing, or to make the configurator's rules simpler.

## Checklist when adding or changing a block

- [ ] Drawn at scale 1, units match the drawings (bus phases 5 apart).
- [ ] Unique UPPERCASE name, revision suffix if it replaces an older version.
- [ ] Base point and pole layout as in rule 7 (for 3-phase devices).
- [ ] `HS_CONN` marker POINT on each terminal (rule 8).
- [ ] Attribute tags and visibility names chosen (and not changed later).
- [ ] Every attribute the engineer may fill has a **prompt**: the prompt becomes the
      field's label in the app's editor, so no code is needed for a new block's fields.
      Give each attribute its own tag.
- [ ] Library saved.
- [ ] Click **Audit Blocks** in the app. In one click it updates `catalog/blocks.json`
      (connection markers, sizes, visibility states, attributes and prompts) and the
      app's editor fields. Then check the block in a generated drawing.
