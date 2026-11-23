# Hyper Switchboard Configurator (Rebuild)

## How to work on this project
- The owner (Sammy) makes all design decisions. Before changing architecture, layout rules,
  data structures, file layout, block handling, or UI behavior, describe the options and
  tradeoffs and WAIT for explicit approval. Small bug fixes inside an agreed design are fine,
  but explain what changed and why.
- Favor code the owner can read and fix himself: plain Python, small focused modules,
  descriptive names, comments that explain *why*. No clever tricks.
- Record every approved decision in `docs/DECISIONS.md` (date + decision + reason).
- Numbers that control layout are never hard-coded. They live in config files the owner
  can edit.
- Version history is local git only (no remote). Commit ONLY when Sammy asks.
- The legacy V4.12.2 package is reference only. Do not copy its patch-on-patch structure;
  ask before reusing any of its logic.

## Reference drawings (check at the start of every session)
- Sammy adds finished jobs to `docs/SWBD_reference/` as a `.dxf` (exact geometry) plus a
  `.pdf` with the same base name (visual check). He does not track what has been studied.
- At the start of each session, compare the files in that folder against
  `docs/SWBD_reference/INDEX.md`. For any job not yet in the index: read it, add an entry
  to INDEX.md using the format at the top of that file, and tell Sammy what was found.
- Proposed rules found in a reference stay marked "pending approval" in INDEX.md. They go
  into DECISIONS.md, config, or code only after Sammy approves them.
- Read DXF files with `ezdxf` (dev-only dependency) rather than raw text; they can be huge.

## Build resources (Sammy's files for Claude; read only)
- `docs/AI_resources/` holds the team's existing tools (LISP routines, spreadsheets, notes...).
  Its purpose: take each tool's logic and build it into this program, so the configurator
  becomes one tool that integrates all of them (Sammy, 2026-11-10). The default is to take
  the logic as is. Point out any slips found in a tool, rather than redesigning it.
- The files are for reading only: their logic or information.
- NEVER edit, rename, move, or delete anything in that folder. Claude's notes about them go in
  `docs/AI_RESOURCES_INDEX.md` (outside the folder).
- At the start of each session, compare the folder against `AI_RESOURCES_INDEX.md`; for any
  new file, read it, add an entry, and tell Sammy what it does and where its logic would go
  in the program. Where it lives in the program (config, UI, which step) is a design choice,
  so it goes into code once Sammy approves that.

## Weekly meeting updates (keep current without being asked)
- `docs/WEEKLY_UPDATES.md` is what Sammy brings to the weekly meeting (Fridays, 9 am Eastern;
  sometimes skipped, so don't assume one happened just because Friday passed). Update it whenever a
  library block is added or changed (Block Updates), a release goes out or its scope changes
  (SWBD Configurator Updates, listed by release: released since the last meeting, then
  upcoming), and when the outlook changes (Coming Up).
- Bullets are a few words each, in the format at the top of that file. When Sammy says a
  meeting happened, start a new section for the next one.

## Non-negotiable rules
- Controlled blocks (WBLOCK .dwg files) are ALWAYS inserted at scale 1.0. Never scale them.
  Flipping (X scale -1) is allowed, but text and attributes must still read normally.
- Blocks are NOT exploded. Connection points are read from marker points inside the block.
- Block geometry is authoritative. Code never redraws or reinterprets a block's contents.

## Tech stack (approved)
- Python 3.11+
- UI: PySide6
- AutoCAD output: live COM via pywin32
- Layout is computed in pure Python (no AutoCAD needed) so the preview and the drawing
  always agree. AutoCAD placement is the final step only.
