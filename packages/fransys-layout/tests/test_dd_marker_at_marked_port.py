"""A link marker stands at the side of the port it marks, on the page it stands on.

A terminal's branch marker leaves by the symbol port that carries no drawn wire (`_free_side`).
"Drawn" means drawn on THIS page. Before the fix `_linked` passed `routed`, the ports of every
"""

from functools import cache
from typing import TYPE_CHECKING, Any

import fransys as fr
import fransys_parts
import pytest
from _drawn_pages import drawn_pages
from _model_build_cover import cabinet_document, layout_trigger_document
from dd_chain_fixtures import markers_in
from fransys_author.design import Design

from fransys_model.kernel import Severity
from fransys_model.layout import DrawingSet, Page, layout_of

if TYPE_CHECKING:
    from fransys_layout.drawing import DrawnSymbol

_PROJECT: dict[str, Any] = {
    "title": "Marker at port",
    "number": "P-1009",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}
# (strip, group) of each terminal, in author order; the first is the hub
_PUMPS = (("X1", 1), ("X3", 2), ("X3", 3))  # the hub is beside -X3:1 in the top-level set only
_PAIR = (("X1", 1), ("X3", 2), ("X3", 2))  # -X3:1 and -X3:2 are beside each other in both sets


@cache
def _built(spec: tuple[tuple[str, int], ...], *, pair: bool = False):
    """A cabinet unit `+C1` with one boundary terminal per `spec` entry, the first wired to each
    other on the inner side (one PE net). Outer sides run to another location. Three relays stand
    in each group, so a group's terminal is on a page of its own in the unit's set. With `pair` the
    second and third terminals are also wired to each other. Returns the model and the terminals'
    designations, in `spec` order."""
    parts = fransys_parts.load("demo_parts")
    d = Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    cab = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    cab.revision(1, date="2026-01-01", text="First release", created="XX")
    c1 = cab.location("C1", "Cabinet")
    groups = {n: cab.group(f"G{n}", f"Group {n}") for _, n in spec}
    strips = {name: cab.strip(name, at=c1) for name in dict.fromkeys(n for n, _ in spec)}
    terminals = [strips[name].terminal("DEMO-TB-2.5-TWIN", group=groups[n]) for name, n in spec]
    earth, blue = cab.wiring(colour="GNYE", gauge="2.5"), cab.wiring(colour="BU", gauge="0.5")
    for other in terminals[1:]:
        earth(terminals[0].inner, other.inner)
    if pair:
        earth(terminals[1].inner, terminals[2].inner)
    outside, field = d.location("EXT", "External"), d.group("FLD", "Field")
    for n, terminal in enumerate(terminals, start=1):  # every outer side runs to another location
        end = d.strip(f"XE{n}", at=outside).terminal("DEMO-TB-2.5", group=field)
        cable = d.cable("DEMO-CBL-4G1.5", tag=f"W{n}", at=outside, group=field)
        cable.core(1, terminal.outer, end.outer)
    for terminal in terminals:
        cab.boundary(terminal)
    for tag, n in enumerate(3 * sorted({n for _, n in spec}), start=1):
        relay = cab.item("DEMO-RLY-2CO-24", tag=f"K{tag}", at=c1, group=groups[n])
        blue(relay.fn("coil")["A1"], relay.fn("coil")["A2"])
        for contact, pins in (("co_1", ("11", "14")), ("co_2", ("21", "24"))):  # layout-0112
            blue(relay.fn(contact)[pins[0]], relay.fn(contact)[pins[1]])
    result = fr.build(parts, d.draft(), layout_trigger_document("demo-pump-cabinet"), cabinet_document(outside))
    assert not [f for f in result.findings if f.severity is Severity.ERROR]
    return result, [f"-{name}:{n}" for name, n in (("X1", 1), ("X3", 1), ("X3", 2))]


@pytest.fixture(autouse=True)
def _one_build_per_test():
    """Each test builds its own model, so the finding sweep counts every node's build (a cached build counts for the first test only)."""
    _built.cache_clear()


def _build(spec: tuple[tuple[str, int], ...], *, pair: bool = False):
    """`_built`'s model and designations."""
    result, tags = _built(spec, pair=pair)
    return result.model, tags


