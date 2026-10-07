"""Small invented designs and readers for the D1/D2 tests (layout deep dive, F5-C part A).

Designs are built through the author facade on `examples/demo-parts` (invented parts only), then
laid out by `fr.build`. The readers look at the laid-out records only: `SymbolPlacement`,
`Route` and `LinkMarker`, found by the function key the author gave (`("XA", "terminal", "1",
"fn", "terminal")`, `("Q1", "fn", "element")`) and the port's marking.
"""

from itertools import pairwise
from typing import TYPE_CHECKING, Any

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import layout_trigger_document

from fransys_model.layout import LinkMarker, Route, SymbolPlacement, layout_of
from fransys_model.vocab.tables import functions, ports

if TYPE_CHECKING:
    from fransys_model.kernel import Model

PROJECT: dict[str, Any] = {
    "title": "Chains",
    "number": "P-1",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}
TERMINAL = "DEMO-TB-2.5"
MCB = "DEMO-MCB-C6"


def design() -> tuple[Any, Any]:
    """The demo parts and a fresh `Design` with its project block."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    return parts, d


def build(parts: Any, d: Any) -> Any:
    """Build and lay out; the result carries `model` and `findings`."""
    return fr.build(parts, d.draft(), layout_trigger_document())


def contactor_with_pole_one_wired(*, relays: bool) -> Any:
    """K1 (3 poles), only pole 1 wired XA:1 - K1:main - XB:1, and three 2CO relays when `relays`.

    Each relay's coil and first contact are fed from one XA terminal and end at an XB terminal
    of their own. Built and laid out (`build`).
    """
    parts, d = design()
    c, g = d.location("C1", "Cabinet"), d.group("G1", "Group")
    top, bottom = d.strip("XA", at=c), d.strip("XB", at=c)
    wire = d.wiring(colour="BU", gauge="0.75")
    k1 = d.item("DEMO-CTR-3P-24", tag="K1", at=c, group=g)
    wire(top.terminal(TERMINAL, group=g).outer, k1.fn("main")["1"])
    wire(k1.fn("main")["2"], bottom.terminal(TERMINAL, group=g).inner)
    if relays:
        feed = top.terminal(TERMINAL, group=g)
        for tag in ("K2", "K3", "K4"):
            relay = d.item("DEMO-RLY-2CO-24", tag=tag, at=c, group=g)
            wire(feed.inner, relay.fn("coil")["A1"])
            wire(relay.fn("coil")["A2"], bottom.terminal(TERMINAL, group=g).inner)
            wire(feed.inner, relay.fn("co_1")["11"])
            wire(relay.fn("co_1")["14"], bottom.terminal(TERMINAL, group=g).inner)
            wire(feed.inner, relay.fn("co_2")["21"])  # layout-0112: an unwired contact is not drawn
            wire(relay.fn("co_2")["24"], bottom.terminal(TERMINAL, group=g).inner)
    return build(parts, d)


def three_breakers(*, daisy: bool) -> Model:
    """Q1..Q3 side by side under one feed XA:1, each ending in its own terminal XB:n, laid out.

    The feed fans to each breaker's `1`, or with `daisy` feeds Q1:1, which chains to Q2:1 and on.
    """
    parts, d = design()
    c, g = d.location("C1", "Cabinet"), d.group("G1", "Group")
    feed, ends = d.strip("XA", at=c).terminal(TERMINAL, group=g), d.strip("XB", at=c)
    wire = d.wiring(colour="BU", gauge="0.75")
    qs = [d.item(MCB, tag=f"Q{n}", at=c, group=g) for n in (1, 2, 3)]
    for q in qs:
        wire(q["2"], ends.terminal(TERMINAL, group=g).inner)
    if daisy:
        wire(feed.outer, qs[0]["1"])
        wire(qs[0]["1"], qs[1]["1"])
        wire(qs[1]["1"], qs[2]["1"])
    else:
        for q in qs:
            wire(feed.outer, q["1"])
    return build(parts, d).model


def terminal_chain(n: int) -> Model:
    """A strip X1 of `n` terminals in one group, wired inner to inner in a chain, laid out."""
    parts, d = design()
    strip = d.strip("X1", at=d.location("C1", "Cabinet"))
    group = d.group("PLC", "PLC")
    terminals = [strip.terminal(TERMINAL, group=group) for _ in range(n)]
    wire = d.wiring(colour="BU", gauge="0.5")
    for one, other in pairwise(terminals):
        wire(one.inner, other.inner)
    return build(parts, d).model


def terminal_key(strip: str, index: int) -> tuple[str, ...]:
    """The function key of terminal `index` of strip `strip`."""
    return (strip, "terminal", str(index), "fn", "terminal")


def placed(model: Model, *key: str) -> SymbolPlacement:
    """The one placement of the function keyed `key`."""
    found = [
        p
        for p in layout_of(model, SymbolPlacement).values()
        if functions(model)[p.function].key == key
    ]
    assert len(found) == 1, f"{key}: {len(found)} placements"
    return found[0]


def route_between(
    model: Model, a: tuple[tuple[str, ...], str], b: tuple[tuple[str, ...], str]
) -> Route:
    """The one route whose two ends are the ports `(function key, marking)` `a` and `b`."""

    def end(route_port: Any) -> tuple[tuple[str, ...], str]:
        record = ports(model)[route_port]
        return functions(model)[record.function].key, record.name

    found = [r for r in layout_of(model, Route).values() if {end(r.a), end(r.b)} == {a, b}]
    assert len(found) == 1, f"{a} - {b}: {len(found)} routes"
    return found[0]


def markers_on(model: Model, key: tuple[str, ...], marking: str) -> list[LinkMarker]:
    """Every link marker standing on the port `marking` of the function keyed `key`."""
    return [
        m
        for m in layout_of(model, LinkMarker).values()
        if ports(model)[m.port].name == marking
        and functions(model)[ports(model)[m.port].function].key == key
    ]
