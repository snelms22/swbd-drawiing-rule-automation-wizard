# Switchboard Configurator: getting started

*Draft for Sammy to review before release 2.0.0.*

## Installing (once per PC)
1. Make sure the **CAD BLOCKS** library is synced to your PC (OneDrive), like for the
   block library.
2. Open `CAD BLOCKS\CONFIGURATORS\Switchboard Configurator\`, open
   **Install Switchboard Configurator.zip**, and run **Install Switchboard Configurator**
   inside it (you can also extract it first; it doesn't matter where it runs from).
3. You get a **Switchboard Configurator** icon on your desktop and in the Start menu.
   After restarting AutoCAD 2026, there is also a **Hyper** tab on the ribbon with a
   Switchboard Configurator button (or type `HYPERSWBD`).

Updates arrive by themselves: the app always opens the newest version. If a new version
comes out while the app is open, it offers to restart.

## Using it
- **File > New** starts a switchboard with one empty section. **File > Open from Library**
  opens a ready-made one (for example the sample) to start from.
- Build the lineup on the left (add, remove and reorder sections), and fill in each
  section's Above, Below and Tie breaker in the middle. The preview on the right and the
  warnings below update as you go.
- **File > Save** saves your project (`.swbd`) in `CONFIGURATORS\Jobs`.
- **Generate drawing** makes the AutoCAD drawing. The first time, you pick the folder your
  drawings go in (change it later with **File > Drawing Folder**). A copy of the project is
  saved next to every drawing, so any drawing can be remade.

## Good to know
- **One person edits a project at a time.** If someone else has it open, you get a
  read-only copy; use **Save As** to keep your changes under another name.
- The app uses AutoCAD 2026 (never AutoCAD Electrical). It opens AutoCAD if it isn't open.
- **Help > About** shows which version you have.
- Something not working? Tell Sammy, and mention the version from Help > About.
