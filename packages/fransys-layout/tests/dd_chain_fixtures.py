"""Small invented designs and readers for the tests.

Designs are built through the author facade on `examples/demo-parts` (invented parts only), then
laid out by `fr.build`. The readers look at the page `Drawing`s of the core path
(`drawn_pages`). A drawn symbol carries no subject, so `placed` finds one by its library
key and the nearest TAG text of the designation the page prints (`-K1`, `-XA:1`); a wire is
found by the points it ends on.
"""

from itertools import pairwise
from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
import fransys_author
import fransys_parts
from _drawn_pages import drawn_pages
from _model_build_cover import cabinet_document, layout_trigger_document

from electrical_symbols import LIBRARY
from fransys_layout.symbols import library_symbol, symbol_shape

if TYPE_CHECKING:
    from fransys_layout.drawing import Drawing, DrawnSymbol, DrawnWire
    from fransys_model.kernel import Id, Model

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


def build(parts: Any, d: Any, prints: Any = None) -> Any:
    """Build and lay out; the result carries `model` and `findings`.

    The look findings (`LONE_CELL`) only name a set some document prints (model-0201): a test that
    reads them passes the location whose cabinet schematic prints the design as `prints`.
    """
    document = layout_trigger_document() if prints is None else cabinet_document(prints)
    return fr.build(parts, d.draft(), document)


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
    # layout-0218: an unwired coil is drawn nowhere; one wire to K1's own aux keeps it drawn
    wire(k1.fn("coil")["A1"], k1.fn("aux")["13"])
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


def terminal_tag(strip: str, index: int) -> str:
    """The designation text a terminal prints."""
    return f"-{strip}:{index}"


class Placed(NamedTuple):
    """A drawn symbol with the page it stands on and that page's Drawing."""

    page: Id
    drawing: Drawing
    symbol: DrawnSymbol

    @property
    def x(self) -> int:
        """The symbol's x in G."""
        return self.symbol.x

    @property
    def y(self) -> int:
        """The symbol's y in G."""
        return self.symbol.y


def placed(
    model: Model, tag: str, symbol: str, poles: int = 1, marking: str | None = None
) -> Placed:
    """The one drawn `symbol` (library key) of `poles` poles whose nearest TAG text reads `tag`.

    `marking`, if given, must be among its slot strings.

    Each text is taken by the nearest symbol of that key on its page; one symbol is the answer.
    """
    found = []
    for page, drawing in drawn_pages(model).items():
        keyed = [
            s
            for s in drawing.symbols
            if s.key == symbol
            and s.poles == poles
            and (marking is None or marking in dict(s.slots).values())
        ]
        for text in (t for t in drawing.texts if t.kind == "TAG" and t.text == tag):
            if keyed:
                nearest = min(keyed, key=lambda s: abs(s.x - text.box.x) + abs(s.y - text.box.y))
                found.append(Placed(page, drawing, nearest))
    assert len(set(found)) == 1, f"{tag} {symbol}: {len(set(found))} symbols"
    return found[0]


def body_x(p: Placed) -> tuple[int, int]:
    """The (left, right) of the symbol's body on its page, from the library's shape."""
    shape = symbol_shape(library_symbol(LIBRARY, p.symbol.key, p.symbol.poles), LIBRARY)
    assert p.symbol.orient in ("R0", "R180"), p.symbol.orient
    body = shape.body
    if p.symbol.orient == "R0":
        return p.x + body.x, p.x + body.x + body.w
    return p.x - body.x - body.w, p.x - body.x


def wires_ending_at(drawing: Drawing, point: tuple[int, int]) -> list[DrawnWire]:
    """Every wire of the page with an end on `point`."""
    return [w for w in drawing.wires if point in (w.points[0], w.points[-1])]


def pin_at(p: Placed, pin: str) -> tuple[int, int]:
    """Where the symbol's pin `pin` (a library pin id such as `1.in`) stands on the page (R0)."""
    shape = symbol_shape(library_symbol(LIBRARY, p.symbol.key, p.symbol.poles), LIBRARY)
    assert p.symbol.orient == "R0", p.symbol.orient
    turn = shape.pins[pin]
    return p.x + turn.dx, p.y + turn.dy
