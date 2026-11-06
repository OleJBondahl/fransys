# Two-pump station: the authoring script.
#
# Written for Fransys (see the pin in pyproject.toml). It authors the
# cabinet unit and the system around it; `__main__` checks
# the model and writes the three output folders. Known gaps in the library are tracked in
# GAPS.md, and cited here only as "GAPS.md G<n>".
#
# Two levels share this file. The easy level writes a circuit out, one device and one wire per
# line: the incoming supply, the main switch, the control supply, the PLC rack. The efficient level
# puts the same calls in a function or a table: `pump()` is called once per pump, the pumps' PLC
# channels come from `PUMPS`, and the parts come from the typed module `parts_typed.py`
# (regenerate it with `python -m fransys parts-module example_parts parts_typed.py`).
#
# Wire colours follow the repo rule: L1 BN, L2 BK, L3 GY, N BU, PE GNYE; on the 24 V side a wire
# with an end on a 24V terminal is RD, an end on a GND terminal is BK, any other is WH.

import sys
from pathlib import Path
from typing import NamedTuple

import fransys as fr
from fransys.colours import BK, BN, BU, GY, RD, WH

import parts_typed as P

PHASES = (BN, BK, GY)  # L1, L2, L3


# Per pump: the PLC input pins its two feedback contacts return on, the interface relay that
# drives its contactor coil, and the DO channel that switches that relay.
class PumpRow(NamedTuple):
    n: int
    di: tuple[str, str]
    relay: str
    do: str


PUMPS = (PumpRow(1, ("DI1", "DI2"), "K1", "DO1"), PumpRow(2, ("DI3", "DI4"), "K2", "DO2"))


# What the system outside reaches in the cabinet: the incoming terminals, the pump terminals, the
# Ethernet port.
class CabinetPoints(NamedTuple):
    L1: fr.Run
    L2: fr.Run
    L3: fr.Run
    N: fr.Run
    PE: fr.Run
    U: fr.Run
    V: fr.Run
    W: fr.Run
    PE_PUMP: fr.Run
    ETH: fr.Fn


def pump(
    u, n, *, phases, colours, motor_terminals, v24, gnd, di_overload, di_running, relay_contact
):
    """Author pump `n` in the cabinet `u` and return its aux block and overload relay.

    `phases` are the three feed terminals with their wire `colours`, `motor_terminals` the U, V and W terminals the motor
    cable leaves on, `v24` three terminals of the 24 V rail and `gnd` two of the GND rail,
    `di_overload` and `di_running` the PLC input pins, `relay_contact` the make contact of the interface relay
    that drives the coil.
    """
    fuse_holder = u.device(f"F{n}1", P.P_3NW7033)
    for pole in (1, 2, 3):
        u.device(None, P.P_3NW8004_1, name=f"f{n}1_pole_{pole}_link", parent=fuse_holder)
    contactor = u.device(f"Q{n}1", P.LC1D09BD)
    aux_block = u.device(None, P.LADN22, name=f"q{n}_aux_block", parent=contactor)
    overload = u.device(f"B{n}2", P.LRD08, mounted_on=contactor.main)
    lamp = u.device(None, P.P_3SU1102_6AA40_1AA0, name=f"run_lamp{n}")

    # The motor branch: feed, fuse links, contactor, overload relay, motor terminals. The
    # overload relay plugs onto the contactor's output blades (`mounted_on`), so no wire joins them.
    poles = (("1", "2", "1/L1", "2/T1"), ("3", "4", "3/L2", "4/T2"), ("5", "6", "5/L3", "6/T3"))
    for i, (feed, out, line, load) in enumerate(poles):
        holder_pole = (fuse_holder.pole_1, fuse_holder.pole_2, fuse_holder.pole_3)[i]
        u.series(phases[i], holder_pole[feed], wire=(colours[i], 1.5))
        u.series(holder_pole[out], contactor.main[line], wire=(colours[i], 1.5))
        u.series(overload.main[load], motor_terminals[i], wire=(colours[i], 1.5))

    # Coil circuit: the interface relay's make contact, through the
    # overload relay's break contact 95-96 to the contactor coil, and back to GND.
    u.series(relay_contact, overload.nc["95"], wire=(WH, 1.5))
    u.series(overload.nc["96"], contactor.coil["A1"], wire=(WH, 1.5))
    u.series(contactor.coil["A2"], gnd[0], wire=(BK, 1.5))

    # Running lamp: 24 V through the aux block's make contact, so it follows the contactor.
    u.series(v24[0], aux_block.no["53/NO"], wire=(RD, 1.5))
    u.series(aux_block.no["54"], lamp.lamp["X1"], wire=(WH, 1.5))
    u.series(lamp.lamp["X2"], gnd[1], wire=(BK, 1.5))

    # PLC feedback: the overload relay's make contact (97-98) and the aux block's second make
    # contact (83-84 of the aux block), each fed from 24 V and returning to a DI channel.
    u.series(v24[1], overload.no["97"], wire=(RD, 1.5))
    u.series(overload.no["98"], di_overload, wire=(WH, 1.5))
    u.series(v24[2], aux_block.no_2["83/NO"], wire=(RD, 1.5))
    u.series(aux_block.no_2["84"], di_running, wire=(WH, 1.5))
    return aux_block, overload


