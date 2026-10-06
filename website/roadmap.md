# Roadmap

Fransys is in beta. This page lists what comes next, in no fixed order. Each release's guide
says what changed.

## Drawings
- Cable and harness drawings, with their own layout.
- Revision marks on changed drawings, and a revision table on unit covers.
- Block diagrams of units.
- Steady work on drawing quality.

## Checks
- A check that the supply and signal levels match where two units meet.
- A list of interface changes between two revisions of a unit.
- A finding for a power input with no supply path, and for two rails joined only through
  contacts.

## Outputs
- Board fabrication files (Gerber, drill, position, BOM) through KiCad's command line.
- Document sets for one unit, with its nested units shown as black boxes.
- Items supplied by others, drawn dashed and kept off the BOM.

## Documentation
- A documentation index for coding agents.

## 1.0.0
- A stable API, kept stable across minor versions.
- A review of the packaging: PyPI, and whether stable building blocks such as the symbol
  toolkit become packages of their own.
- A lighter, cleaned-up repository.
