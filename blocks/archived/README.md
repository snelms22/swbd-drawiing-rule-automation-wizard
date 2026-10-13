Archived block files (2026-10-12). Not used by the configurator.

Blocks now come from Hyper's block library drawing `Symbols-blocks.dwg` (path in
`config/autocad_settings.json`; decision 2026-10-11, Option B). These files are kept only
for reference:
- `SCHEM_*` / `SCHEME_*`: copied unchanged from the legacy V4.12.2 MacroLibrary.
- `3P_FIXED_CIRCUIT_BREAKER.dwg`, `3P_DRAW-OUT_BREAKER.dwg`: Sammy's breaker files (each
  holds a whole drawing rather than one block, so they did not insert as dynamic blocks).