@fr.unit(
    "pump-cabinet",
    revision=11,
    interface_version=1,
    date="2026-11-06",
    text="Re-release on Fransys v0.22.6; the design is unchanged (R1807).",
    by="SK",
    title="Pump cabinet",
    number="SKX-PC-2",
    history=[
        {"revision": 1, "date": "2026-09-01", "text": "First release", "created": "SK"},
        {
            "revision": 2,
            "date": "2026-09-23",
            "text": "Overload feedback to the PLC",
            "created": "SK",
        },
        {
            "revision": 3,
            "date": "2026-10-02",
            "text": "TeSys D parts, 24V and GND rails, IEC wire colours",
            "created": "SK",
        },
        {
            "revision": 4,
            "date": "2026-10-05",
            "text": "Unit tags, links, busbars and rail bonds, energy on fed supplies",
            "created": "SK",
        },
        {
            "revision": 5,
            "date": "2026-10-06",
            "text": "Three phases on four terminals each, pump n on terminal n+2",
            "created": "SK",
        },
        {
            "revision": 6,
            "date": "2026-10-06",
            "text": (
                "Owner ruling 2026-10-06, a cabinet is a unit: the place C1 is gone. The change "
                "list reads No changes. because the listing drops a place that holds the whole "
                "unit, baseline L2, kept by design (REL-DIFF-PLACE)"
            ),
            "created": "SK",
        },
        {
            "revision": 7,
            "date": "2026-10-16",
            "text": "Re-cut under fransys 0.19.9, drawings redrawn, no design change",
            "created": "SK",
        },
        {
            "revision": 8,
            "date": "2026-10-25",
            "text": "Pump contact blocks LADN22: the running feedback leaves on the block's second make contact, 83-84 (R780)",
            "created": "SK",
        },
        {
            "revision": 9,
            "date": "2026-10-26",
            "text": "Terminal strip X01 is X4 and breaker F01 is F1: a tag takes no leading zero (R1114)",
            "created": "SK",
        },
        {
            "revision": 10,
            "date": "2026-10-28",
            "text": "No mate, board unit or harness line: the interface relays are wired in the cabinet, and the Ethernet link is a cable (R1216, R1253)",
            "created": "SK",
        },
    ],
)
def cabinet(u):
    """The pump cabinet: incoming feed, control supply, PLC, interface relays and two pump starters."""
    # -- =SUP: incoming terminals and main switch ------------------------------------------
    with u.function("SUP", "Incoming supply"):
        # One strip, one run per conductor: a run is a named group of terminals (L1, N, PE).
        x1 = u.terminal_strip("X1", P.P_2002_1201, pe=P.P_2002_1207, interface=True)
        x1_l1, x1_l2, x1_l3, x1_n = (x1.run(kind, 1) for kind in ("L1", "L2", "L3", "N"))
        x1_pe = x1.run(
            "PE", 1, rail=True
        )  # the cabinet's PE rail: one flagged terminal, bonded to the mounting rail by its foot
        # The three phases and the neutral start at the cabinet's own incoming terminals.
        u.ac_supply("mains", 230, x1_l1[1], x1_l2[1], x1_l3[1], n=x1_n[1])
        incoming_pe = x1_pe[1]  # taken here, so the PE terminal joins this block

        q1 = u.device("Q1", P.P_3LD2054_0TK51)
        for run, pin, colour in ((x1_l1, "1L1", BN), (x1_l2, "3L2", BK), (x1_l3, "5L3", GY)):
            u.series(run[1], q1.main[pin], wire=(colour, 2.5))

        # -X4 distributes the three phases after -Q1: one terminal per consumer and phase,
        # each phase one bridged run, as on the real strip. Wires land on the bridged side.
        # Every phase has four terminals: pump n takes terminal n+2 on L1, L2 and L3; terminal 2
        # on L2 and L3 is a bridged spare, so the three phases follow one pattern.
        x4 = u.terminal_strip("X4", P.P_2002_1201)
        l1 = x4.run("L1", 4, bridged=True)
        l2 = x4.run("L2", 4, bridged=True)
        l3 = x4.run("L3", 4, bridged=True)
        for rail, port, colour in ((l1, "2T1", BN), (l2, "4T2", BK), (l3, "6T3", GY)):
            u.series(q1.main[port], rail[1], wire=(colour, 2.5))

    # -- =CTL: miniature circuit breaker and the 24 V DC power supply ----------------------
    with u.function("CTL", "Control supply"):
        f1 = u.device("F1", P.P_5SY6506_7)
        u.series(l1[2], f1.pole["1"], wire=(BN, 1.5))
        u.series(x1_n[1], f1.pole["3 N"], wire=(BU, 1.5))

        t1 = u.device("T1", P.QUINT4_PS_1AC_24DC_2_5_SC)
        u.series(f1.pole["2"], t1.input["L/+"], wire=(BN, 1.5))
        u.series(f1.pole["N 4"], t1.input["N/-"], wire=(BU, 1.5))

        # -X2 is the 24 V distribution: every 24V point is bridged on one rail, every GND point
        # on the other, and each consumer lands on its own terminal. The supply's output lands on
        # the first. 24V: supply, controller system, controller field, one per interface relay, then three per
        # pump. GND: supply, controller system, controller field, then two per pump.
        x2 = u.terminal_strip("X2", P.P_2002_1201)
        v24, gnd = x2.run("24V", 11, bridged=True), x2.run("GND", 7, bridged=True)
        u.dc_supply("24V", plus=v24[1], minus=gnd[1], voltage=24, names=("24V", "GND"))
        u.series(t1.output["+"], v24[1], wire=(RD, 1.5))
        u.series(t1.output["-"], gnd[1], wire=(BK, 1.5))

    # -- =PLC: WAGO controller and I/O modules ---------------------------------------------
    with u.function("PLC", "WAGO PLC"):
        rack = u.rack("U1")
        # The rack container is -U1; its modules carry the rack scheme as explicit tags,
        # counting up per type (C1 controller, DI1, DO1, E1 end module).
        # The controller's first RJ45 port is the cabinet's interface, where the cable from outside
        # plugs in; the second is left open on purpose.
        controller = u.device(
            "C1",
            P.P_750_8212,
            name="controller",
            parent=rack,
            position=1,
            interface=("x1",),
            unused=("x2",),
        )
        di = u.device("DI1", P.P_750_402, name="di", parent=rack, position=2)
        do = u.device("DO1", P.P_750_504, name="do", parent=rack, position=3)
        u.device("E1", P.P_750_600, name="end", parent=rack, position=4)

        # The controller takes the system supply and the field supply separately.
        u.series(v24[2], controller.system["24 V"], wire=(RD, 1.5))
        u.series(gnd[2], controller.system["0V"], wire=(BK, 1.5))
        u.series(v24[3], controller.field["+"], wire=(RD, 1.5))
        u.series(gnd[3], controller.field["-"], wire=(BK, 1.5))

        # The field supply reaches the I/O modules through the rack's power-jumper contacts.
        for module in (di, do):
            u.detail.busbar(controller.field["+"], module.power["24V"])
            u.detail.busbar(controller.field["-"], module.power["0V"])

    # -- per-pump power and control circuits -----------------------------------------------
    x3 = u.terminal_strip("X3", P.P_2002_1201, pe=P.P_2002_1207, interface=True)
    motor_u, motor_v, motor_w, motor_pe = (x3.run(kind, 2) for kind in ("U", "V", "W", "PE"))
    feeds = {1: (l1[3], l2[3], l3[3]), 2: (l1[4], l2[4], l3[4])}
    pump_pe = []
    for row in PUMPS:
        n = row.n
        with u.function(f"P{n}", f"Pump {n}"):
            # The interface relay between the PLC output and the contactor coil: a 24 V DC relay
            # with no diode, since the PLC module handles the coil.
            relay = u.device(row.relay, P.P_40_61_9_024_1000)
            u.series(do[row.do], relay.coil["A1"], wire=(WH, 0.5))
            u.series(do.power["0V"], relay.coil["A2"], wire=(WH, 0.5))
            u.series(v24[3 + n], relay.contact["11"], wire=(RD, 0.5))
            aux_block, overload = pump(
                u,
                n,
                phases=feeds[n],
                colours=PHASES,
                motor_terminals=(motor_u[n], motor_v[n], motor_w[n]),
                v24=[v24[6 + 3 * (n - 1) + k] for k in range(3)],
                gnd=[gnd[4 + 2 * (n - 1) + k] for k in range(2)],
                di_overload=di[row.di[0]],
                di_running=di[row.di[1]],
                relay_contact=relay.contact["14"],
            )
            pump_pe.append(motor_pe[n])  # taken here, so the PE terminal joins the pump's block
            # The PLC channels: the two feedback contacts in, the interface relay's coil out.
            overload.no.plc(fr.DI, f"P{n}_OVERLOAD", priority=2 * n - 1)
            aux_block.no_2.plc(fr.DI, f"P{n}_RUNNING", priority=2 * n)
            relay.coil.plc(fr.DO, f"P{n}_RUN", priority=n)

    u.earth(
        incoming_pe, *pump_pe
    )  # one PE net for the whole design; the feet bond each terminal to the mounting rail

    return CabinetPoints(
        x1_l1, x1_l2, x1_l3, x1_n, x1_pe, motor_u, motor_v, motor_w, motor_pe, controller.x1
    )


