"""D9 (deep dive): a link marker stands at the side of the port it marks, on the page it stands on.

A terminal's branch marker leaves by the symbol port that carries no drawn wire (C22, `_free_side`).
"Drawn" means drawn on THIS page. Before the fix `_linked` passed `routed`, the ports of every
kept connection, so a terminal whose inner port is joined to the hub by a wire that is drawn in
ANOTHER drawing set (the wire is kept: the two are side by side there) counted as wired here, so
its inner port was not free, its unwired outer port was, and the marker of the inner port moved to
the outer port's side.

The PE net here is the pump station's: three terminals, `-X1:1` (the hub) wired to `-X3:1` and to
`-X3:2` on their inner side, each `-X3` terminal in a group of its own (its own "pump") with its
outer side unwired. In the top-level set the three pins stand in one row, so `-X1:1` and `-X3:1`
are side by side and that wire is drawn there; in the unit's own set no two are, so both `-X3`
terminals take a branch marker. The two must stand alike: at the N port, the inner one.
Built through the `fransys` facade from `examples/demo-parts`, read from `layout.*` records.

The last test is the other half of C22: a terminal whose inner port carries a wire drawn on the
marker's own page still leaves by its free S port.
"""

from functools import cache
from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import system_document

from fransys_model.kernel import Id, Severity
from fransys_model.layout import (
    DrawingSet,
    LinkMarker,
    Orientation,
    Page,
    StarKind,
    SymbolPlacement,
    layout_of,
)
from fransys_model.vocab.tables import ports

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
def _build(spec: tuple[tuple[str, int], ...], *, pair: bool = False):
    """A cabinet unit `+C1` with one boundary terminal per `spec` entry, the first wired to each
    other on the inner side (one PE net). Outer sides run to another location. Three relays stand
    in each group, so a group's terminal is on a page of its own in the unit's set. With `pair` the
    second and third terminals are also wired to each other. Returns the model and the terminals'
    inner ports, in `spec` order."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    cab = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    cab.revision(1, date="2026-01-01", text="First release", created="XX")
    c1 = cab.location("C1", "Cabinet")
    groups = {n: cab.group(f"G{n}", f"Group {n}") for _, n in spec}
    strips = {name: cab.strip(name, at=c1) for name, _ in spec}
    terminals = [strips[name].terminal("DEMO-TB-2.5", group=groups[n]) for name, n in spec]
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
    result = fr.build(parts, d.draft(), system_document())
    assert not [f for f in result.findings if f.severity is Severity.ERROR]
    return result.model, [terminal.inner.id for terminal in terminals]


def _own_branches(model, port: Id) -> list[tuple[LinkMarker, SymbolPlacement]]:
    """`port`'s branch markers in a unit's own set, each with its terminal's placement there."""
    pages, sets = layout_of(model, Page), layout_of(model, DrawingSet)
    function = ports(model)[port].function
    stands = layout_of(model, SymbolPlacement).values()
    return [
        (m, next(p for p in stands if p.function == function and p.page == m.page))
        for m in layout_of(model, LinkMarker).values()
        if m.port == port
        and m.star is StarKind.BRANCH
        and sets[pages[m.page].drawing_set].unit is not None
    ]


def _inward(model, port: Id) -> int:
    """The marker's stub end less its terminal's y, signed so that above zero is the inner port's
    side: the inner port faces N when the terminal is `R0`, S when it is `R180`."""
    ((marker, terminal),) = _own_branches(model, port)
    assert terminal.orientation in (Orientation.R0, Orientation.R180)
    return (marker.y - terminal.y) * (-1 if terminal.orientation is Orientation.R0 else 1)


def test_a_marker_stands_at_its_ports_side_though_its_wire_is_drawn_in_another_set() -> None:
    """-X3:1 is joined to the hub by a wire drawn in the top-level set only: on its own page the
    inner port has no wire, so its branch marker stands at the inner port (D9)."""
    # UNDO: stages/star_markers.py:_free_side, `(facing_of[f], *end.page) not in wired` ->
    #     `facing_of[f] not in {port for port, *_ in wired}` (wired on any page or set counts):
    #     FAILED test_a_marker_stands_at_its_ports_side_though_its_wire_is_drawn_in_another_set
    #     and test_two_pumps_markers_for_one_pe_net_stand_at_the_same_side
    model, (_hub, near, _far) = _build(_PUMPS)
    assert _inward(model, near) > 0, "the inner port's marker leaves by the outer port's side"


def test_control_a_port_with_no_other_wire_stands_at_its_own_side() -> None:
    """-X3:2 has no kept wire anywhere: its branch marker stands at the inner port. Must pass on
    the base and after the fix."""
    # UNDO: stages/star_markers.py:_free_side, the last line `return end if keep else
    #     _clear_of_tag(end, world)` -> `return _side(end, world, Facing.N)` (a branch with both
    #     sides free always leaves by N): FAILED this test and
    #     test_a_marker_stands_at_its_ports_side_though_its_wire_is_drawn_in_another_set
    model, (_hub, _near, far) = _build(_PUMPS)
    assert _inward(model, far) > 0


def test_two_pumps_markers_for_one_pe_net_stand_at_the_same_side() -> None:
    """Pump 1's -X3:1 and pump 2's -X3:2 differ only in where the hub's wire is drawn: their
    markers stand at the same side of their terminals, and at the same distance."""
    # UNDO: as in the first test (`_free_side` counts a wire drawn on any page or set):
    #     FAILED test_two_pumps_markers_for_one_pe_net_stand_at_the_same_side (with
    #     test_a_marker_stands_at_its_ports_side_though_its_wire_is_drawn_in_another_set)
    model, (_hub, near, far) = _build(_PUMPS)
    assert _inward(model, near) == _inward(model, far)


def test_a_terminal_whose_inner_wire_is_drawn_on_the_page_leaves_by_the_outer_port() -> None:
    """C22 kept: -X3:1 and -X3:2 stand beside each other with a wire drawn between them on the
    page, and the star's one marker for that pair stands at whichever sorts first. That inner
    port carries a wire drawn here, so the marker leaves by the free outer port."""
    # UNDO: stages/star_markers.py:_free_side, `if len(free) == 1:` -> `if False:` (the marker keeps
    #     its port's side): FAILED this test alone, id
    #     test_a_terminal_whose_inner_wire_is_drawn_on_the_page_leaves_by_the_outer_port
    # UNDO: engines/schematic/engine.py:_linked, the `wired` argument of `star_markers` set
    #     to an empty frozenset (nothing counts as wired): FAILED the same test, alone
    model, (_hub, near, far) = _build(_PAIR, pair=True)
    found = _own_branches(model, near) + _own_branches(model, far)
    assert len(found) == 1
    port = near if _own_branches(model, near) else far
    assert _inward(model, port) < 0
