# Pump station: a Fransys example

A complete design built with [Fransys](https://github.com/OleJBondahl/fransys) from real
catalogue parts: a pump cabinet and a relay interface board, released as two units, and the
station that joins them. Every export Fransys produces for it is in `out/`.

**Beta**, like Fransys, until 1.0.0. Every drawing and list is also on the site:
<https://olejbondahl.github.io/fransys/examples/pump-station/>.

## The station

- A 400 V supply, a main switch, and two pumps, each with its fuses, contactor and overload
  relay.
- A 24 V DC control supply and a WAGO 750 PLC rack with digital inputs and outputs.
- A relay interface board between the PLC outputs and the contactor coils, nested in the cabinet
  as a unit of its own.
- Pilot lights, and the field cables to the motors.

## What is here

| Path | What it holds |
|---|---|
| `build.py` | The design script. |
| `parts/` | The part library: one TOML file per catalogue part. `parts/README.md` lists each with its datasheet. |
| `parts_typed.py` | The typed parts module, made by `python -m fransys parts-module`. |
| `out/` | Every export: `all/` for the station, `cabinet/` for the cabinet unit, `board/` for the relay board. |
| `releases/` | Frozen baselines of the two units. A test checks them with `fr.verify`. |
| `GAPS.md` | What this Fransys release cannot yet say about the station, and the workaround used. |
| `system.md`, `cabinet.md`, `relay-board.md` | The documents' cover pages. |

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