d = fr.design(P, place="EXT")
d.location("EXT", "External")
d.project(
    title="Two-pump station",
    number="EX-1",
    customer="Example works",
    revision=6,
    author="fransys-examples",
)
d.revision(1, date="2026-09-23", text="First issue", created="SK")
d.revision(
    2,
    date="2026-10-06",
    text="The cabinet is a unit with no place of its own (owner ruling 2026-10-06)",
    created="SK",
)
d.revision(
    3,
    date="2026-10-06",
    text="-W3-W1 prints as -W3 (Fransys 0.11.0, R129 lone cable)",
    created="SK",
)
d.revision(
    4,
    date="2026-10-25",
    text="Pump cabinet 1.8: LADN22 contact blocks (R780)",
    created="SK",
)
d.revision(
    5,
    date="2026-10-26",
    text="Pump cabinet 1.9: terminal strip X01 is X4, breaker F01 is F1 (R1114)",
    created="SK",
)

d.revision(
    6,
    date="2026-10-28",
    text="Pump cabinet 1.10: no mate, board unit or harness line; the Ethernet link W3 is a cable",
    created="SK",
)

cab = d.add(cabinet, "U1", place=None)

# -- outside the cabinet, at +EXT ----------------------------------------------------------
with d.function("SUP", "Incoming supply"):
    # The upstream terminals, by others, and the incoming cable.
    x0 = d.terminal_strip("X0", P.P_2002_1201, pe=P.P_2002_1207, external=True)
    upstream = [x0.run(kind, 1) for kind in ("L1", "L2", "L3", "N", "PE")]
    w1 = d.cable("W1", P.P_1119405, length_m=10)
    for core, (outside, inside) in enumerate(
        zip(upstream, (cab.L1, cab.L2, cab.L3, cab.N, cab.PE), strict=True), start=1
    ):
        w1.core(core, outside[1], inside[1])