def test_every_branch_marker_the_loop_makes_has_room() -> None:
    """The strap's tag pair is planned by the cut and reserved by the placement: no MARKER_UNPLACED (layout-0508)."""
    for spec, pair in ((_PUMPS, False), (_PAIR, True)):
        codes = [f.code for f in _built(spec, pair=pair)[0].findings]
        assert "MARKER_UNPLACED" not in codes
        assert codes.count("CONNECTION_NOT_DRAWN") == 0


def _point_under(drawing, tag: str):
    """The point text of the terminal printed `tag` (`-X3:1`): the point `1` standing nearest the strip tag `-X3` of its run (STRIP-TAG-ONCE)."""
    strip, _, point = tag.partition(":")
    texts = [t for t in drawing.texts if t.kind == "TAG"]
    runs = [t for t in texts if t.owner is None and t.text == strip]
    points = [t for t in texts if t.owner and t.text == point]
    return min(points, key=lambda p: min(abs(p.box.x - r.box.x) + abs(p.box.y - r.box.y) for r in runs), default=None) if runs else None


def _own_branches(model, tag: str) -> list[tuple[DrawnSymbol, DrawnSymbol]]:
    """The markers in a unit's own set standing at the terminal printed `tag`, with that terminal.

    A marker names no subject, so it belongs to the terminal whose x it stands on.
    """
    pages, sets = layout_of(model, Page), layout_of(model, DrawingSet)
    found: list[tuple[DrawnSymbol, DrawnSymbol]] = []
    for page, drawing in drawn_pages(model).items():
        if sets[pages[page].drawing_set].unit is None:
            continue
        text = _point_under(drawing, tag)
        if text is None:  # the unit's set may span pages: only the terminal's own page counts
            continue
        terminal = min(
            (s for s in drawing.symbols if s.key == "terminal"),
            key=lambda s: abs(s.x - text.box.x) + abs(s.y - text.box.y),
        )
        found += [(m, terminal) for m in markers_in(drawing) if m.x == terminal.x]
    return found


def _inward(model, tag: str) -> int:
    """The marker's y less its terminal's y, signed so that above zero is the inner port's
    side: the inner port faces N when the terminal is `R0`, S when it is `R180`."""
    found = _own_branches(model, tag)
    assert found, f"no branch marker stands at {tag}"
    ((marker, terminal),) = found
    assert terminal.orient in ("R0", "R180")
    return (marker.y - terminal.y) * (-1 if terminal.orient == "R0" else 1)


def test_a_marker_stands_at_its_ports_side_though_its_wire_is_drawn_in_another_set() -> None:
    """-X3:1 is joined to the hub by a wire drawn in the top-level set only: on its own page the
    inner port has no wire, so its branch marker stands at the inner port."""
    model, (_hub, near, _far) = _build(_PUMPS)
    assert _inward(model, near) > 0, "the inner port's marker leaves by the outer port's side"


def test_control_a_port_with_no_other_wire_stands_at_its_own_side() -> None:
    """-X3:2 has no kept wire anywhere: its branch marker stands at the inner port. Must pass on
    the base and after the fix."""
    model, (_hub, _near, far) = _build(_PUMPS)
    assert _inward(model, far) > 0


def test_two_pumps_markers_for_one_pe_net_stand_at_the_same_side() -> None:
    """Pump 1's -X3:1 and pump 2's -X3:2 differ only in where the hub's wire is drawn: their
    markers stand at the same side of their terminals, and at the same distance."""
    model, (_hub, near, far) = _build(_PUMPS)
    assert _inward(model, near) == _inward(model, far)


def test_a_terminal_whose_inner_wire_is_drawn_on_the_page_leaves_by_the_outer_port() -> None:
    """Kept: -X3:1 and -X3:2 stand beside each other with a wire drawn between them on the
    page, and the star's one marker for that pair stands at whichever sorts first. That inner
    port carries a wire drawn here, so the marker leaves by the free outer port."""
    model, (_hub, near, far) = _build(_PAIR, pair=True)
    found = _own_branches(model, near) + _own_branches(model, far)
    assert len(found) == 1
    port = near if _own_branches(model, near) else far
    assert _inward(model, port) < 0
