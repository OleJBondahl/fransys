# pump-station

A complete design built with [Fransys](https://github.com/OleJBondahl/fransys) from real
catalogue parts: a pump cabinet and a relay interface board, released as two units, and the
station that joins them. Every export Fransys produces for it is in `out/`.

**Beta**, like Fransys, until 1.0.0. Every drawing and list is also on the site:
<https://olejbondahl.github.io/fransys/examples/pump-station/>.

## The station

- A 400 V supply, a main switch, and two pumps. Each pump has a 4 A aM, 10x38 fuse, a Schneider
  LC1D09 contactor and a matching LRD08 overload relay. The main switch isolates, so the fuse
  has no switch-disconnector.
- A 24 V DC control supply and a WAGO PFC200 controller (750-82xx) with 750 digital I/O modules.
  The 0 V of the 24 V supply is GND everywhere, and the PSU's DC output lands only on the rail
  terminals.
- A relay interface board between the PLC outputs and the contactor coils: industrial 24 V DC
  PCB relays with no diode, since the PLC modules handle the coil. It is nested in the cabinet as
  a unit of its own.
- Pilot lights, driven by an auxiliary contact on each contactor, and the field cables to the
  motors.
- Every part file carries its datasheet rating.

## What is here

| Path | What it holds |
|---|---|
| `build.py` | The design script. |
| `parts/` | The part library: one TOML file per catalogue part. `parts/README.md` lists each with its datasheet. |
| `parts_typed.py` | The typed parts module, made by `python -m fransys parts-module`. |
| `out/` | Every export: `all/` for the station, `cabinet/` for the cabinet unit, `board/` for the relay board. Each folder keeps its CSV and XML files in `data/`. |
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

## out/all

### EX-1-v1.3.pdf

[Download the PDF](files/all/EX-1-v1.3.pdf)

[![EX-1-v1.3, page 1](img/all/EX-1-v1.3-p01.png)](img/all/EX-1-v1.3-p01.png)

[![EX-1-v1.3, page 2](img/all/EX-1-v1.3-p02.png)](img/all/EX-1-v1.3-p02.png)

[![EX-1-v1.3, page 3](img/all/EX-1-v1.3-p03.png)](img/all/EX-1-v1.3-p03.png)

[![EX-1-v1.3, page 4](img/all/EX-1-v1.3-p04.png)](img/all/EX-1-v1.3-p04.png)

[![EX-1-v1.3, page 5](img/all/EX-1-v1.3-p05.png)](img/all/EX-1-v1.3-p05.png)

[![EX-1-v1.3, page 6](img/all/EX-1-v1.3-p06.png)](img/all/EX-1-v1.3-p06.png)

[![EX-1-v1.3, page 7](img/all/EX-1-v1.3-p07.png)](img/all/EX-1-v1.3-p07.png)

[![EX-1-v1.3, page 8](img/all/EX-1-v1.3-p08.png)](img/all/EX-1-v1.3-p08.png)

### pump-cabinet-v1.7.pdf

[Download the PDF](files/all/pump-cabinet-v1.7.pdf)

[![pump-cabinet-v1.7, page 1](img/all/pump-cabinet-v1.7-p01.png)](img/all/pump-cabinet-v1.7-p01.png)

[![pump-cabinet-v1.7, page 2](img/all/pump-cabinet-v1.7-p02.png)](img/all/pump-cabinet-v1.7-p02.png)

[![pump-cabinet-v1.7, page 3](img/all/pump-cabinet-v1.7-p03.png)](img/all/pump-cabinet-v1.7-p03.png)

[![pump-cabinet-v1.7, page 4](img/all/pump-cabinet-v1.7-p04.png)](img/all/pump-cabinet-v1.7-p04.png)

[![pump-cabinet-v1.7, page 5](img/all/pump-cabinet-v1.7-p05.png)](img/all/pump-cabinet-v1.7-p05.png)

[![pump-cabinet-v1.7, page 6](img/all/pump-cabinet-v1.7-p06.png)](img/all/pump-cabinet-v1.7-p06.png)

[![pump-cabinet-v1.7, page 7](img/all/pump-cabinet-v1.7-p07.png)](img/all/pump-cabinet-v1.7-p07.png)

[![pump-cabinet-v1.7, page 8](img/all/pump-cabinet-v1.7-p08.png)](img/all/pump-cabinet-v1.7-p08.png)

[![pump-cabinet-v1.7, page 9](img/all/pump-cabinet-v1.7-p09.png)](img/all/pump-cabinet-v1.7-p09.png)

[![pump-cabinet-v1.7, page 10](img/all/pump-cabinet-v1.7-p10.png)](img/all/pump-cabinet-v1.7-p10.png)

### relay-interface-board-v1.4.pdf

[Download the PDF](files/all/relay-interface-board-v1.4.pdf)

[![relay-interface-board-v1.4, page 1](img/all/relay-interface-board-v1.4-p01.png)](img/all/relay-interface-board-v1.4-p01.png)

[![relay-interface-board-v1.4, page 2](img/all/relay-interface-board-v1.4-p02.png)](img/all/relay-interface-board-v1.4-p02.png)

[![relay-interface-board-v1.4, page 3](img/all/relay-interface-board-v1.4-p03.png)](img/all/relay-interface-board-v1.4-p03.png)

[![relay-interface-board-v1.4, page 4](img/all/relay-interface-board-v1.4-p04.png)](img/all/relay-interface-board-v1.4-p04.png)

[![relay-interface-board-v1.4, page 5](img/all/relay-interface-board-v1.4-p05.png)](img/all/relay-interface-board-v1.4-p05.png)

- Open the overview page: [EX-1-v1.3-overview.html](files/all/EX-1-v1.3-overview.html)

## out/all/data

### EX-1-v1.3-bom.csv

[Download the CSV](files/all/data/EX-1-v1.3-bom.csv)

| mpn | revision | manufacturer | description | count | designations |
| --- | --- | --- | --- | --- | --- |
| 1119304 |  | Lapp | OELFLEX CLASSIC 110, 4G1.5 | 2 | -W11; -W21 |
| 1119405 |  | Lapp | OELFLEX CLASSIC 110, 5G2.5 | 1 | -W1 |
| 1757022 |  | Phoenix Contact | PCB connector plug, 3-pin, 5.08 mm pitch | 2 | -U1-J1; -U1-J2 |
| 1757255 |  | Phoenix Contact | PCB header, 3-pin, 5.08 mm pitch | 2 | -U1-U2-J1; -U1-U2-J2 |
| 1LE1003-0EB42-2AA4 |  | Innomotics | Induction motor, 4-pole, IE3, 400 V Y, frame 90, foot B3; 3.15 A; 1.5 kW | 2 | -M1; -M2 |
| 2002-1201 |  | WAGO | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V | 39 | -U1-X01:L1:1; -U1-X01:L1:2; -U1-X01:L1:3; -U1-X01:L1:4; -U1-X01:L2:1; -U1-X01:L2:2; -U1-X01:L2:3; -U1-X01:L2:4; -U1-X01:L3:1; -U1-X01:L3:2; -U1-X01:L3:3; -U1-X01:L3:4; -U1-X1:L1:1; -U1-X1:L2:1; -U1-X1:L3:1; -U1-X1:N:1; -U1-X2:24V:1; -U1-X2:24V:2; -U1-X2:24V:3; -U1-X2:24V:4; -U1-X2:24V:5; -U1-X2:24V:6; -U1-X2:24V:7; -U1-X2:24V:8; -U1-X2:24V:9; -U1-X2:24V:10; -U1-X2:GND:1; -U1-X2:GND:2; -U1-X2:GND:3; -U1-X2:GND:4; -U1-X2:GND:5; -U1-X2:GND:6; -U1-X2:GND:7; -U1-X3:U:1; -U1-X3:U:2; -U1-X3:V:1; -U1-X3:V:2; -U1-X3:W:1; -U1-X3:W:2 |
| 2002-1207 |  | WAGO | TOPJOB S ground terminal block, 2.5 mm2, green-yellow | 3 | -U1-X1:PE:1; -U1-X3:PE:1; -U1-X3:PE:2 |
| 21700601 |  | Lapp | EPIC DATA RJ45, Cat.6A, T568B, field-installable plug | 2 | -W3-J1; -W3-J2 |
| 2170465 |  | Lapp | ETHERLINE Cat.6A P, industrial Ethernet cable, S/FTP | 1 | -W3 |
| 3LD2054-0TK51 |  | Siemens | Switch-disconnector, 3-pole; 16 A | 1 | -U1-Q1 |
| 3NW7033 |  | Siemens | Fuse holder, 3-pole, 10x38 mm; 32 A | 2 | -U1-F11; -U1-F21 |
| 3NW8004-1 |  | Siemens | SENTRON cylindrical fuse link, 10x38 mm, aM; 4 A | 6 | -U1-F11; -U1-F21 |
| 3SU1102-6AA40-1AA0 |  | Siemens | Pilot light 22 mm, green, integrated LED 24 V AC/DC | 2 | -U1-P1; -U1-P2 |
| 40.61.9.024.1000 |  | Finder | PCB relay, 1 changeover contact, 16 A, 24 V DC coil | 2 | -U1-U2-K1; -U1-U2-K2 |
| 5SY6506-7 |  | Siemens | Miniature circuit breaker, 1P+N, curve C; 6 A | 1 | -U1-F01 |
| 750-402 |  | WAGO | 4-channel digital input module, 24 V DC | 1 | -U1-DI1 |
| 750-504 |  | WAGO | 4-channel digital output module, 24 V DC; 0.5 A | 1 | -U1-DO1 |
| 750-600 |  | WAGO | End module, terminates the internal data bus; no data contacts | 1 | -U1-E1 |
| 750-8212 |  | WAGO | PFC200 controller, 2nd generation, 2x ETHERNET, RS-232/-485 | 1 | -U1-C1 |
| LADN11 |  | Schneider Electric | TeSys D front-mount auxiliary contact block, 1 NO + 1 NC | 2 | -U1-Q11; -U1-Q21 |
| LC1D09BD |  | Schneider Electric | TeSys D contactor, 3-pole, AC-3 9 A, 1 NO + 1 NC auxiliary, 24 V DC coil | 2 | -U1-Q11; -U1-Q21 |
| LRD08 |  | Schneider Electric | TeSys thermal overload relay, class 10A, 2.5-4 A, 1 NO + 1 NC | 2 | -U1-B12; -U1-B22 |
| QUINT4-PS/1AC/24DC/2.5/SC |  | Phoenix Contact | Power supply, 1-phase, 24 V DC; 2.5 A | 1 | -U1-T1 |
| SKX-RIB-2 |  | this repo | Relay interface board, 2 channels, revision 01 | 1 | -U1-U2 |

### EX-1-v1.3-cables.csv

[Download the CSV](files/all/data/EX-1-v1.3-cables.csv)

| designation | mpn | description | core_count | gauge_mm2 | length_mm | from_label | to_label | pairs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| -W1 | 1119405 | OELFLEX CLASSIC 110, 5G2.5 | 5 | 2.5 | 10000 | -U1-X1 | +EXT-X0 |  |
| -W3 | 2170465 | ETHERLINE Cat.6A P, industrial Ethernet cable, S/FTP | 8 | 0.33 | 3000 | +EXT-W3-J1 | +EXT-W3-J2 |  |
| -W11 | 1119304 | OELFLEX CLASSIC 110, 4G1.5 | 4 | 1.5 | 15000 | -U1-X3 | +EXT-M1 |  |
| -W21 | 1119304 | OELFLEX CLASSIC 110, 4G1.5 | 4 | 1.5 | 15000 | -U1-X3 | +EXT-M2 |  |

### EX-1-v1.3-connectors-PLC-U1-U2.csv

[Download the CSV](files/all/data/EX-1-v1.3-connectors-PLC-U1-U2.csv)

| designation | style | pincount | gender | mate_designation | marking | net | mate_port_designation | ends |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| -U1-U2-J1 | mstb-header-3p | 3 | female | -U1-J1 | 1 |  | -U1-J1:1 | -U1-DO1:DO1; -U1-U2-K1:A1 |
| -U1-U2-J1 | mstb-header-3p | 3 | female | -U1-J1 | 2 |  | -U1-J1:2 | -U1-DO1:DO2; -U1-U2-K2:A1 |
| -U1-U2-J1 | mstb-header-3p | 3 | female | -U1-J1 | 3 |  | -U1-J1:3 | -U1-DO1:0V; -U1-U2-K1:A2; -U1-U2-K2:A2 |
| -U1-U2-J2 | mstb-header-3p | 3 | female | -U1-J2 | 1 |  | -U1-J2:1 | -U1-U2-K1:11; -U1-U2-K2:11; -U1-X2:24V:4 |
| -U1-U2-J2 | mstb-header-3p | 3 | female | -U1-J2 | 2 |  | -U1-J2:2 | -U1-B12:95; -U1-U2-K1:14 |
| -U1-U2-J2 | mstb-header-3p | 3 | female | -U1-J2 | 3 |  | -U1-J2:3 | -U1-B22:95; -U1-U2-K2:14 |

### EX-1-v1.3-cores.csv

[Download the CSV](files/all/data/EX-1-v1.3-cores.csv)

| cable | core | colour | pair | end_a | end_b | note |
| --- | --- | --- | --- | --- | --- | --- |
| -W1 | 1 | BK1 |  | -U1-X1:L1:1 | -X0:L1:1 |  |
| -W1 | 2 | BK2 |  | -U1-X1:L2:1 | -X0:L2:1 |  |
| -W1 | 3 | BK3 |  | -U1-X1:L3:1 | -X0:L3:1 |  |
| -W1 | 4 | BK4 |  | -U1-X1:N:1 | -X0:N:1 |  |
| -W1 | 5 | GNYE |  | -U1-X1:PE:1 | -X0:PE:1 |  |
| -W3 | 1 | WHOG |  | -W3-J1:1 | -W3-J2:1 |  |
| -W3 | 2 | OG |  | -W3-J1:2 | -W3-J2:2 |  |
| -W3 | 3 | WHGN |  | -W3-J1:3 | -W3-J2:3 |  |
| -W3 | 4 | BU |  | -W3-J1:4 | -W3-J2:4 |  |
| -W3 | 5 | WHBU |  | -W3-J1:5 | -W3-J2:5 |  |
| -W3 | 6 | GN |  | -W3-J1:6 | -W3-J2:6 |  |
| -W3 | 7 | WHBN |  | -W3-J1:7 | -W3-J2:7 |  |
| -W3 | 8 | BN |  | -W3-J1:8 | -W3-J2:8 |  |
| -W11 | 1 | BK1 |  | -U1-X3:U:1 | -M1:U1 |  |
| -W11 | 2 | BK2 |  | -U1-X3:V:1 | -M1:V1 |  |
| -W11 | 3 | BK3 |  | -U1-X3:W:1 | -M1:W1 |  |
| -W11 | 4 | GNYE |  | -U1-X3:PE:1 | -M1:PE |  |
| -W21 | 1 | BK1 |  | -U1-X3:U:2 | -M2:U1 |  |
| -W21 | 2 | BK2 |  | -U1-X3:V:2 | -M2:V1 |  |
| -W21 | 3 | BK3 |  | -U1-X3:W:2 | -M2:W1 |  |
| -W21 | 4 | GNYE |  | -U1-X3:PE:2 | -M2:PE |  |

### EX-1-v1.3-designations.csv

[Download the CSV](files/all/data/EX-1-v1.3-designations.csv)

| designation | reference | description |
| --- | --- | --- |
| -K1 | =PLC+EXT-K1 | Unmanaged Ethernet switch, 5x RJ45, DIN rail |
| -M1 | =P1+EXT-M1 | Induction motor, 4-pole, IE3, 400 V Y, frame 90, foot B3; 3.15 A; 1.5 kW |
| -M2 | =P2+EXT-M2 | Induction motor, 4-pole, IE3, 400 V Y, frame 90, foot B3; 3.15 A; 1.5 kW |
| -U1-B12 | =P1-U1-B12 | TeSys thermal overload relay, class 10A, 2.5-4 A, 1 NO + 1 NC |
| -U1-B22 | =P2-U1-B22 | TeSys thermal overload relay, class 10A, 2.5-4 A, 1 NO + 1 NC |
| -U1-C1 | =PLC-U1-C1 | PFC200 controller, 2nd generation, 2x ETHERNET, RS-232/-485 |
| -U1-DI1 | =PLC-U1-DI1 | 4-channel digital input module, 24 V DC |
| -U1-DO1 | =PLC-U1-DO1 | 4-channel digital output module, 24 V DC; 0.5 A |
| -U1-E1 | =PLC-U1-E1 | End module, terminates the internal data bus; no data contacts |
| -U1-F01 | =CTL-U1-F01 | Miniature circuit breaker, 1P+N, curve C; 6 A |
| -U1-F11 | =P1-U1-F11 | Fuse holder, 3-pole, 10x38 mm; 32 A |
| -U1-F21 | =P2-U1-F21 | Fuse holder, 3-pole, 10x38 mm; 32 A |
| -U1-J1 | =PLC-U1-J1 | PCB connector plug, 3-pin, 5.08 mm pitch |
| -U1-J2 | =PLC-U1-J2 | PCB connector plug, 3-pin, 5.08 mm pitch |
| -U1-P1 | =P1-U1-P1 | Pilot light 22 mm, green, integrated LED 24 V AC/DC |
| -U1-P2 | =P2-U1-P2 | Pilot light 22 mm, green, integrated LED 24 V AC/DC |
| -U1-Q1 | =SUP-U1-Q1 | Switch-disconnector, 3-pole; 16 A |
| -U1-Q11 | =P1-U1-Q11 | TeSys D contactor, 3-pole, AC-3 9 A, 1 NO + 1 NC auxiliary, 24 V DC coil |
| -U1-Q21 | =P2-U1-Q21 | TeSys D contactor, 3-pole, AC-3 9 A, 1 NO + 1 NC auxiliary, 24 V DC coil |
| -U1-T1 | =CTL-U1-T1 | Power supply, 1-phase, 24 V DC; 2.5 A |
| -U1-U1 | =PLC-U1-U1 |  |
| -U1-U2 | =PLC-U1-U2 | Relay interface board, 2 channels, revision 01 |
| -U1-U2-J1 | =PLC-U1-U2-J1 | PCB header, 3-pin, 5.08 mm pitch |
| -U1-U2-J2 | =PLC-U1-U2-J2 | PCB header, 3-pin, 5.08 mm pitch |
| -U1-U2-K1 | =PLC-U1-U2-K1 | PCB relay, 1 changeover contact, 16 A, 24 V DC coil |
| -U1-U2-K2 | =PLC-U1-U2-K2 | PCB relay, 1 changeover contact, 16 A, 24 V DC coil |
| -U1-X01 | -U1-X01 |  |
| -U1-X1 | -U1-X1 |  |
| -U1-X01:L1:1 | =SUP-U1-X01:L1:1 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X1:L1:1 | =SUP-U1-X1:L1:1 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X01:L1:2 | =SUP-U1-X01:L1:2 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X01:L1:3 | =SUP-U1-X01:L1:3 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X01:L1:4 | =SUP-U1-X01:L1:4 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X01:L2:1 | =SUP-U1-X01:L2:1 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X1:L2:1 | =SUP-U1-X1:L2:1 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X01:L2:2 | =SUP-U1-X01:L2:2 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X01:L2:3 | =SUP-U1-X01:L2:3 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X01:L2:4 | =SUP-U1-X01:L2:4 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X01:L3:1 | =SUP-U1-X01:L3:1 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X1:L3:1 | =SUP-U1-X1:L3:1 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X01:L3:2 | =SUP-U1-X01:L3:2 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X01:L3:3 | =SUP-U1-X01:L3:3 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X01:L3:4 | =SUP-U1-X01:L3:4 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X1:N:1 | =SUP-U1-X1:N:1 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X1:PE:1 | =SUP-U1-X1:PE:1 | TOPJOB S ground terminal block, 2.5 mm2, green-yellow |
| -U1-X2 | -U1-X2 |  |
| -U1-X2:24V:1 | =CTL-U1-X2:24V:1 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X2:24V:2 | =CTL-U1-X2:24V:2 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X2:24V:3 | =CTL-U1-X2:24V:3 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X2:24V:4 | =CTL-U1-X2:24V:4 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X2:24V:5 | =CTL-U1-X2:24V:5 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X2:24V:6 | =CTL-U1-X2:24V:6 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X2:24V:7 | =CTL-U1-X2:24V:7 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X2:24V:8 | =CTL-U1-X2:24V:8 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X2:24V:9 | =CTL-U1-X2:24V:9 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X2:24V:10 | =CTL-U1-X2:24V:10 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X2:GND:1 | =CTL-U1-X2:GND:1 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X2:GND:2 | =CTL-U1-X2:GND:2 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X2:GND:3 | =CTL-U1-X2:GND:3 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X2:GND:4 | =CTL-U1-X2:GND:4 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X2:GND:5 | =CTL-U1-X2:GND:5 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X2:GND:6 | =CTL-U1-X2:GND:6 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X2:GND:7 | =CTL-U1-X2:GND:7 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X3 | -U1-X3 |  |
| -U1-X3:PE:1 | =P1-U1-X3:PE:1 | TOPJOB S ground terminal block, 2.5 mm2, green-yellow |
| -U1-X3:PE:2 | =P2-U1-X3:PE:2 | TOPJOB S ground terminal block, 2.5 mm2, green-yellow |
| -U1-X3:U:1 | =P1-U1-X3:U:1 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X3:U:2 | =P2-U1-X3:U:2 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X3:V:1 | =P1-U1-X3:V:1 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X3:V:2 | =P2-U1-X3:V:2 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X3:W:1 | =P1-U1-X3:W:1 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -U1-X3:W:2 | =P2-U1-X3:W:2 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -W1 | =SUP+EXT-W1 | OELFLEX CLASSIC 110, 5G2.5 |
| -W3 | =PLC+EXT-W3 |  |
| -W3 | =PLC+EXT-W3 | ETHERLINE Cat.6A P, industrial Ethernet cable, S/FTP |
| -W3-J1 | =PLC+EXT-W3-J1 | EPIC DATA RJ45, Cat.6A, T568B, field-installable plug |
| -W3-J2 | =PLC+EXT-W3-J2 | EPIC DATA RJ45, Cat.6A, T568B, field-installable plug |
| -W11 | =P1+EXT-W11 | OELFLEX CLASSIC 110, 4G1.5 |
| -W21 | =P2+EXT-W21 | OELFLEX CLASSIC 110, 4G1.5 |
| -X0 | +EXT-X0 |  |
| -X0:L1:1 | =SUP+EXT-X0:L1:1 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X0:L2:1 | =SUP+EXT-X0:L2:1 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X0:L3:1 | =SUP+EXT-X0:L3:1 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X0:N:1 | =SUP+EXT-X0:N:1 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X0:PE:1 | =SUP+EXT-X0:PE:1 | TOPJOB S ground terminal block, 2.5 mm2, green-yellow |

### EX-1-v1.3-plc.csv

[Download the CSV](files/all/data/EX-1-v1.3-plc.csv)

| pin | channel_name | signal | signal_name | wired_to |
| --- | --- | --- | --- | --- |
| -U1-DI1:DI1 | 1 | di | P1_OVERLOAD | -U1-B12:98 |
| -U1-DI1:DI2 | 2 | di | P1_RUNNING | -U1-Q11:14 |
| -U1-DI1:DI3 | 3 | di | P2_OVERLOAD | -U1-B22:98 |
| -U1-DI1:DI4 | 4 | di | P2_RUNNING | -U1-Q21:14 |
| -U1-DO1:DO1 | 1 | do | P1_RUN | -U1-J1:1 |
| -U1-DO1:DO2 | 2 | do | P2_RUN | -U1-J1:2 |
| -U1-DO1:DO3 | 3 | do |  |  |
| -U1-DO1:DO4 | 4 | do |  |  |

### EX-1-v1.3-terminals-EXT-X0.csv

[Download the CSV](files/all/data/EX-1-v1.3-terminals-EXT-X0.csv)

| designation | group | index | side_a | side_b | jumper_group |
| --- | --- | --- | --- | --- | --- |
| -X0:L1:1 | L1 | 1 |  | -U1-X1:L1:1 |  |
| -X0:L2:1 | L2 | 1 |  | -U1-X1:L2:1 |  |
| -X0:L3:1 | L3 | 1 |  | -U1-X1:L3:1 |  |
| -X0:N:1 | N | 1 |  | -U1-X1:N:1 |  |
| -X0:PE:1 | PE | 1 |  | -U1-X1:PE:1 |  |

### EX-1-v1.3-terminals-U1-X01.csv

[Download the CSV](files/all/data/EX-1-v1.3-terminals-U1-X01.csv)

| designation | group | index | side_a | side_b | jumper_group |
| --- | --- | --- | --- | --- | --- |
| -U1-X01:L1:1 | L1 | 1 | -U1-Q1:2T1; -U1-X01:L1:2 |  | 1 |
| -U1-X01:L1:2 | L1 | 2 | -U1-F01:1; -U1-X01:L1:1; -U1-X01:L1:3 |  | 1 |
| -U1-X01:L1:3 | L1 | 3 | -U1-F11:1; -U1-X01:L1:2; -U1-X01:L1:4 |  | 1 |
| -U1-X01:L1:4 | L1 | 4 | -U1-F21:1; -U1-X01:L1:3 |  | 1 |
| -U1-X01:L2:1 | L2 | 1 | -U1-Q1:4T2; -U1-X01:L2:2 |  | 2 |
| -U1-X01:L2:2 | L2 | 2 | -U1-X01:L2:1; -U1-X01:L2:3 |  | 2 |
| -U1-X01:L2:3 | L2 | 3 | -U1-F11:3; -U1-X01:L2:2; -U1-X01:L2:4 |  | 2 |
| -U1-X01:L2:4 | L2 | 4 | -U1-F21:3; -U1-X01:L2:3 |  | 2 |
| -U1-X01:L3:1 | L3 | 1 | -U1-Q1:6T3; -U1-X01:L3:2 |  | 3 |
| -U1-X01:L3:2 | L3 | 2 | -U1-X01:L3:1; -U1-X01:L3:3 |  | 3 |
| -U1-X01:L3:3 | L3 | 3 | -U1-F11:5; -U1-X01:L3:2; -U1-X01:L3:4 |  | 3 |
| -U1-X01:L3:4 | L3 | 4 | -U1-F21:5; -U1-X01:L3:3 |  | 3 |

### EX-1-v1.3-terminals-U1-X1.csv

[Download the CSV](files/all/data/EX-1-v1.3-terminals-U1-X1.csv)

| designation | group | index | side_a | side_b | jumper_group |
| --- | --- | --- | --- | --- | --- |
| -U1-X1:L1:1 | L1 | 1 | -U1-Q1:1L1 | +EXT-X0:L1:1 |  |
| -U1-X1:L2:1 | L2 | 1 | -U1-Q1:3L2 | +EXT-X0:L2:1 |  |
| -U1-X1:L3:1 | L3 | 1 | -U1-Q1:5L3 | +EXT-X0:L3:1 |  |
| -U1-X1:N:1 | N | 1 | -U1-F01:3 N | +EXT-X0:N:1 |  |
| -U1-X1:PE:1 | PE | 1 | -U1-X3:PE:1; -U1-X3:PE:2 | +EXT-X0:PE:1 |  |

### EX-1-v1.3-terminals-U1-X2.csv

[Download the CSV](files/all/data/EX-1-v1.3-terminals-U1-X2.csv)

| designation | group | index | side_a | side_b | jumper_group |
| --- | --- | --- | --- | --- | --- |
| -U1-X2:24V:1 | 24V | 1 | -U1-T1:+; -U1-X2:24V:2 |  | 1 |
| -U1-X2:24V:2 | 24V | 2 | -U1-C1:24 V; -U1-X2:24V:1; -U1-X2:24V:3 |  | 1 |
| -U1-X2:24V:3 | 24V | 3 | -U1-C1:+; -U1-X2:24V:2; -U1-X2:24V:4 |  | 1 |
| -U1-X2:24V:4 | 24V | 4 | -U1-J2:1; -U1-X2:24V:3; -U1-X2:24V:5 |  | 1 |
| -U1-X2:24V:5 | 24V | 5 | -U1-Q11:53/NO; -U1-X2:24V:4; -U1-X2:24V:6 |  | 1 |
| -U1-X2:24V:6 | 24V | 6 | -U1-B12:97; -U1-X2:24V:5; -U1-X2:24V:7 |  | 1 |
| -U1-X2:24V:7 | 24V | 7 | -U1-Q11:13/NO; -U1-X2:24V:6; -U1-X2:24V:8 |  | 1 |
| -U1-X2:24V:8 | 24V | 8 | -U1-Q21:53/NO; -U1-X2:24V:7; -U1-X2:24V:9 |  | 1 |
| -U1-X2:24V:9 | 24V | 9 | -U1-B22:97; -U1-X2:24V:8; -U1-X2:24V:10 |  | 1 |
| -U1-X2:24V:10 | 24V | 10 | -U1-Q21:13/NO; -U1-X2:24V:9 |  | 1 |
| -U1-X2:GND:1 | GND | 1 | -U1-T1:-; -U1-X2:GND:2 |  | 2 |
| -U1-X2:GND:2 | GND | 2 | -U1-C1:0V; -U1-X2:GND:1; -U1-X2:GND:3 |  | 2 |
| -U1-X2:GND:3 | GND | 3 | -U1-C1:-; -U1-X2:GND:2; -U1-X2:GND:4 |  | 2 |
| -U1-X2:GND:4 | GND | 4 | -U1-Q11:A2; -U1-X2:GND:3; -U1-X2:GND:5 |  | 2 |
| -U1-X2:GND:5 | GND | 5 | -U1-P1:X2; -U1-X2:GND:4; -U1-X2:GND:6 |  | 2 |
| -U1-X2:GND:6 | GND | 6 | -U1-Q21:A2; -U1-X2:GND:5; -U1-X2:GND:7 |  | 2 |
| -U1-X2:GND:7 | GND | 7 | -U1-P2:X2; -U1-X2:GND:6 |  | 2 |

### EX-1-v1.3-terminals-U1-X3.csv

[Download the CSV](files/all/data/EX-1-v1.3-terminals-U1-X3.csv)

| designation | group | index | side_a | side_b | jumper_group |
| --- | --- | --- | --- | --- | --- |
| -U1-X3:PE:1 | PE | 1 | -U1-X1:PE:1 | +EXT-M1:PE |  |
| -U1-X3:PE:2 | PE | 2 | -U1-X1:PE:1 | +EXT-M2:PE |  |
| -U1-X3:U:1 | U | 1 | -U1-B12:2/T1 | +EXT-M1:U1 |  |
| -U1-X3:U:2 | U | 2 | -U1-B22:2/T1 | +EXT-M2:U1 |  |
| -U1-X3:V:1 | V | 1 | -U1-B12:4/T2 | +EXT-M1:V1 |  |
| -U1-X3:V:2 | V | 2 | -U1-B22:4/T2 | +EXT-M2:V1 |  |
| -U1-X3:W:1 | W | 1 | -U1-B12:6/T3 | +EXT-M1:W1 |  |
| -U1-X3:W:2 | W | 2 | -U1-B22:6/T3 | +EXT-M2:W1 |  |

### EX-1-v1.3-wires.csv

[Download the CSV](files/all/data/EX-1-v1.3-wires.csv)

| from | to | colour | cross_section_mm2 | label |
| --- | --- | --- | --- | --- |
| -U1-B12:95 | -U1-J2:2 | WH | 1.5 | -U1-B12:95 -U1-J2:2 |
| -U1-B12:96 | -U1-Q11:A1 | WH | 1.5 | -U1-B12:96 -U1-Q11:A1 |
| -U1-B12:98 | -U1-DI1:DI1 | WH | 1.5 | -U1-B12:98 -U1-DI1:DI1 |
| -U1-B22:95 | -U1-J2:3 | WH | 1.5 | -U1-B22:95 -U1-J2:3 |
| -U1-B22:96 | -U1-Q21:A1 | WH | 1.5 | -U1-B22:96 -U1-Q21:A1 |
| -U1-B22:98 | -U1-DI1:DI3 | WH | 1.5 | -U1-B22:98 -U1-DI1:DI3 |
| -U1-DI1:DI2 | -U1-Q11:14 | WH | 1.5 | -U1-DI1:DI2 -U1-Q11:14 |
| -U1-DI1:DI4 | -U1-Q21:14 | WH | 1.5 | -U1-DI1:DI4 -U1-Q21:14 |
| -U1-DO1:0V | -U1-J1:3 | WH | 0.5 | -U1-DO1:0V -U1-J1:3 |
| -U1-DO1:DO1 | -U1-J1:1 | WH | 0.5 | -U1-DO1:DO1 -U1-J1:1 |
| -U1-DO1:DO2 | -U1-J1:2 | WH | 0.5 | -U1-DO1:DO2 -U1-J1:2 |
| -U1-F01:2 | -U1-T1:L/+ | BN | 1.5 | -U1-F01:2 -U1-T1:L/+ |
| -U1-F01:N 4 | -U1-T1:N/- | BU | 1.5 | -U1-F01:N 4 -U1-T1:N/- |
| -U1-F11:2 | -U1-Q11:1/L1 | BN | 1.5 | -U1-F11:2 -U1-Q11:1/L1 |
| -U1-F11:4 | -U1-Q11:3/L2 | BK | 1.5 | -U1-F11:4 -U1-Q11:3/L2 |
| -U1-F11:6 | -U1-Q11:5/L3 | GY | 1.5 | -U1-F11:6 -U1-Q11:5/L3 |
| -U1-F21:2 | -U1-Q21:1/L1 | BN | 1.5 | -U1-F21:2 -U1-Q21:1/L1 |
| -U1-F21:4 | -U1-Q21:3/L2 | BK | 1.5 | -U1-F21:4 -U1-Q21:3/L2 |
| -U1-F21:6 | -U1-Q21:5/L3 | GY | 1.5 | -U1-F21:6 -U1-Q21:5/L3 |
| -U1-P1:X1 | -U1-Q11:54 | WH | 1.5 | -U1-P1:X1 -U1-Q11:54 |
| -U1-P2:X1 | -U1-Q21:54 | WH | 1.5 | -U1-P2:X1 -U1-Q21:54 |
| -U1-U2-J1:1 | -U1-U2-K1:A1 | WH | 0.5 | -U1-U2-J1:1 -U1-U2-K1:A1 |
| -U1-U2-J1:2 | -U1-U2-K2:A1 | WH | 0.5 | -U1-U2-J1:2 -U1-U2-K2:A1 |
| -U1-U2-J1:3 | -U1-U2-K1:A2 | WH | 0.5 | -U1-U2-J1:3 -U1-U2-K1:A2 |
| -U1-U2-J1:3 | -U1-U2-K2:A2 | WH | 0.5 | -U1-U2-J1:3 -U1-U2-K2:A2 |
| -U1-U2-J2:1 | -U1-U2-K1:11 | WH | 0.5 | -U1-U2-J2:1 -U1-U2-K1:11 |
| -U1-U2-J2:1 | -U1-U2-K2:11 | WH | 0.5 | -U1-U2-J2:1 -U1-U2-K2:11 |
| -U1-U2-J2:2 | -U1-U2-K1:14 | WH | 0.5 | -U1-U2-J2:2 -U1-U2-K1:14 |
| -U1-U2-J2:3 | -U1-U2-K2:14 | WH | 0.5 | -U1-U2-J2:3 -U1-U2-K2:14 |
| -U1-X01:L1:1 | -U1-Q1:2T1 | BN | 2.5 | -U1-X01:L1:1 -U1-Q1:2T1 |
| -U1-X1:L1:1 | -U1-Q1:1L1 | BN | 2.5 | -U1-X1:L1:1 -U1-Q1:1L1 |
| -U1-X01:L1:2 | -U1-F01:1 | BN | 1.5 | -U1-X01:L1:2 -U1-F01:1 |
| -U1-X01:L1:3 | -U1-F11:1 | BN | 1.5 | -U1-X01:L1:3 -U1-F11:1 |
| -U1-X01:L1:4 | -U1-F21:1 | BN | 1.5 | -U1-X01:L1:4 -U1-F21:1 |
| -U1-X01:L2:1 | -U1-Q1:4T2 | BK | 2.5 | -U1-X01:L2:1 -U1-Q1:4T2 |
| -U1-X1:L2:1 | -U1-Q1:3L2 | BK | 2.5 | -U1-X1:L2:1 -U1-Q1:3L2 |
| -U1-X01:L2:3 | -U1-F11:3 | BK | 1.5 | -U1-X01:L2:3 -U1-F11:3 |
| -U1-X01:L2:4 | -U1-F21:3 | BK | 1.5 | -U1-X01:L2:4 -U1-F21:3 |
| -U1-X01:L3:1 | -U1-Q1:6T3 | GY | 2.5 | -U1-X01:L3:1 -U1-Q1:6T3 |
| -U1-X1:L3:1 | -U1-Q1:5L3 | GY | 2.5 | -U1-X1:L3:1 -U1-Q1:5L3 |
| -U1-X01:L3:3 | -U1-F11:5 | GY | 1.5 | -U1-X01:L3:3 -U1-F11:5 |
| -U1-X01:L3:4 | -U1-F21:5 | GY | 1.5 | -U1-X01:L3:4 -U1-F21:5 |
| -U1-X1:N:1 | -U1-F01:3 N | BU | 1.5 | -U1-X1:N:1 -U1-F01:3 N |
| -U1-X2:24V:1 | -U1-T1:+ | RD | 1.5 | -U1-X2:24V:1 -U1-T1:+ |
| -U1-X2:24V:2 | -U1-C1:24 V | RD | 1.5 | -U1-X2:24V:2 -U1-C1:24 V |
| -U1-X2:24V:3 | -U1-C1:+ | RD | 1.5 | -U1-X2:24V:3 -U1-C1:+ |
| -U1-X2:24V:4 | -U1-J2:1 | RD | 0.5 | -U1-X2:24V:4 -U1-J2:1 |
| -U1-X2:24V:5 | -U1-Q11:53/NO | RD | 1.5 | -U1-X2:24V:5 -U1-Q11:53/NO |
| -U1-X2:24V:6 | -U1-B12:97 | RD | 1.5 | -U1-X2:24V:6 -U1-B12:97 |
| -U1-X2:24V:7 | -U1-Q11:13/NO | RD | 1.5 | -U1-X2:24V:7 -U1-Q11:13/NO |
| -U1-X2:24V:8 | -U1-Q21:53/NO | RD | 1.5 | -U1-X2:24V:8 -U1-Q21:53/NO |
| -U1-X2:24V:9 | -U1-B22:97 | RD | 1.5 | -U1-X2:24V:9 -U1-B22:97 |
| -U1-X2:24V:10 | -U1-Q21:13/NO | RD | 1.5 | -U1-X2:24V:10 -U1-Q21:13/NO |
| -U1-X2:GND:1 | -U1-T1:- | BK | 1.5 | -U1-X2:GND:1 -U1-T1:- |
| -U1-X2:GND:2 | -U1-C1:0V | BK | 1.5 | -U1-X2:GND:2 -U1-C1:0V |
| -U1-X2:GND:3 | -U1-C1:- | BK | 1.5 | -U1-X2:GND:3 -U1-C1:- |
| -U1-X2:GND:4 | -U1-Q11:A2 | BK | 1.5 | -U1-X2:GND:4 -U1-Q11:A2 |
| -U1-X2:GND:5 | -U1-P1:X2 | BK | 1.5 | -U1-X2:GND:5 -U1-P1:X2 |
| -U1-X2:GND:6 | -U1-Q21:A2 | BK | 1.5 | -U1-X2:GND:6 -U1-Q21:A2 |
| -U1-X2:GND:7 | -U1-P2:X2 | BK | 1.5 | -U1-X2:GND:7 -U1-P2:X2 |
| -U1-X3:U:1 | -U1-B12:2/T1 | BN | 1.5 | -U1-X3:U:1 -U1-B12:2/T1 |
| -U1-X3:U:2 | -U1-B22:2/T1 | BN | 1.5 | -U1-X3:U:2 -U1-B22:2/T1 |
| -U1-X3:V:1 | -U1-B12:4/T2 | BK | 1.5 | -U1-X3:V:1 -U1-B12:4/T2 |
| -U1-X3:V:2 | -U1-B22:4/T2 | BK | 1.5 | -U1-X3:V:2 -U1-B22:4/T2 |
| -U1-X3:W:1 | -U1-B12:6/T3 | GY | 1.5 | -U1-X3:W:1 -U1-B12:6/T3 |
| -U1-X3:W:2 | -U1-B22:6/T3 | GY | 1.5 | -U1-X3:W:2 -U1-B22:6/T3 |

- Download: [EX-1-v1.3-wago-PLC-U1-U1.xml](files/all/data/EX-1-v1.3-wago-PLC-U1-U1.xml)

## out/board/data

### relay-interface-board-v1.4-bom.csv

[Download the CSV](files/board/data/relay-interface-board-v1.4-bom.csv)

| mpn | revision | manufacturer | description | count | designations |
| --- | --- | --- | --- | --- | --- |
| 1757255 |  | Phoenix Contact | PCB header, 3-pin, 5.08 mm pitch | 2 | -J1; -J2 |
| 40.61.9.024.1000 |  | Finder | PCB relay, 1 changeover contact, 16 A, 24 V DC coil | 2 | -K1; -K2 |
| SKX-RIB-2 |  | this repo | Relay interface board, 2 channels, revision 01 | 1 |  |

### relay-interface-board-v1.4-cables.csv

[Download the CSV](files/board/data/relay-interface-board-v1.4-cables.csv)

| designation | mpn | description | core_count | gauge_mm2 | length_mm | from_label | to_label | pairs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

### relay-interface-board-v1.4-connectors.csv

[Download the CSV](files/board/data/relay-interface-board-v1.4-connectors.csv)

| designation | style | pincount | gender | mate_designation | marking | net | mate_port_designation | ends |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| -J1 | mstb-header-3p | 3 | female |  | 1 |  |  | -K1:A1 |
| -J1 | mstb-header-3p | 3 | female |  | 2 |  |  | -K2:A1 |
| -J1 | mstb-header-3p | 3 | female |  | 3 |  |  | -K1:A2; -K2:A2 |
| -J2 | mstb-header-3p | 3 | female |  | 1 |  |  | -K1:11; -K2:11 |
| -J2 | mstb-header-3p | 3 | female |  | 2 |  |  | -K1:14 |
| -J2 | mstb-header-3p | 3 | female |  | 3 |  |  | -K2:14 |

### relay-interface-board-v1.4-cores.csv

[Download the CSV](files/board/data/relay-interface-board-v1.4-cores.csv)

| cable | core | colour | pair | end_a | end_b | note |
| --- | --- | --- | --- | --- | --- | --- |

### relay-interface-board-v1.4-designations.csv

[Download the CSV](files/board/data/relay-interface-board-v1.4-designations.csv)

| designation | reference | description |
| --- | --- | --- |
| -J1 | -J1 | PCB header, 3-pin, 5.08 mm pitch |
| -J2 | -J2 | PCB header, 3-pin, 5.08 mm pitch |
| -K1 | -K1 | PCB relay, 1 changeover contact, 16 A, 24 V DC coil |
| -K2 | -K2 | PCB relay, 1 changeover contact, 16 A, 24 V DC coil |

### relay-interface-board-v1.4-plc.csv

[Download the CSV](files/board/data/relay-interface-board-v1.4-plc.csv)

| pin | channel_name | signal | signal_name | wired_to |
| --- | --- | --- | --- | --- |

### relay-interface-board-v1.4-wires.csv

[Download the CSV](files/board/data/relay-interface-board-v1.4-wires.csv)

| from | to | colour | cross_section_mm2 | label |
| --- | --- | --- | --- | --- |
| -J1:1 | -K1:A1 | WH | 0.5 | -J1:1 -K1:A1 |
| -J1:2 | -K2:A1 | WH | 0.5 | -J1:2 -K2:A1 |
| -J1:3 | -K1:A2 | WH | 0.5 | -J1:3 -K1:A2 |
| -J1:3 | -K2:A2 | WH | 0.5 | -J1:3 -K2:A2 |
| -J2:1 | -K1:11 | WH | 0.5 | -J2:1 -K1:11 |
| -J2:1 | -K2:11 | WH | 0.5 | -J2:1 -K2:11 |
| -J2:2 | -K1:14 | WH | 0.5 | -J2:2 -K1:14 |
| -J2:3 | -K2:14 | WH | 0.5 | -J2:3 -K2:14 |

## out/board

### relay-interface-board-v1.4.pdf

[Download the PDF](files/board/relay-interface-board-v1.4.pdf)

[![relay-interface-board-v1.4, page 1](img/board/relay-interface-board-v1.4-p01.png)](img/board/relay-interface-board-v1.4-p01.png)

[![relay-interface-board-v1.4, page 2](img/board/relay-interface-board-v1.4-p02.png)](img/board/relay-interface-board-v1.4-p02.png)

[![relay-interface-board-v1.4, page 3](img/board/relay-interface-board-v1.4-p03.png)](img/board/relay-interface-board-v1.4-p03.png)

[![relay-interface-board-v1.4, page 4](img/board/relay-interface-board-v1.4-p04.png)](img/board/relay-interface-board-v1.4-p04.png)

[![relay-interface-board-v1.4, page 5](img/board/relay-interface-board-v1.4-p05.png)](img/board/relay-interface-board-v1.4-p05.png)

## out/cabinet/data

### pump-cabinet-v1.7-bom.csv

[Download the CSV](files/cabinet/data/pump-cabinet-v1.7-bom.csv)

| mpn | revision | manufacturer | description | count | designations |
| --- | --- | --- | --- | --- | --- |
| 1757022 |  | Phoenix Contact | PCB connector plug, 3-pin, 5.08 mm pitch | 2 | -J1; -J2 |
| 2002-1201 |  | WAGO | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V | 39 | -X01:L1:1; -X01:L1:2; -X01:L1:3; -X01:L1:4; -X01:L2:1; -X01:L2:2; -X01:L2:3; -X01:L2:4; -X01:L3:1; -X01:L3:2; -X01:L3:3; -X01:L3:4; -X1:L1:1; -X1:L2:1; -X1:L3:1; -X1:N:1; -X2:24V:1; -X2:24V:2; -X2:24V:3; -X2:24V:4; -X2:24V:5; -X2:24V:6; -X2:24V:7; -X2:24V:8; -X2:24V:9; -X2:24V:10; -X2:GND:1; -X2:GND:2; -X2:GND:3; -X2:GND:4; -X2:GND:5; -X2:GND:6; -X2:GND:7; -X3:U:1; -X3:U:2; -X3:V:1; -X3:V:2; -X3:W:1; -X3:W:2 |
| 2002-1207 |  | WAGO | TOPJOB S ground terminal block, 2.5 mm2, green-yellow | 3 | -X1:PE:1; -X3:PE:1; -X3:PE:2 |
| 3LD2054-0TK51 |  | Siemens | Switch-disconnector, 3-pole; 16 A | 1 | -Q1 |
| 3NW7033 |  | Siemens | Fuse holder, 3-pole, 10x38 mm; 32 A | 2 | -F11; -F21 |
| 3NW8004-1 |  | Siemens | SENTRON cylindrical fuse link, 10x38 mm, aM; 4 A | 6 | -F11; -F21 |
| 3SU1102-6AA40-1AA0 |  | Siemens | Pilot light 22 mm, green, integrated LED 24 V AC/DC | 2 | -P1; -P2 |
| 5SY6506-7 |  | Siemens | Miniature circuit breaker, 1P+N, curve C; 6 A | 1 | -F01 |
| 750-402 |  | WAGO | 4-channel digital input module, 24 V DC | 1 | -DI1 |
| 750-504 |  | WAGO | 4-channel digital output module, 24 V DC; 0.5 A | 1 | -DO1 |
| 750-600 |  | WAGO | End module, terminates the internal data bus; no data contacts | 1 | -E1 |
| 750-8212 |  | WAGO | PFC200 controller, 2nd generation, 2x ETHERNET, RS-232/-485 | 1 | -C1 |
| LADN11 |  | Schneider Electric | TeSys D front-mount auxiliary contact block, 1 NO + 1 NC | 2 | -Q11; -Q21 |
| LC1D09BD |  | Schneider Electric | TeSys D contactor, 3-pole, AC-3 9 A, 1 NO + 1 NC auxiliary, 24 V DC coil | 2 | -Q11; -Q21 |
| LRD08 |  | Schneider Electric | TeSys thermal overload relay, class 10A, 2.5-4 A, 1 NO + 1 NC | 2 | -B12; -B22 |
| QUINT4-PS/1AC/24DC/2.5/SC |  | Phoenix Contact | Power supply, 1-phase, 24 V DC; 2.5 A | 1 | -T1 |
| SKX-RIB-2 | 1.4 |  | Relay interface board | 1 | -U2 |

### pump-cabinet-v1.7-cables.csv

[Download the CSV](files/cabinet/data/pump-cabinet-v1.7-cables.csv)

| designation | mpn | description | core_count | gauge_mm2 | length_mm | from_label | to_label | pairs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

### pump-cabinet-v1.7-cores.csv

[Download the CSV](files/cabinet/data/pump-cabinet-v1.7-cores.csv)

| cable | core | colour | pair | end_a | end_b | note |
| --- | --- | --- | --- | --- | --- | --- |

### pump-cabinet-v1.7-designations.csv

[Download the CSV](files/cabinet/data/pump-cabinet-v1.7-designations.csv)

| designation | reference | description |
| --- | --- | --- |
| -B12 | =P1-B12 | TeSys thermal overload relay, class 10A, 2.5-4 A, 1 NO + 1 NC |
| -B22 | =P2-B22 | TeSys thermal overload relay, class 10A, 2.5-4 A, 1 NO + 1 NC |
| -C1 | =PLC-C1 | PFC200 controller, 2nd generation, 2x ETHERNET, RS-232/-485 |
| -DI1 | =PLC-DI1 | 4-channel digital input module, 24 V DC |
| -DO1 | =PLC-DO1 | 4-channel digital output module, 24 V DC; 0.5 A |
| -E1 | =PLC-E1 | End module, terminates the internal data bus; no data contacts |
| -F01 | =CTL-F01 | Miniature circuit breaker, 1P+N, curve C; 6 A |
| -F11 | =P1-F11 | Fuse holder, 3-pole, 10x38 mm; 32 A |
| -F21 | =P2-F21 | Fuse holder, 3-pole, 10x38 mm; 32 A |
| -J1 | =PLC-J1 | PCB connector plug, 3-pin, 5.08 mm pitch |
| -J2 | =PLC-J2 | PCB connector plug, 3-pin, 5.08 mm pitch |
| -P1 | =P1-P1 | Pilot light 22 mm, green, integrated LED 24 V AC/DC |
| -P2 | =P2-P2 | Pilot light 22 mm, green, integrated LED 24 V AC/DC |
| -Q1 | =SUP-Q1 | Switch-disconnector, 3-pole; 16 A |
| -Q11 | =P1-Q11 | TeSys D contactor, 3-pole, AC-3 9 A, 1 NO + 1 NC auxiliary, 24 V DC coil |
| -Q21 | =P2-Q21 | TeSys D contactor, 3-pole, AC-3 9 A, 1 NO + 1 NC auxiliary, 24 V DC coil |
| -T1 | =CTL-T1 | Power supply, 1-phase, 24 V DC; 2.5 A |
| -U1 | =PLC-U1 |  |
| -X01 | -X01 |  |
| -X1 | -X1 |  |
| -X01:L1:1 | =SUP-X01:L1:1 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X1:L1:1 | =SUP-X1:L1:1 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X01:L1:2 | =SUP-X01:L1:2 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X01:L1:3 | =SUP-X01:L1:3 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X01:L1:4 | =SUP-X01:L1:4 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X01:L2:1 | =SUP-X01:L2:1 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X1:L2:1 | =SUP-X1:L2:1 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X01:L2:2 | =SUP-X01:L2:2 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X01:L2:3 | =SUP-X01:L2:3 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X01:L2:4 | =SUP-X01:L2:4 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X01:L3:1 | =SUP-X01:L3:1 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X1:L3:1 | =SUP-X1:L3:1 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X01:L3:2 | =SUP-X01:L3:2 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X01:L3:3 | =SUP-X01:L3:3 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X01:L3:4 | =SUP-X01:L3:4 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X1:N:1 | =SUP-X1:N:1 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X1:PE:1 | =SUP-X1:PE:1 | TOPJOB S ground terminal block, 2.5 mm2, green-yellow |
| -X2 | -X2 |  |
| -X2:24V:1 | =CTL-X2:24V:1 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X2:24V:2 | =CTL-X2:24V:2 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X2:24V:3 | =CTL-X2:24V:3 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X2:24V:4 | =CTL-X2:24V:4 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X2:24V:5 | =CTL-X2:24V:5 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X2:24V:6 | =CTL-X2:24V:6 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X2:24V:7 | =CTL-X2:24V:7 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X2:24V:8 | =CTL-X2:24V:8 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X2:24V:9 | =CTL-X2:24V:9 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X2:24V:10 | =CTL-X2:24V:10 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X2:GND:1 | =CTL-X2:GND:1 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X2:GND:2 | =CTL-X2:GND:2 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X2:GND:3 | =CTL-X2:GND:3 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X2:GND:4 | =CTL-X2:GND:4 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X2:GND:5 | =CTL-X2:GND:5 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X2:GND:6 | =CTL-X2:GND:6 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X2:GND:7 | =CTL-X2:GND:7 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X3 | -X3 |  |
| -X3:PE:1 | =P1-X3:PE:1 | TOPJOB S ground terminal block, 2.5 mm2, green-yellow |
| -X3:PE:2 | =P2-X3:PE:2 | TOPJOB S ground terminal block, 2.5 mm2, green-yellow |
| -X3:U:1 | =P1-X3:U:1 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X3:U:2 | =P2-X3:U:2 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X3:V:1 | =P1-X3:V:1 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X3:V:2 | =P2-X3:V:2 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X3:W:1 | =P1-X3:W:1 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |
| -X3:W:2 | =P2-X3:W:2 | TOPJOB S feed-through terminal block, 2.5 mm2, grey; 24 A; 800 V |

### pump-cabinet-v1.7-plc.csv

[Download the CSV](files/cabinet/data/pump-cabinet-v1.7-plc.csv)

| pin | channel_name | signal | signal_name | wired_to |
| --- | --- | --- | --- | --- |
| -DI1:DI1 | 1 | di | P1_OVERLOAD | -B12:98 |
| -DI1:DI2 | 2 | di | P1_RUNNING | -Q11:14 |
| -DI1:DI3 | 3 | di | P2_OVERLOAD | -B22:98 |
| -DI1:DI4 | 4 | di | P2_RUNNING | -Q21:14 |
| -DO1:DO1 | 1 | do | P1_RUN | -J1:1 |
| -DO1:DO2 | 2 | do | P2_RUN | -J1:2 |
| -DO1:DO3 | 3 | do |  |  |
| -DO1:DO4 | 4 | do |  |  |

### pump-cabinet-v1.7-terminals-X01.csv

[Download the CSV](files/cabinet/data/pump-cabinet-v1.7-terminals-X01.csv)

| designation | group | index | side_a | side_b | jumper_group |
| --- | --- | --- | --- | --- | --- |
| -X01:L1:1 | L1 | 1 | -Q1:2T1; -X01:L1:2 |  | 1 |
| -X01:L1:2 | L1 | 2 | -F01:1; -X01:L1:1; -X01:L1:3 |  | 1 |
| -X01:L1:3 | L1 | 3 | -F11:1; -X01:L1:2; -X01:L1:4 |  | 1 |
| -X01:L1:4 | L1 | 4 | -F21:1; -X01:L1:3 |  | 1 |
| -X01:L2:1 | L2 | 1 | -Q1:4T2; -X01:L2:2 |  | 2 |
| -X01:L2:2 | L2 | 2 | -X01:L2:1; -X01:L2:3 |  | 2 |
| -X01:L2:3 | L2 | 3 | -F11:3; -X01:L2:2; -X01:L2:4 |  | 2 |
| -X01:L2:4 | L2 | 4 | -F21:3; -X01:L2:3 |  | 2 |
| -X01:L3:1 | L3 | 1 | -Q1:6T3; -X01:L3:2 |  | 3 |
| -X01:L3:2 | L3 | 2 | -X01:L3:1; -X01:L3:3 |  | 3 |
| -X01:L3:3 | L3 | 3 | -F11:5; -X01:L3:2; -X01:L3:4 |  | 3 |
| -X01:L3:4 | L3 | 4 | -F21:5; -X01:L3:3 |  | 3 |

### pump-cabinet-v1.7-terminals-X1.csv

[Download the CSV](files/cabinet/data/pump-cabinet-v1.7-terminals-X1.csv)

| designation | group | index | side_a | side_b | jumper_group |
| --- | --- | --- | --- | --- | --- |
| -X1:L1:1 | L1 | 1 | -Q1:1L1 | +EXT-X0:L1:1 |  |
| -X1:L2:1 | L2 | 1 | -Q1:3L2 | +EXT-X0:L2:1 |  |
| -X1:L3:1 | L3 | 1 | -Q1:5L3 | +EXT-X0:L3:1 |  |
| -X1:N:1 | N | 1 | -F01:3 N | +EXT-X0:N:1 |  |
| -X1:PE:1 | PE | 1 | -X3:PE:1; -X3:PE:2 | +EXT-X0:PE:1 |  |

### pump-cabinet-v1.7-terminals-X2.csv

[Download the CSV](files/cabinet/data/pump-cabinet-v1.7-terminals-X2.csv)

| designation | group | index | side_a | side_b | jumper_group |
| --- | --- | --- | --- | --- | --- |
| -X2:24V:1 | 24V | 1 | -T1:+; -X2:24V:2 |  | 1 |
| -X2:24V:2 | 24V | 2 | -C1:24 V; -X2:24V:1; -X2:24V:3 |  | 1 |
| -X2:24V:3 | 24V | 3 | -C1:+; -X2:24V:2; -X2:24V:4 |  | 1 |
| -X2:24V:4 | 24V | 4 | -J2:1; -X2:24V:3; -X2:24V:5 |  | 1 |
| -X2:24V:5 | 24V | 5 | -Q11:53/NO; -X2:24V:4; -X2:24V:6 |  | 1 |
| -X2:24V:6 | 24V | 6 | -B12:97; -X2:24V:5; -X2:24V:7 |  | 1 |
| -X2:24V:7 | 24V | 7 | -Q11:13/NO; -X2:24V:6; -X2:24V:8 |  | 1 |
| -X2:24V:8 | 24V | 8 | -Q21:53/NO; -X2:24V:7; -X2:24V:9 |  | 1 |
| -X2:24V:9 | 24V | 9 | -B22:97; -X2:24V:8; -X2:24V:10 |  | 1 |
| -X2:24V:10 | 24V | 10 | -Q21:13/NO; -X2:24V:9 |  | 1 |
| -X2:GND:1 | GND | 1 | -T1:-; -X2:GND:2 |  | 2 |
| -X2:GND:2 | GND | 2 | -C1:0V; -X2:GND:1; -X2:GND:3 |  | 2 |
| -X2:GND:3 | GND | 3 | -C1:-; -X2:GND:2; -X2:GND:4 |  | 2 |
| -X2:GND:4 | GND | 4 | -Q11:A2; -X2:GND:3; -X2:GND:5 |  | 2 |
| -X2:GND:5 | GND | 5 | -P1:X2; -X2:GND:4; -X2:GND:6 |  | 2 |
| -X2:GND:6 | GND | 6 | -Q21:A2; -X2:GND:5; -X2:GND:7 |  | 2 |
| -X2:GND:7 | GND | 7 | -P2:X2; -X2:GND:6 |  | 2 |

### pump-cabinet-v1.7-terminals-X3.csv

[Download the CSV](files/cabinet/data/pump-cabinet-v1.7-terminals-X3.csv)

| designation | group | index | side_a | side_b | jumper_group |
| --- | --- | --- | --- | --- | --- |
| -X3:PE:1 | PE | 1 | -X1:PE:1 | +EXT-M1:PE |  |
| -X3:PE:2 | PE | 2 | -X1:PE:1 | +EXT-M2:PE |  |
| -X3:U:1 | U | 1 | -B12:2/T1 | +EXT-M1:U1 |  |
| -X3:U:2 | U | 2 | -B22:2/T1 | +EXT-M2:U1 |  |
| -X3:V:1 | V | 1 | -B12:4/T2 | +EXT-M1:V1 |  |
| -X3:V:2 | V | 2 | -B22:4/T2 | +EXT-M2:V1 |  |
| -X3:W:1 | W | 1 | -B12:6/T3 | +EXT-M1:W1 |  |
| -X3:W:2 | W | 2 | -B22:6/T3 | +EXT-M2:W1 |  |

### pump-cabinet-v1.7-wires.csv

[Download the CSV](files/cabinet/data/pump-cabinet-v1.7-wires.csv)

| from | to | colour | cross_section_mm2 | label |
| --- | --- | --- | --- | --- |
| -B12:95 | -J2:2 | WH | 1.5 | -B12:95 -J2:2 |
| -B12:96 | -Q11:A1 | WH | 1.5 | -B12:96 -Q11:A1 |
| -B12:98 | -DI1:DI1 | WH | 1.5 | -B12:98 -DI1:DI1 |
| -B22:95 | -J2:3 | WH | 1.5 | -B22:95 -J2:3 |
| -B22:96 | -Q21:A1 | WH | 1.5 | -B22:96 -Q21:A1 |
| -B22:98 | -DI1:DI3 | WH | 1.5 | -B22:98 -DI1:DI3 |
| -DI1:DI2 | -Q11:14 | WH | 1.5 | -DI1:DI2 -Q11:14 |
| -DI1:DI4 | -Q21:14 | WH | 1.5 | -DI1:DI4 -Q21:14 |
| -DO1:0V | -J1:3 | WH | 0.5 | -DO1:0V -J1:3 |
| -DO1:DO1 | -J1:1 | WH | 0.5 | -DO1:DO1 -J1:1 |
| -DO1:DO2 | -J1:2 | WH | 0.5 | -DO1:DO2 -J1:2 |
| -F01:2 | -T1:L/+ | BN | 1.5 | -F01:2 -T1:L/+ |
| -F01:N 4 | -T1:N/- | BU | 1.5 | -F01:N 4 -T1:N/- |
| -F11:2 | -Q11:1/L1 | BN | 1.5 | -F11:2 -Q11:1/L1 |
| -F11:4 | -Q11:3/L2 | BK | 1.5 | -F11:4 -Q11:3/L2 |
| -F11:6 | -Q11:5/L3 | GY | 1.5 | -F11:6 -Q11:5/L3 |
| -F21:2 | -Q21:1/L1 | BN | 1.5 | -F21:2 -Q21:1/L1 |
| -F21:4 | -Q21:3/L2 | BK | 1.5 | -F21:4 -Q21:3/L2 |
| -F21:6 | -Q21:5/L3 | GY | 1.5 | -F21:6 -Q21:5/L3 |
| -P1:X1 | -Q11:54 | WH | 1.5 | -P1:X1 -Q11:54 |
| -P2:X1 | -Q21:54 | WH | 1.5 | -P2:X1 -Q21:54 |
| -X01:L1:1 | -Q1:2T1 | BN | 2.5 | -X01:L1:1 -Q1:2T1 |
| -X1:L1:1 | -Q1:1L1 | BN | 2.5 | -X1:L1:1 -Q1:1L1 |
| -X01:L1:2 | -F01:1 | BN | 1.5 | -X01:L1:2 -F01:1 |
| -X01:L1:3 | -F11:1 | BN | 1.5 | -X01:L1:3 -F11:1 |
| -X01:L1:4 | -F21:1 | BN | 1.5 | -X01:L1:4 -F21:1 |
| -X01:L2:1 | -Q1:4T2 | BK | 2.5 | -X01:L2:1 -Q1:4T2 |
| -X1:L2:1 | -Q1:3L2 | BK | 2.5 | -X1:L2:1 -Q1:3L2 |
| -X01:L2:3 | -F11:3 | BK | 1.5 | -X01:L2:3 -F11:3 |
| -X01:L2:4 | -F21:3 | BK | 1.5 | -X01:L2:4 -F21:3 |
| -X01:L3:1 | -Q1:6T3 | GY | 2.5 | -X01:L3:1 -Q1:6T3 |
| -X1:L3:1 | -Q1:5L3 | GY | 2.5 | -X1:L3:1 -Q1:5L3 |
| -X01:L3:3 | -F11:5 | GY | 1.5 | -X01:L3:3 -F11:5 |
| -X01:L3:4 | -F21:5 | GY | 1.5 | -X01:L3:4 -F21:5 |
| -X1:N:1 | -F01:3 N | BU | 1.5 | -X1:N:1 -F01:3 N |
| -X2:24V:1 | -T1:+ | RD | 1.5 | -X2:24V:1 -T1:+ |
| -X2:24V:2 | -C1:24 V | RD | 1.5 | -X2:24V:2 -C1:24 V |
| -X2:24V:3 | -C1:+ | RD | 1.5 | -X2:24V:3 -C1:+ |
| -X2:24V:4 | -J2:1 | RD | 0.5 | -X2:24V:4 -J2:1 |
| -X2:24V:5 | -Q11:53/NO | RD | 1.5 | -X2:24V:5 -Q11:53/NO |
| -X2:24V:6 | -B12:97 | RD | 1.5 | -X2:24V:6 -B12:97 |
| -X2:24V:7 | -Q11:13/NO | RD | 1.5 | -X2:24V:7 -Q11:13/NO |
| -X2:24V:8 | -Q21:53/NO | RD | 1.5 | -X2:24V:8 -Q21:53/NO |
| -X2:24V:9 | -B22:97 | RD | 1.5 | -X2:24V:9 -B22:97 |
| -X2:24V:10 | -Q21:13/NO | RD | 1.5 | -X2:24V:10 -Q21:13/NO |
| -X2:GND:1 | -T1:- | BK | 1.5 | -X2:GND:1 -T1:- |
| -X2:GND:2 | -C1:0V | BK | 1.5 | -X2:GND:2 -C1:0V |
| -X2:GND:3 | -C1:- | BK | 1.5 | -X2:GND:3 -C1:- |
| -X2:GND:4 | -Q11:A2 | BK | 1.5 | -X2:GND:4 -Q11:A2 |
| -X2:GND:5 | -P1:X2 | BK | 1.5 | -X2:GND:5 -P1:X2 |
| -X2:GND:6 | -Q21:A2 | BK | 1.5 | -X2:GND:6 -Q21:A2 |
| -X2:GND:7 | -P2:X2 | BK | 1.5 | -X2:GND:7 -P2:X2 |
| -X3:U:1 | -B12:2/T1 | BN | 1.5 | -X3:U:1 -B12:2/T1 |
| -X3:U:2 | -B22:2/T1 | BN | 1.5 | -X3:U:2 -B22:2/T1 |
| -X3:V:1 | -B12:4/T2 | BK | 1.5 | -X3:V:1 -B12:4/T2 |
| -X3:V:2 | -B22:4/T2 | BK | 1.5 | -X3:V:2 -B22:4/T2 |
| -X3:W:1 | -B12:6/T3 | GY | 1.5 | -X3:W:1 -B12:6/T3 |
| -X3:W:2 | -B22:6/T3 | GY | 1.5 | -X3:W:2 -B22:6/T3 |

- Download: [pump-cabinet-v1.7-wago-U1.xml](files/cabinet/data/pump-cabinet-v1.7-wago-U1.xml)

## out/cabinet

### pump-cabinet-v1.7.pdf

[Download the PDF](files/cabinet/pump-cabinet-v1.7.pdf)

[![pump-cabinet-v1.7, page 1](img/cabinet/pump-cabinet-v1.7-p01.png)](img/cabinet/pump-cabinet-v1.7-p01.png)

[![pump-cabinet-v1.7, page 2](img/cabinet/pump-cabinet-v1.7-p02.png)](img/cabinet/pump-cabinet-v1.7-p02.png)

[![pump-cabinet-v1.7, page 3](img/cabinet/pump-cabinet-v1.7-p03.png)](img/cabinet/pump-cabinet-v1.7-p03.png)

[![pump-cabinet-v1.7, page 4](img/cabinet/pump-cabinet-v1.7-p04.png)](img/cabinet/pump-cabinet-v1.7-p04.png)

[![pump-cabinet-v1.7, page 5](img/cabinet/pump-cabinet-v1.7-p05.png)](img/cabinet/pump-cabinet-v1.7-p05.png)

[![pump-cabinet-v1.7, page 6](img/cabinet/pump-cabinet-v1.7-p06.png)](img/cabinet/pump-cabinet-v1.7-p06.png)

[![pump-cabinet-v1.7, page 7](img/cabinet/pump-cabinet-v1.7-p07.png)](img/cabinet/pump-cabinet-v1.7-p07.png)

[![pump-cabinet-v1.7, page 8](img/cabinet/pump-cabinet-v1.7-p08.png)](img/cabinet/pump-cabinet-v1.7-p08.png)

[![pump-cabinet-v1.7, page 9](img/cabinet/pump-cabinet-v1.7-p09.png)](img/cabinet/pump-cabinet-v1.7-p09.png)

[![pump-cabinet-v1.7, page 10](img/cabinet/pump-cabinet-v1.7-p10.png)](img/cabinet/pump-cabinet-v1.7-p10.png)

