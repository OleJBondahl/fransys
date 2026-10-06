"""DD-REPLICA-HOME (layout-0076): a child unit's boundary terminal, wired to a device in another
group, builds ("the records put name one id twice, with different content" before the fix).

Unit `inner` (a child of unit `outer`) holds, all at location FIELD, a strip terminal `T` in group
GA, a relay `Ka` in GA wired to `T`'s outer port (so the chain splits at the group change and `T`
keeps a column of its own), and a relay `K1` in group GB wired to `T`'s inner port on a page of its
own (`break_before`). `T` is a boundary of `inner`. `T` is drawn three times: at home, as a replica
beside `K1` (group GB) in the same drawing set, and as the black box in `outer`'s set.
`replicate_boundaries` took the black box's group from the last column of `T` (the replica beside
`K1`), not from its home, so it inherited GB and two placements in two drawing sets took one key.

Built through the `fransys` facade from `examples/demo-parts`; read from `layout.*` records.
"""

from typing import TYPE_CHECKING, Any

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import system_document

from fransys_model.kernel import Severity
from fransys_model.layout import DrawingSet, Label, Page, SymbolPlacement, layout_of
from fransys_model.vocab.tables import aspect_nodes, functions, units

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model

_PROJECT: dict[str, Any] = {
    "title": "Nested boundary terminal",
    "number": "P-1009",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def _build():
    """The design of the module docstring; returns the build result."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-25", text="First issue", created="XX")
    outer = d.scope("outer").unit("outer", revision=1, interface="1")
    outer.revision(1, date="2026-01-01", text="First release", created="XX")
    inner = outer.scope("in", at=outer.location("BOX", "Box")).unit(
        "inner", revision=1, interface="1"
    )
    inner.revision(1, date="2026-01-01", text="First release", created="XX")
    field = inner.location("FIELD", "Field side")
    group_a, group_b = inner.group("GA", "Group A"), inner.group("GB", "Group B")
    terminal = inner.strip("X1", at=field).terminal("DEMO-TB-2.5", group=group_a)
    ka = inner.item("DEMO-RLY-2CO-24", name="Ka", at=field, group=group_a)
    k1 = inner.item("DEMO-RLY-2CO-24", name="K1", at=field, group=group_b)
    wire = inner.wiring(colour="BU", gauge="0.5")
    wire(ka.fn("coil")["A1"], terminal.function["external"])
    wire(k1.fn("coil")["A1"], terminal.inner)
    inner.break_before(group_b)
    inner.boundary(terminal)
    return fr.build(parts, d.draft(), system_document())


def _terminal(model: Model) -> Id:
    """The id of the one terminal function of `X1`."""
    (found,) = (
        f.id
        for f in functions(model).values()
        if "X1" in f.key[:3] and f.key[-2:] == ("fn", "terminal")
    )
    return found


def _placements(model: Model) -> list[tuple[tuple[str, ...] | None, SymbolPlacement]]:
    """The terminal's placements as `(key of the unit of its drawing set, placement)`, the unit
    `None` for the top-level set."""
    terminal = _terminal(model)
    sets, pages = layout_of(model, DrawingSet), layout_of(model, Page)
    unit_key = {uid: unit.key for uid, unit in units(model).items()}
    return [
        (unit_key.get(sets[pages[p.page].drawing_set].unit), p)
        for p in layout_of(model, SymbolPlacement).values()
        if p.function == terminal
    ]


def test_a_nested_boundary_terminal_with_a_replica_builds_with_keys_of_their_own() -> None:
    """No exception and no ERROR finding; the terminal stands three times, each placement and
    each tag label under an id and a key of its own."""
    # UNDO: stages/replicate.py, `replicate_boundaries`: `for column in homes for
    #     cell` -> `for column in columns for cell` (the black box takes the replica's group)
    #     and write/placements.py, `placements`: drop the `"drawing_set", ...` part of a
    #     replica's extra (the two placements then take one key: a LayoutError from the guard
    #     in write/)
    result = _build()
    assert [f.code for f in result.findings if f.severity is Severity.ERROR] == []
    model = result.model
    placed = [p for _, p in _placements(model)]
    assert len(placed) == 3
    assert len({p.id for p in placed}) == len({p.key for p in placed}) == 3
    tags = [
        label
        for label in layout_of(model, Label).values()
        if label.function == _terminal(model) and label.slot == "tag"
    ]
    assert len(tags) == 3
    assert len({label.id for label in tags}) == len({label.key for label in tags}) == 3


def test_the_black_box_in_the_parent_stands_in_the_terminals_home_group() -> None:
    """The black box in `outer`'s set takes GA, the terminal's own group, and not GB, the group of
    the relay beside which the terminal is drawn again in `inner`'s set."""
    # UNDO: stages/replicate.py, `replicate_boundaries`: `for column in homes for
    #     cell` -> `for column in columns for cell` (the black box takes the replica's group)
    model = _build().model
    pages, nodes = layout_of(model, Page), aspect_nodes(model)
    groups = {
        unit: {nodes[g.group].key[-1] for g in pages[p.page].groups}
        for unit, p in _placements(model)
        if unit is not None and unit[-2:] == ("outer", "unit")
    }
    assert groups == {("outer", "unit"): {"GA"}}
