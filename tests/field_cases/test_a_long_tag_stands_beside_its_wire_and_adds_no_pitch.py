"""Field case: a long tag stands in a body corner clear of its wire and never widens the pitch.

The engineering shape: three lamps in three parallel circuits off one terminal strip. One build
names them `H1`..`H3`, the other gives each a long designation.

The bug: the designation's size was folded into each symbol's footprint, so the long tags pushed
the lamps apart; the tag was a reserved room, not a text placed after the symbols.
The rule: a tag is placed after the symbols and wires, in the first body corner where it fits
(TEXT-CANDIDATES, layout-0371, the 2026-10-18 corners ruling, R327). It reserves no room and adds
no pitch; with no free corner it gives `LABEL_UNPLACED`.
"""

from typing import TYPE_CHECKING

import fransys as fr
import pytest
from _drawn_pages import drawn_pages
from _model_build_cover import cabinet_document
from fransys.colours import BU

if TYPE_CHECKING:
    from fransys_layout.drawing import Drawing, DrawnWire
    from fransys_model.kernel import Model

LAMPS = 3


def _build(names: tuple[str, ...]) -> fr.BuildResult:
    """Lamps `names` each between two terminals of strip `X1`."""
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Tags", number="P-3", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-19", text="First issue", created="XX")
    cabinet = d.location("CAB", "Cabinet")
    strip = d.terminal_strip("X1", "DEMO-TB-2.5")
    with d.function("G1", "Lamps"):
        for k, name in enumerate(names):
            lamp = d.device(name, "DEMO-LAMP-24")
            d.detail.wire(strip[2 * k + 1], lamp[1], wire=(BU, 0.5))
            d.detail.wire(lamp[2], strip[2 * k + 2], wire=(BU, 0.5))
    return fr.build(d, cabinet_document(cabinet))


@pytest.fixture(scope="module")
def short() -> Model:
    return _build(tuple(f"H{k}" for k in range(1, LAMPS + 1))).model


@pytest.fixture(scope="module")
def long() -> Model:
    return _build(tuple(f"HLAMP-NORTH-WING-{k}" for k in range(1, LAMPS + 1))).model


def _page(model: Model) -> Drawing:
    ((page,),) = [[d] for d in drawn_pages(model).values()]
    return page


def _lamp_xs(page: Drawing) -> list[int]:
    return sorted(s.x for s in page.symbols if "lamp" in s.key)


def _crosses(box, wire: DrawnWire) -> bool:
    """Whether a wire piece passes through the open interior of `box`."""
    for (x0, y0), (x1, y1) in zip(wire.points, wire.points[1:], strict=False):
        lo_x, hi_x, lo_y, hi_y = min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)
        if lo_x < box.x + box.w and hi_x > box.x and lo_y < box.y + box.h and hi_y > box.y:
            return True
        if lo_x == hi_x and box.x < lo_x < box.x + box.w and lo_y < box.y + box.h and hi_y > box.y:
            return True
        if lo_y == hi_y and box.y < lo_y < box.y + box.h and lo_x < box.x + box.w and hi_x > box.x:
            return True
    return False


def test_a_long_tag_adds_no_pitch(short: Model, long: Model) -> None:
    """The lamps stand at the same x whatever their designations print."""
    assert len(_lamp_xs(_page(short))) == LAMPS
    assert _lamp_xs(_page(long)) == _lamp_xs(_page(short))


def test_a_long_tag_touches_no_wire(long: Model) -> None:
    """No lamp tag box meets any wire of its page."""
    page = _page(long)
    tags = [t for t in page.texts if t.kind == "TAG"]
    assert len(tags) >= LAMPS
    assert [t.text for t in tags if any(_crosses(t.box, w) for w in page.wires)] == []
