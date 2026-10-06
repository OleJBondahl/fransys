"""WP17 synthetic use case: a small cabinet (ROADMAP WP17).

All parts, MPNs and designations are invented for this repo; none describe a real
product or project (CLAUDE.md invariant, red flag "Real project data in fixtures").
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from kit import Kit, PartSpec, Ref, Slot, template_of

from fransys_model.vocab.enums import (
    Aspect,
    ConductorKind,
    FunctionKind,
    LinkKind,
    NetClass,
    PartCategory,
    PortRole,
    SignalType,
)
from fransys_model.vocab.facets.cable import CableProductFacet
from fransys_model.vocab.facets.plc import PlcBindingFacet, PlcChannelFacet, PlcRequestFacet
from fransys_model.vocab.facets.scaling import ScalingFacet
from fransys_model.vocab.facets.terminal import TerminalFacet

if TYPE_CHECKING:
    from fransys_model.kernel import Draft
    from fransys_model.vocab import PartBundle

type Things = dict[str, Ref]
type Catalogue = dict[str, PartBundle]
type _ModuleRow = tuple[int, str, SignalType, tuple[str, ...]]

_L1_TERMINALS = (("L1", 1), ("L1", 2), ("L2", 1), ("L3", 1), ("PE", 1))
_FIELD_PAIRS = ("PT01", "TT01", "S1")
_MODULES: tuple[_ModuleRow, ...] = (
    (1, "SIM-AI4-020", SignalType.AI_CURRENT, ("+", "-")),
    (2, "SIM-DI8-024", SignalType.DI, ("I", "M")),
    (3, "SIM-RTD4-PT100", SignalType.RTD, ("+R", "-R")),
)


def _pins(*names: str) -> tuple[tuple[str, PortRole], ...]:
    return tuple((name, PortRole.GENERIC) for name in names)


def _channel_pin(base: str, number: int) -> str:
    """`base`'s pin name for channel `number`, numbered as the device prints it.

    A letter base is suffixed (`"I"` -> `"I1"`), a sign base is prefixed (`"+"` -> `"1+"`), and
    a signed-letter base keeps the letter and numbers between it and the sign (`"+R"` ->
    `"R1+"`). Distinct per channel, so two ports of one module never print the same text
    (PORT_DESIGNATION_DUPLICATE, decision 0077).
    """
    if base in ("+", "-"):
        return f"{number}{base}"
    if base in ("+R", "-R"):
        return f"R{number}{base[0]}"
    return f"{base}{number}"


def _catalogue(kit: Kit) -> Catalogue:
    """Every part of the cabinet, declared once."""
    coil = (FunctionKind.COIL, _pins("A1", "A2"))
    terminal_side = (("internal", PortRole.INTERNAL), ("external", PortRole.EXTERNAL))
    specs = (
        PartSpec(
            "psu",
            "SIM-PSU-24VDC-5A",
            "G",
            PartCategory.GENERIC,
            {"output": (FunctionKind.SUPPLY, _pins("+24V", "0V"))},
        ),
        PartSpec(
            "fuse-2a",
            "SIM-FUSE-2A",
            "F",
            PartCategory.PROTECTION,
            {"element": (FunctionKind.PROTECTION, _pins("1", "2"))},
            ((("element", "1"), ("element", "2"), LinkKind.CONDUCTIVE),),
        ),
        PartSpec(
            "contactor-1no",
            "SIM-CONTACTOR-9A-1NO",
            "K",
            PartCategory.ELECTROMECHANICAL,
            {"coil": coil, "no_1": (FunctionKind.CONTACT_NO, _pins("13", "14"))},
            ((("no_1", "13"), ("no_1", "14"), LinkKind.SWITCHED),),
        ),
        PartSpec(
            "contactor-1co",
            "SIM-CONTACTOR-9A-1CO",
            "K",
            PartCategory.ELECTROMECHANICAL,
            {"coil": coil, "co_1": (FunctionKind.CONTACT_CO, _pins("11", "12", "14"))},
            (
                (("co_1", "11"), ("co_1", "14"), LinkKind.SWITCHED),
                (("co_1", "12"), ("co_1", "14"), LinkKind.SWITCHED),
            ),
        ),
        PartSpec(
            "terminal",
            "SIM-TERMINAL-2.5MM",
            "X",
            PartCategory.TERMINAL,
            {"terminal": (FunctionKind.TERMINAL, terminal_side)},
            ((("terminal", "internal"), ("terminal", "external"), LinkKind.CONDUCTIVE),),
        ),
        PartSpec("rack", "SIM-RACK-8", "A", PartCategory.PLC_MODULE),
        PartSpec("cable", "SIM-CABLE-2X0.75-SH", "W", PartCategory.CABLE),
        PartSpec(
            "pt",
            "SIM-PT-4-20MA",
            "B",
            PartCategory.GENERIC,
            {"signal": (FunctionKind.SENSOR, _pins("+", "-"))},
        ),
        PartSpec(
            "rtd",
            "SIM-PT100-2W",
            "B",
            PartCategory.GENERIC,
            {"signal": (FunctionKind.SENSOR, _pins("1", "2"))},
        ),
        PartSpec(
            "pb",
            "SIM-PB-NO",
            "S",
            PartCategory.GENERIC,
            {"signal": (FunctionKind.SWITCH, _pins("1", "2"))},
        ),
    )
    catalogue = {spec.key: kit.part(spec) for spec in specs}
    kit.facet(
        CableProductFacet,
        ("cable", "cable_product"),
        subject=catalogue["cable"].part.id,
        core_colours=("BN", "BU"),
        gauge_mm2=Decimal("0.75"),
        shielded=True,
    )
    return catalogue


def _terminal(kit: Kit, bundle: PartBundle, strip: Ref, group: str, index: int) -> Ref:
    """One terminal of `strip`, with its `terminal` facet."""
    key = (*strip.key, f"{group.lower()}-{index}")
    terminal = kit.stamp(bundle, key, Slot(None, parent=strip.item))
    kit.facet(TerminalFacet, (*key, "terminal"), subject=terminal.item, group=group, index=index)
    return terminal


def _supply(kit: Kit, catalogue: Catalogue, things: Things) -> None:
    """The supply, the fuse, the two pump starters and the spare, and the 24 V wiring."""
    things["g1"] = g1 = kit.stamp(catalogue["psu"], ("g1",), Slot("G1"))
    things["f1"] = f1 = kit.stamp(catalogue["fuse-2a"], ("f1",), Slot("F1"))
    things["k1"] = k1 = kit.stamp(catalogue["contactor-1no"], ("k1",), Slot("K1"))
    things["k2"] = k2 = kit.stamp(catalogue["contactor-1co"], ("k2",), Slot("K2"))
    things["k3"] = kit.stamp(catalogue["contactor-1no"], ("k3",), Slot("K3", installed=False))
    kit.wire(g1.port("output", "+24V"), f1.port("element", "1"), ("w-24v-in",))
    for starter in (k1, k2):
        kit.wire(f1.port("element", "2"), starter.port("coil", "A1"), ("w-24v", *starter.key))
        kit.wire(g1.port("output", "0V"), starter.port("coil", "A2"), ("w-0v", *starter.key))
    kit.net(
        "P24V",
        (
            g1.port("output", "+24V"),
            f1.port("element", "1"),
            f1.port("element", "2"),
            k1.port("coil", "A1"),
            k2.port("coil", "A1"),
        ),
        net_class=NetClass.POWER,
        potential="+24V",
    )
    kit.net(
        "N0V",
        (g1.port("output", "0V"), k1.port("coil", "A2"), k2.port("coil", "A2")),
        net_class=NetClass.POWER,
        potential="0V",
    )


def _strips(kit: Kit, catalogue: Catalogue, things: Things) -> None:
    """Strip `X1` (power distribution, one `L1` jumper) and strip `X2` (field wiring)."""
    x1 = things["x1"] = kit.container(("x1",), "X1")
    x2 = things["x2"] = kit.container(("x2",), "X2")
    for group, index in _L1_TERMINALS:
        things[f"x1/{group}-{index}"] = _terminal(kit, catalogue["terminal"], x1, group, index)
    for group in _FIELD_PAIRS:
        for index in (1, 2):
            things[f"x2/{group}-{index}"] = _terminal(kit, catalogue["terminal"], x2, group, index)
    inside, outside = "internal", "external"
    l1a, l1b = things["x1/L1-1"], things["x1/L1-2"]
    kit.wire(
        l1a.port("terminal", inside),
        l1b.port("terminal", inside),
        ("x1", "jumper-l1"),
        ConductorKind.JUMPER,
    )
    kit.wire(
        things["x1/L2-1"].port("terminal", inside),
        things["k1"].port("no_1", "13"),
        ("w-l2-k1",),
    )
    kit.wire(
        things["x1/L3-1"].port("terminal", inside),
        things["k2"].port("co_1", "11"),
        ("w-l3-k2",),
    )
    for group, ends in (
        ("L1", (l1a, l1b)),
        ("L2", (things["x1/L2-1"],)),
        ("L3", (things["x1/L3-1"],)),
        ("PE", (things["x1/PE-1"],)),
    ):
        kit.net(
            group,
            tuple(t.port("terminal", side) for t in ends for side in (inside, outside)),
            net_class=NetClass.PE if group == "PE" else NetClass.POWER,
            potential=group,
        )


def _module(kit: Kit, rack: Ref, row: _ModuleRow) -> Ref:
    """A rack module in its slot, its channel templates and `plc_channel` facets."""
    position, mpn, signal, pins = row
    count = 8 if signal is SignalType.DI else 4
    functions = {
        f"ch{number}": (
            FunctionKind.PLC_CHANNEL,
            _pins(*(_channel_pin(base, number) for base in pins)),
        )
        for number in range(1, count + 1)
    }
    bundle = kit.part(
        PartSpec(f"module-{mpn.lower()}", mpn, "A", PartCategory.PLC_MODULE, functions)
    )
    for number in range(1, count + 1):
        kit.facet(
            PlcChannelFacet,
            (*bundle.part.key, f"ch{number}", "plc_channel"),
            subject=template_of(bundle, f"ch{number}"),
            signal=signal,
            channel=number,
        )
    key = (*rack.key, f"m{position}")
    return kit.stamp(bundle, key, Slot(f"A1-{position}", parent=rack.item, position=position))


def _rack(kit: Kit, catalogue: Catalogue, things: Things) -> None:
    """Rack `A1` and its three modules."""
    things["a1"] = rack = kit.stamp(catalogue["rack"], ("a1",), Slot("A1"))
    for row in _MODULES:
        things[f"a1-{row[0]}"] = _module(kit, rack, row)


def _request(kit: Kit, device: Ref, asked: tuple[str, SignalType, int], channel: Ref) -> None:
    """The device's `signal` function asks for a channel and holds the one the pass gives it."""
    name, signal, priority = asked
    function_key = device.function_keys["signal"]
    kit.facet(
        PlcRequestFacet,
        (*function_key, "plc_request"),
        subject=device.function("signal"),
        signal=signal,
        signal_name=name,
        priority=priority,
    )
    kit.facet(
        PlcBindingFacet,
        (*function_key, "plc_binding"),
        subject=device.function("signal"),
        channel=channel.function("ch1"),
    )


