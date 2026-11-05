"""Small invented designs and readers for the tests.

Designs are built through the author facade on `examples/demo-parts` (invented parts only), then
laid out by `fr.build`. The readers look at the page `Drawing`s of the core path
"""

from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
import fransys_parts
from _drawn_pages import drawn_pages, markers_in  # noqa: F401 - re-exported to the dd tests
from _model_build_cover import cabinet_document, printed
from fransys_author.design import Design

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
    d = Design(parts)
    d.project(**PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    return parts, d


def build(parts: Any, d: Any, prints: Any = None) -> fr.BuildResult:
    """Build and lay out; the result carries `model` and `findings`.

    The look findings (`LONE_CELL`) only name a set some document prints (model-0201): a test that
    reads them passes the location whose cabinet schematic prints the design as `prints`.
    """
    drafts = printed(d.draft()) if prints is None else (d.draft(), cabinet_document(prints))
    return fr.build(parts, *drafts)


def contactor_with_pole_one_wired(*, relays: bool) -> Any:
    """K1 (3 poles), only pole 1 wired XA:1 - K1:main - XB:1, and three 2CO relays when `relays`.

    Each relay's coil and first contact are fed from an XA terminal each (a point takes one conductor, R1266) and end at an XB terminal
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
    wire(k1.fn("coil")["A2"], k1.fn("aux")["14"])
    if relays:
        for tag in ("K2", "K3", "K4"):
            relay = d.item("DEMO-RLY-2CO-24", tag=tag, at=c, group=g)
            wire(top.terminal(TERMINAL, group=g).inner, relay.fn("coil")["A1"])
            wire(relay.fn("coil")["A2"], bottom.terminal(TERMINAL, group=g).inner)
            wire(top.terminal(TERMINAL, group=g).inner, relay.fn("co_1")["11"])
            wire(relay.fn("co_1")["14"], bottom.terminal(TERMINAL, group=g).inner)
            wire(top.terminal(TERMINAL, group=g).inner, relay.fn("co_2")["21"])  # layout-0112: an unwired contact is not drawn
            wire(relay.fn("co_2")["24"], bottom.terminal(TERMINAL, group=g).inner)
    return build(parts, d)


def terminal_tag(strip: str, index: int) -> str:
    """The designation text a terminal prints."""
    return f"-{strip}:{index}"


class Placed(NamedTuple):
    """A drawn symbol with the page it stands on and that page's Drawing."""

    page: Id[Any]
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


def placed(model: Model, tag: str, symbol: str, poles: int = 1, marking: str | None = None) -> Placed:
    """The one drawn `symbol` (library key) of `poles` poles whose nearest TAG text reads `tag`.

    `marking`, if given, must be among its slot strings.
    A symbol of that key is the answer when the nearest TAG text of the same device letters reads `tag`; one symbol is the answer.
    """
    found = []
    for page, drawing in drawn_pages(model).items():
        keyed = [s for s in drawing.symbols if s.key == symbol and s.poles == poles and (marking is None or marking in dict(s.slots).values())]
        tags = [t for t in drawing.texts if t.kind == "TAG" and t.text[:2] == tag[:2]]
        for sym in keyed:
            nearest = min(tags, key=lambda t: abs(sym.x - t.box.x) + abs(sym.y - t.box.y), default=None)
            if nearest is not None and nearest.text == tag:
                found.append(Placed(page, drawing, sym))
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
