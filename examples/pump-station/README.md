# Pump station: a Fransys example

A complete design built with [Fransys](https://github.com/OleJBondahl/fransys) from real
catalogue parts: a pump cabinet, released as one unit, and the station around it. Every export Fransys produces for it is in `out/`.

**Beta**, like Fransys, until 1.0.0. Every drawing and list is also on the site:
<https://olejbondahl.github.io/fransys/examples/pump-station/>.

## The station

- A 400 V supply, a main switch, and two pumps. Each pump has a 4 A aM, 10x38 fuse, a Schneider
  LC1D09 contactor and a matching LRD08 overload relay. The main switch isolates, so the fuse
  has no switch-disconnector.
- A 24 V DC control supply and a WAGO PFC200 controller (750-82xx) with 750 digital I/O modules.
  The 0 V of the 24 V supply is GND everywhere, and the PSU's DC output lands only on the rail
  terminals.
- Two interface relays between the PLC outputs and the contactor coils: industrial 24 V DC
  PCB relays with no diode, since the PLC modules handle the coil. They are wired in the cabinet.
- Pilot lights, driven by an auxiliary contact on each contactor, and the field cables to the
  motors.
- Every part file carries its datasheet rating.

## What is here

| Path | What it holds |
|---|---|
| `build.py` | The design script. |
| `parts/` | The part library: one TOML file per catalogue part. `parts/README.md` lists each with its datasheet. |
| `parts_typed.py` | The typed parts module, made by `python -m fransys parts-module`. |
| `out/` | Every export: `all/` for the station, `cabinet/` for the cabinet unit. Each folder keeps its CSV and XML files in `data/`. |
| `releases/` | Frozen baseline of the cabinet unit. A test checks them with `fr.verify`. Stored releases restart at the 0.22 baseline: Fransys 0.22 reads no older listing (owner 2026-10-16: migration cost is no criterion). Release note: pump-cabinet 1.10 is the cabinet's first release; 1.9 and the relay board 1.4 stored listing version 5, which 0.22 no longer reads (listing_version 6), and 1.9 had a mate, a board unit and a harness line (R1216, R1253). |
| `GAPS.md` | What this Fransys release cannot yet say about the station, and the workaround used. |
| `system.md`, `cabinet.md` | The documents' cover pages. |

## Two levels in one script

`build.py` shows two ways to write a design. The easy level writes the incoming supply and the
single circuits out, one device and one wire per line. The efficient level writes the two pumps
as one `pump()` function called twice, takes their PLC channels from the `PUMPS` table, and uses
the typed parts module.

## Use it as a starting point

This folder is a project of its own, set up the way your project would use Fransys:
`pyproject.toml` pins Fransys at a release tag. Copy the folder, then:

```bash
uv sync
uv run python build.py             # rebuild out/
uv run python build.py --release   # write the unit baselines into releases/
just ci                            # lint, types and tests (needs just: https://just.systems)
```

## License

MIT, as Fransys. Part names and numbers belong to their manufacturers. The part files restate
their published datasheets.
