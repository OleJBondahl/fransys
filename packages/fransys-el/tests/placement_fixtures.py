"""Models and symbol kits the problem-builder tests share: a demo design and planted features."""

from typing import TYPE_CHECKING, NamedTuple

import fransys as fr
from fransys.colours import BU
from fransys_el import Conventions, build, options
from fransys_el.placement_ids import symbol_key
from fransys_el.placement_kit import Pick, SymbolKit

from electrical_symbols import LIBRARY
from fransys_layout.core import Placement, build_flow, order_blocks
from fransys_layout.core.blocks import assign_blocks
from fransys_layout.core.cut import cut_pages
from fransys_layout.core.place import place_pages
from fransys_model.derive import item_designation
from fransys_model.vocab import functions, ports

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_el.kit_keys import PickKey

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Function

__all__ = ["demo_model", "kit_for", "placed", "planted_model", "sid"]

_FEATURES = ("strip", "relay", "three_pole", "generic", "unit", "mate")


class _Feed(NamedTuple):
    """The planted unit's interface: one strip, whose terminals are its boundary."""

    X1: fr.TerminalStrip


@fr.unit("planted-feed", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _feed(d: fr.Design) -> _Feed:
    return _Feed(d.terminal_strip("X1", "DEMO-TB-2.5", 2, interface=True))


def demo_model() -> Model:
    """A terminal strip, a relay, a 3-pole breaker, a motor and a 16-channel PLC input module."""
    d = fr.design("demo_parts")
    g1 = d.device("G1", "DEMO-PSU-24")
    dc = d.dc_supply("24VDC", g1.output)
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 3)
    s1 = d.device("S1", "DEMO-PB-NO")
    k1 = d.device("K1", "DEMO-RLY-2CO-24")
    q1 = d.device("Q1", "DEMO-MCB-3P")
    m1 = d.device("M1", "DEMO-MOTOR-4KW")
    a1 = d.device("A1", "DEMO-PLC-DI-16")
    with d.function("CTRL", "Relay control"):
        d.series(dc.plus, s1.sw, k1.coil, dc.minus, wire=(BU, 0.75))
        d.series(dc.plus, k1.co_1.no, a1, wire=(BU, 0.75))
    with d.function("POWER", "Motor feed"):
        d.series(x1, q1.element, m1.motor, wire=2.5)
    return fr.build(d).model


def planted_model(*, crossed: bool = False, **features: bool) -> Model:
    """A design with each planted feature on or off, all on by default.

    The features are strip, relay, three_pole, generic, unit and mate. `crossed=True` swaps
    phases 1 and 2 between the two 3-pole breakers of `three_pole`.
    """
    unknown = set(features) - set(_FEATURES)
    if unknown:
        msg = f"planted_model has no feature {sorted(unknown)}"
        raise ValueError(msg)
    on = dict.fromkeys(_FEATURES, True) | features
    d = fr.design("demo_parts")
    g1 = d.device("G1", "DEMO-PSU-24")
    dc = d.dc_supply("24VDC", g1.output)
    if on["strip"]:
        x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 3)
        with d.function("FEED", "Strip feed"):
            d.series(dc.plus, x1[1], dc.minus, wire=(BU, 0.75))
    if on["relay"]:
        s1 = d.device("S1", "DEMO-PB-NO")
        k1 = d.device("K1", "DEMO-RLY-2CO-24")
        with d.function("RELAY", "Relay"):
            d.series(dc.plus, s1.sw, k1.coil, dc.minus, wire=(BU, 0.75))
            d.series(dc.plus, k1.co_1.no, k1.co_2.no, dc.minus, wire=(BU, 0.75))
    if on["three_pole"]:
        q1 = d.device("Q1", "DEMO-MCB-3P")
        q2 = d.device("Q2", "DEMO-MCB-3P")
        with d.function("BREAKERS", "Breaker pair"):
            if crossed:
                d.detail.wire(q1.element["2"], q2.element["3"], wire=(BU, 2.5))
                d.detail.wire(q1.element["4"], q2.element["1"], wire=(BU, 2.5))
                d.detail.wire(q1.element["6"], q2.element["5"], wire=(BU, 2.5))
            else:
                d.series(q1.element, q2.element, wire=2.5)
    if on["generic"]:
        b1 = d.device("B1", "DEMO-SENSOR-2W")
        a2 = d.device("A2", "DEMO-PLC-DI-2")
        with d.function("SENSE", "Two-wire sensor"):
            d.detail.wire(g1.output["+"], b1.sig["1"], wire=(BU, 0.75))
            d.detail.wire(b1.sig["2"], a2.di_1["1"], wire=(BU, 0.75))
    if on["unit"]:
        io = d.add(_feed, "U1")
        with d.function("FIELD", "Unit feed"):
            d.series(dc.plus, io.X1[1], dc.minus, wire=(BU, 0.75))
    if on["mate"]:
        j1 = d.device("J1", "DEMO-CONN-2P")
        j2 = d.device("J2", "DEMO-CONN-2P")
        d.mate(j1.x1, j2.x1)
        with d.function("MATED", "Mated feed"):
            d.detail.wire(g1.output["+"], j1.x1["1"], wire=(BU, 0.75))
            d.detail.wire(g1.output["-"], j2.x1["1"], wire=(BU, 0.75))
    return fr.build(d).model


