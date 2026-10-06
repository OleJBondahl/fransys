"""D9 per drawing set (layout-0070): a star may drop no conductor and must still draw its markers.

A unit's earth hub is wired beside two terminals in the unit's own set (one column of one
group). The same four terminals stand in the top-level set as boundary pins in a row of
their group: left, hub, an unwired pin, right. There the hub is beside `left` only, so the net
is a star (two clusters in that set) though every wire is beside somewhere and none is dropped
from routing. `star_markers` took `min(star.conductors)` of the empty set and raised. Built
through the `fransys` facade from `examples/demo-parts`.
"""

from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import system_document

from fransys_model.kernel import Severity

_PROJECT: dict[str, Any] = {
    "title": "Star no dropped wire",
    "number": "P-1009",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def test_a_star_that_drops_no_conductor_builds_without_error() -> None:
    """The hub is beside both terminals in the unit's set, and apart from one in the parent set."""
    # UNDO: stages/references/markers.py, `star_markers`:
    #     `min(star.conductors or star.wires)` to `min(star.conductors)`:
    #     `fr.build` raises ValueError (min() of an empty set)
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    cab = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    cab.revision(1, date="2026-01-01", text="First release", created="XX")
    c1 = cab.location("C1", "Cabinet")
    g1 = cab.group("G1", "Group 1")
    x1, x2, x3 = (cab.strip(name, at=c1) for name in ("X1", "X2", "X3"))
    left, hub = (x1.terminal("DEMO-TB-2.5", group=g1) for _ in range(2))
    filler = x2.terminal("DEMO-TB-2.5", group=g1)  # in the top row between the hub and `right`
    right = x3.terminal("DEMO-TB-2.5", group=g1)
    earth = cab.wiring(colour="GNYE", gauge="2.5")
    earth(hub.inner, left.inner)
    earth(hub.inner, right.inner)
    for terminal in (left, hub, filler, right):
        cab.boundary(terminal)
    result = fr.build(parts, d.draft(), system_document())
    assert not [f for f in result.findings if f.severity is Severity.ERROR]