def _field(kit: Kit, catalogue: Catalogue, things: Things) -> None:
    """Three field devices: two on cables, one panel-wired; each leg is its own declared net."""
    for name, part, designation in (("b1", "pt", "B1"), ("b2", "rtd", "B2"), ("s1", "pb", "S1")):
        things[name] = kit.stamp(catalogue[part], (name,), Slot(designation))
    for name, designation in (("w1", "W1"), ("w2", "W2")):
        things[name] = kit.stamp(catalogue["cable"], (name,), Slot(designation))
    b1, b2, s1 = things["b1"], things["b2"], things["s1"]
    kit.facet(
        ScalingFacet,
        (*b1.function_keys["signal"], "scaling"),
        subject=b1.function("signal"),
        unit="bar",
        raw_min=4,
        raw_max=20,
        eng_min=Decimal(0),
        eng_max=Decimal(10),
    )
    legs = (
        (
            "b1",
            ("+", "-"),
            "w1",
            "PT01",
            "a1-1",
            (_channel_pin("+", 1), _channel_pin("-", 1)),
            "PT01_LOOP",
        ),
        (
            "b2",
            ("1", "2"),
            "w2",
            "TT01",
            "a1-3",
            (_channel_pin("+R", 1), _channel_pin("-R", 1)),
            "TT01_LOOP",
        ),
        (
            "s1",
            ("1", "2"),
            None,
            "S1",
            "a1-2",
            (_channel_pin("I", 1), _channel_pin("M", 1)),
            "S1_LOOP",
        ),
    )
    for device, pins, cable, group, module, channel_pins, loop in legs:
        for index, sign in enumerate("+-", start=1):
            terminal = things[f"x2/{group}-{index}"]
            field_port = things[device].port("signal", pins[index - 1])
            landing = terminal.port("terminal", "external")
            if cable is None:
                kit.wire(field_port, landing, (device, "wire", str(index)))
            else:
                kit.core(things[cable], index, (field_port, landing))
            channel_port = things[module].port("ch1", channel_pins[index - 1])
            panel = terminal.port("terminal", "internal")
            kit.wire(panel, channel_port, (*terminal.key, "panel"))
            kit.net(
                f"{loop}{sign}",
                (field_port, landing, panel, channel_port),
                net_class=NetClass.SIGNAL,
            )
    _request(kit, b1, ("PT01_Pressure", SignalType.AI_CURRENT, 1), things["a1-1"])
    _request(kit, b2, ("TT01_Temp", SignalType.RTD, 2), things["a1-3"])
    _request(kit, s1, ("Start_PB", SignalType.DI, 1), things["a1-2"])