for row in PUMPS:
    n = row.n
    with d.function(f"P{n}", f"Pump {n}"):
        motor = d.device(f"M{n}", P.P_1LE1003_0EB42_2AA4)
        cable = d.cable(f"W{n}1", P.P_1119304, length_m=15)
        ends = (cab.U, cab.V, cab.W, cab.PE_PUMP)
        for core, (run, pin) in enumerate(zip(ends, ("U1", "V1", "W1", "PE"), strict=True), 1):
            cable.core(core, run[n], motor[pin])  # ty: ignore[invalid-argument-type] -- the pin is one of the part's literal pin names

with d.function("PLC", "WAGO PLC"):
    # The network switch is by others; a patch cable joins it to the controller's first
    # Ethernet port, every one of its eight cores landed on both ends.
    switch = d.device("K1", P.P_1085039, external=True)
    w3 = d.cable("W3", P.P_2170465, length_m=3)
    for core in range(1, 9):
        w3.core(core, cab.ETH[str(core)], switch.port_1[str(core)])  # ty: ignore[invalid-argument-type] -- the typed part lists its pin names as literals; str(core) is one of them

# Every profile field this leaves out takes its house value; the drawing order of the groups is the house one.
d.layout.profile(hide_unused_pins=True)

# Cover paths are relative to this file, so they do not depend on the working directory.
HERE = Path(__file__).parent
LOGO = HERE / "assets" / "fransys-mark.svg"
documents = (
    fr.document(
        fr.DocumentPreset.CABINET_SCHEMATIC, "pump-cabinet", cover=HERE / "cabinet.md", logo=LOGO
    ),
    fr.document(fr.DocumentPreset.SYSTEM, None, cover=HERE / "system.md", logo=LOGO),
)


def main(argv: list[str]) -> None:
    """Check the model, write the two folders, and with `--release` freeze both units."""
    built = fr.build(d, *documents)
    errors = [f for f in fr.check(built) if f.severity is fr.Severity.ERROR]
    if errors:
        raise SystemExit("\n".join(f"{f.code}: {f.message}" for f in errors))
    out = Path("out")
    fr.write(built, out_dir=out / "cabinet", unit="pump-cabinet")
    fr.write(built, out_dir=out / "all", intermediates=Path(".fransys/intermediates"))
    if "--release" in argv:
        # A released revision never
        # changes: change the design, raise the revision, then release again.
        releases = Path("releases")
        fr.release(built, releases, unit="pump-cabinet")


if __name__ == "__main__":
    main(sys.argv[1:])
