# KiCad

Fransys writes a KiCad netlist for each board in your model. This page shows how to import it into a
KiCad 9 board, which settings to use, and how to start a part file from a KiCad symbol.

The model is the schematic. Use KiCad for the board only: no KiCad schematic file, and no
"Update PCB from Schematic". The board gets its parts and nets from the netlist, through the PCB
editor's File > Import > Netlist. The import is a manual step.

## Get the netlist

`fr.write(result, out_dir, intermediates=...)` writes one netlist per board into the
intermediates folder, named `netlist-<board>.net`. A netlist is not an export, so it never lands in `out_dir`.

`fr.check(result)` reports the KiCad findings. Read them first. An `ERROR` (`REFERENCE_DUPLICATE`,
`NET_NAME_DUPLICATE`, `PAD_ON_MULTIPLE_NETS`) means do not import yet. Each code is in findings.md.

## Import settings

Open File > Import > Netlist in the PCB editor, pick the file, and set the dialog like this.

| Setting | Choice | Why |
|---|---|---|
| Link Method | Link footprints using component tstamps (unique ids) | Each part's id comes from the model, not from its designation. A renumbered part (`R1` becomes `R7`) keeps its footprint, position and routing. |
| Delete footprints with no components in netlist | On | The model decides what is on the board. A part you remove from the model leaves the board. |
| Replace footprints with those specified in netlist | On | The footprint comes from the part file. A footprint changed by hand on the board is drift. |
| Delete/replace footprints even if locked | Off | A lock is a deliberate choice. The import reports the locked footprint, and you resolve it by hand. |
| Delete tracks shorting multiple nets | Off | It silently removes routing. Run DRC after the import and fix reported shorts by hand. |

Never switch the link method on a board that already has footprints. Footprints imported by
reference designator carry no matching ids, so a later import by id sees every part as new.

## Import steps

1. Build the project and write it, so the netlist is current.
2. Read the KiCad findings and fix every `ERROR`.
3. In the PCB editor, open File > Import > Netlist, pick the file, and set the settings above.
4. Click **Load and Test Netlist** first. It is a dry run. Read "Changes to Be Applied" and check that
   the deletions and replacements are the ones you expect. Errors must be 0.
5. Click **Update PCB**, place the new footprints, and route.
6. Run DRC. Commit the board file together with the model change that caused it.

## Footprints that only exist on the board

Mounting holes, fiducials and logos have no part in the model. Set the footprint attribute
**Not in schematic** on each one, in its footprint properties. KiCad then leaves them alone
when "Delete footprints with no components in netlist" is on.

## Parts that are not installed

A part with `installed = False` stays in the netlist and on the board, marked do-not-populate.
The BOM report leaves it out. You do not remove it from the board.

## Start a part file from a KiCad symbol

`python -m fransys_kicad <file.kicad_sym> <symbol>` reads one symbol's pins from a `.kicad_sym`
library and prints a part-file skeleton to stdout. It has one `[[function]]` of kind `generic`, with
one port per pin.

```text
uv run python -m fransys_kicad my-library.kicad_sym DEMO-RLY-2U > parts/demo-rly-2u.toml
```

Open the new file and fill in `mpn`, `manufacturer`, `description`, `category` and `class_code`
under `[part]`. Each is an empty string marked `# TODO`. Then run `fr.lint` over the library
(see parts.md). The skeleton lints clean once those five fields are filled.