def build_cabinet() -> Draft:
    """Build the WP17 cabinet fixture: a `Draft`, not yet frozen.

    The invented design (every item but the terminals is numbered by hand, and a terminal
    is named by its `terminal` facet; only the harness leaves an item, its cable, for the
    numbering pass):

    - Power supply `G1` (24 V DC) feeds fuse `F1` (`SIM-FUSE-2A`, a `conductive` link) and two
      pump starters on different parts: `K1` (`SIM-CONTACTOR-9A-1NO`, coil and `no_1`) and `K2`
      (`SIM-CONTACTOR-9A-1CO`, coil and `co_1` with `switched` links); declared nets `P24V` and
      `N0V`. `K3` is a spare `K1` part, `installed=False`, with no conductor: it stays in the
      drawings and drops out of `bom_lines`.
    - Terminal strip `X1` (power distribution): terminals `(L1,1) (L1,2) (L2,1) (L3,1) (PE,1)`;
      a `jumper` bridges the two `L1` terminals' `internal` ports (a jumper between different
      phases would short two declared nets), and declared nets `L1`, `L2`, `L3`, `PE` follow
      the terminals; `L2` and `L3` also feed `K1` and `K2`.
    - Terminal strip `X2` (field wiring): three pairs `PT01`, `TT01`, `S1`; field conductors
      land on `external` ports, panel wires to the PLC on `internal` ports.
    - PLC rack `A1` with modules `A1-1` (4 x `AI_CURRENT`), `A1-2` (8 x `DI`) and `A1-3`
      (4 x `RTD`); `position` is the slot.
    - Field devices `B1` (pressure transmitter, `plc_request` and `scaling`, cable `W1`), `B2`
      (RTD probe, cable `W2`) and `S1` (start pushbutton, two `wire` conductors, no cable).
      The bindings are authored as `plc_allocation` would write them (decision 0020), so the
      PLC report has devices in it; declared nets `PT01_LOOP+/-`, `TT01_LOOP+/-` and
      `S1_LOOP+/-` each hold exactly one physical net.
    - Every item placed at location node `+C1`.
    """
    kit = Kit("tests/usecases/cabinet.py")
    catalogue = _catalogue(kit)
    things: Things = {}
    _supply(kit, catalogue, things)
    _strips(kit, catalogue, things)
    _rack(kit, catalogue, things)
    _field(kit, catalogue, things)
    enclosure = kit.node("c1", Aspect.LOCATION, "C1", "main enclosure")
    for thing in things.values():
        kit.place(thing, enclosure)
    return kit.draft
