"""Scale fixture of the per-unit index work: one container unit holding N cabinet units.

Every cabinet is the units worked example's `pump_cabinet` (`test_units_worked_example.py`),
itself nesting the `io_board` board unit, so a build has `1 + 2N` units. Demo parts only. Each
instance gets its own scope prefix (`pump1`..`pumpN`) and location (`C1`..`CN`) so no reference
designation repeats; each cabinet's two field terminals are declared unused, which clears
`BOUNDARY_UNCONNECTED` without a per-instance top-level cable. Used by
`test_scale_units_fixture.py` and by the profile script in `claude-tools/`.
"""

from typing import Any

import fransys as fr
import fransys_author
import fransys_parts

PROJECT: dict[str, Any] = {
    "title": "Scale",
    "number": "P-1004",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}

UNITS_PER_INSTANCE = 2  # the cabinet unit and the board unit it nests


def _io_board(s):
    """A board unit with one boundary connector, `X1` (the worked example's `io_board`)."""
    u = s.unit("demo-io-board", revision=3, interface="2")
    u.revision(3, date="2026-01-01", text="First release", created="XX")
    grp = u.group("BRD", "I/O board")
    board = u.item("DEMO-PCB-IO", name="board", group=grp)
    x1 = u.item("DEMO-CONN-2P", tag="X1", parent=board, group=grp)
    k1 = u.item("DEMO-RLY-2CO-24", name="k1", parent=board, group=grp)
    wire = u.wiring(colour="BU", gauge="0.5")
    wire(x1["1"], k1.fn("coil")["A1"])
    wire(x1["2"], k1.fn("coil")["A2"])
    u.net("internal", k1.fn("co_1")["11"], k1.fn("co_2")["21"])
    u.boundary(x1)
    return x1


def pump_cabinet(s, *, name):
    """A cabinet unit with two field-terminal boundaries; returns the field terminals."""
    u = s.unit("demo-pump-cabinet", revision=2, interface="1")
    u.revision(2, date="2026-01-01", text="First release", created="XX")
    c = u.location(name, "Pump cabinet")
    grp = u.group("FLD", "Field wiring")
    x2 = u.strip("X2", at=c)
    field = [x2.terminal("DEMO-TB-2.5", group=grp) for _ in range(2)]
    board_x1 = _io_board(u.scope("io", at=c))
    w1 = u.harness(name="w1", tag="WH1", at=c, group=grp)
    p1 = u.item("DEMO-CONN-2P", tag="P1", parent=w1, at=c, group=grp)
    cable = u.cable("DEMO-CBL-4G1.5", name="w1c", parent=w1, at=c)
    cable.core(1, field[0].outer, p1["1"])
    cable.core(2, field[1].outer, p1["2"])
    u.mate(p1, board_x1)
    for terminal in field:
        u.boundary(terminal)
    return field


def scale_design(parts, n):
    """The `Design`: one container unit (`scale-container`) holding `n` cabinet instances."""
    d = fransys_author.Design(parts)
    d.project(**PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    er = d.location("ER", "Engine room")
    container = d.unit("scale-container", revision=1, interface="1")
    container.revision(1, date="2026-01-01", text="First release", created="XX")
    for i in range(1, n + 1):
        field = pump_cabinet(container.scope(f"pump{i}", at=er), name=f"C{i}")
        for terminal in field:
            container.unused(terminal)
    return d


def build_scale(n, *, with_document: bool = False) -> fr.BuildResult:
    """`fr.build` of the `n`-instance design, the facade call the worked example uses.

    `with_document=False` (the default): no document, the shape MODEL-BUILD acceptance 6 (the
    examples' largest build with its documents left out) measures -- decision 0037 (PS1) then
    runs no layout at all, so this default must never change. `with_document=True` adds a
    `system_document()` draft (`_model_build_cover.py`): for a caller that specifically needs
    this design laid out (`tests/test_scale_call_counts.py`'s own layout-code-object count,
    which reads real `stages/place.py` calls that only happen once layout runs).
    """
    parts = fransys_parts.load("demo_parts")
    drafts = (scale_design(parts, n).draft(),)
    if with_document:
        from _model_build_cover import system_document

        drafts = (*drafts, system_document())
    return fr.build(parts, *drafts)