# Function name -> (symbol key, poles, model port name -> symbol port name). A row serves every
# function of that name; `co_1` and `co_2` have different port names, so each has its own row.
_SYMBOLS: dict[str, tuple[str, int, dict[str, str]]] = {
    "input": ("generic-box", 1, {"L": "L", "N": "N"}),
    "output": ("psu", 1, {"+": "plus", "-": "minus"}),
    "sw": ("push-button", 1, {"A": "in", "B": "out"}),
    "coil": ("coil", 1, {"A1": "in", "A2": "out"}),
    "co_1": ("change-over-contact", 1, {"11": "com", "12": "nc", "14": "no"}),
    "co_2": ("change-over-contact", 1, {"21": "com", "22": "nc", "24": "no"}),
    "element": (
        "circuit-breaker",
        3,
        {"1": "1.in", "2": "1.out", "3": "2.in", "4": "2.out", "5": "3.in", "6": "3.out"},
    ),
    "terminal": ("terminal", 1, {"internal": "n", "external": "s"}),
    "motor": ("motor-3ph-pe", 1, {"PE": "pe", "U": "u", "V": "v", "W": "w"}),
    "sig": ("generic-box", 1, {"1": "1", "2": "2"}),
    "x1": ("connector-fixed", 1, {"1": "in", "2": "out"}),
    **{f"di_{n}": ("plc-channel", 1, {str(n): "in"}) for n in range(1, 17)},
}


def leads[V](kit: Mapping[PickKey, V]) -> dict[Id[Function], V]:
    """The entries of `kit` (or any map by pick key) keyed by a function: no pin pick."""
    return {k: v for k, v in kit.items() if k.kind == "function"}  # ty: ignore[invalid-return-type] -- the kind test narrows a union ty cannot follow


def kit_for(model: Model) -> SymbolKit:
    """The symbol kit of `model`: each function's symbol key, poles and port names."""
    all_ports = ports(model)
    found: dict[PickKey, Pick] = {}
    for function, record in functions(model).items():
        key, poles, names = _SYMBOLS[record.name]
        own = {port: names[p.name] for port, p in all_ports.items() if p.function == function}
        found[function] = Pick(key, poles, frozendict(own))
    return frozendict(found)


def sid(model: Model, text: str) -> str:
    """The symbol id (`symbol_key`) of the one function printed `<designation>.<name>`."""
    found = [
        symbol_key(model, f)
        for f, record in functions(model).items()
        if f"{item_designation(model, record.item)}.{record.name}" == text
    ]
    assert len(found) == 1, (text, len(found))
    return found[0]


def placed(model: Model, kit: SymbolKit, conventions: Conventions) -> Placement:
    """Problem, then the five stages in the order of the layout tests' `placed_of`."""
    prob, _ = build(model, kit, conventions, LIBRARY)
    opts = options(conventions, LIBRARY)
    flow = build_flow(prob, opts)
    lists = order_blocks(assign_blocks(flow, prob, opts), flow, opts)
    return place_pages(cut_pages(lists, flow, prob, opts), prob, opts)
