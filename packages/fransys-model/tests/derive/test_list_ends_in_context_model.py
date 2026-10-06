"""List ends print "shortest in context" (item 5): `port_designation_in` and its three callers.

An end in the document's own location prints short (`-B12:2/T1`); one outside it prints its
location path in front (`+EXT-M1:U1`), by the drawings' own `location_prefix`. Invented data.
"""

import pytest
from connector_builders import make_connector
from plant import Plant
from query_builders import make_labelled, make_node, make_placement, make_terminal

from fransys_model.derive import (
    WireRow,
    connector_rows,
    item_location,
    list_context,
    port_designation,
    terminal_rows,
    wire_rows,
)
from fransys_model.derive import drawing_text as drawing_text_module
from fransys_model.derive.drawing_text import port_designation_in
from fransys_model.kernel import Id, Model, SchemaError, make_id
from fransys_model.vocab.aspects import AspectNode
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.core import Item, Port


class _Cabinet:
    """Strip `X3` at `C1` (with a sub-location `SUB`), device `B12` in `C1`, motor `M1` at `EXT`.

    Terminal `T` (of `X3`, so it inherits `C1`) has an internal wire to `B12`'s port `2/T1` and
    an external wire to `M1`'s port `U1`. `S1` sits at `C1/SUB`, `H1` at `C1`, both with a
    connector, so a nested-location mate can be tried.
    """

    def __init__(self) -> None:
        self.plant = Plant()
        self.c1 = make_node("c1", None)
        self.sub = make_node("sub", self.c1.id)
        self.ext = make_node("ext", None)
        self.plant.add(self.c1, self.sub, self.ext)
        self.strip = self.plant.item("x3", designation="X3")
        self.b12 = self.plant.item("b12", designation="B12")
        self.m1 = self.plant.item("m1", designation="M1")
        self.plant.add(
            make_placement("x3-loc", self.strip, self.c1.id),
            make_placement("b12-loc", self.b12, self.c1.id),
            make_placement("m1-loc", self.m1, self.ext.id),
        )
        self.terminal = make_terminal(self.plant, "x3", "t", group="L", index=1)
        self.b12_port = self.plant.port(self.plant.function(self.b12, "f"), "2/T1")
        self.m1_port = self.plant.port(self.plant.function(self.m1, "f"), "U1")
        make_labelled(self.plant, "w-in", self.terminal.internal, self.b12_port, "W1")
        make_labelled(self.plant, "w-out", self.terminal.external, self.m1_port, "W2")

    def model(self) -> Model:
        return self.plant.model()


def _node(key: str) -> Id[AspectNode]:
    return make_id(AspectNode, (key,))


def test_a_terminal_row_prints_its_inside_end_short_and_its_outside_end_with_the_location() -> None:
    """Both ends on the SAME row: `B12` is in `C1` (short), `M1` is at `EXT` (path in front)."""
    cabinet = _Cabinet()
    model = cabinet.model()
    (row,) = terminal_rows(model, cabinet.strip, context=cabinet.c1.id)
    assert row.internal_ends == ("-B12:2/T1",)
    assert row.external_ends == ("+EXT-M1:U1",)


def test_a_terminal_row_without_context_prints_the_full_path_of_each_located_end() -> None:
    """`context=None` (the default) is the empty context path: `+C1-B12:2/T1`, `+EXT-M1:U1`."""
    cabinet = _Cabinet()
    model = cabinet.model()
    (row,) = terminal_rows(model, cabinet.strip)
    assert (row.internal_ends, row.external_ends) == (("+C1-B12:2/T1",), ("+EXT-M1:U1",))
    assert terminal_rows(model, cabinet.strip, context=None) == (row,)


def test_a_terminal_row_without_context_leaves_an_unlocated_end_bare() -> None:
    """A far end with no location has no prefix, even with no context."""
    cabinet = _Cabinet()
    loose = cabinet.plant.item("loose", designation="Q9")
    port = cabinet.plant.port(cabinet.plant.function(loose, "f"), "1")
    other = make_terminal(cabinet.plant, "x3", "u", group="L", index=2)
    make_labelled(cabinet.plant, "w-loose", other.external, port, "W3")
    model = cabinet.model()
    first, second = terminal_rows(model, cabinet.strip)
    assert second.external_ends == ("-Q9:1",)
    assert first.external_ends == ("+EXT-M1:U1",)


def test_a_far_end_on_another_terminal_inherits_its_strips_location() -> None:
    """A jumper's far end is a terminal of `X3` (at `C1`): short in `C1`, `+C1` seen from `EXT`."""
    cabinet = _Cabinet()
    other = make_terminal(cabinet.plant, "x3", "u", group="L", index=2)
    cabinet.plant.wire(cabinet.terminal.internal, other.internal, key="bridge")
    model = cabinet.model()
    first, _ = terminal_rows(model, cabinet.strip, context=cabinet.c1.id)
    assert "-X3:L:2" in first.internal_ends
    first, _ = terminal_rows(model, cabinet.strip, context=cabinet.ext.id)
    assert "+C1-X3:L:2" in first.internal_ends


@pytest.mark.parametrize(
    ("end_key", "context_key", "expected"),
    [
        ("sub", "c1", "+SUB-S1:1"),  # below the context: the path below the common ancestor
        ("sub", "sub", "-S1:1"),  # the context itself: short
        ("c1", "sub", "-H1:1"),  # above the context: nothing below the common ancestor
        ("c1", "ext", "+C1-H1:1"),  # a sibling tree: the whole path
        ("sub", "ext", "+C1+SUB-S1:1"),  # a sibling tree, nested: root first
    ],
)
def test_nested_locations_print_the_path_below_the_common_ancestor(
    end_key: str, context_key: str, expected: str
) -> None:
    """The three pinned cases of the brief, plus the two across the sibling trees."""
    cabinet = _Cabinet()
    s1 = cabinet.plant.item("s1", designation="S1")
    h1 = cabinet.plant.item("h1", designation="H1")
    cabinet.plant.add(
        make_placement("s1-loc", s1, cabinet.sub.id), make_placement("h1-loc", h1, cabinet.c1.id)
    )
    ports = {
        "sub": cabinet.plant.port(cabinet.plant.function(s1, "f"), "1"),
        "c1": cabinet.plant.port(cabinet.plant.function(h1, "f"), "1"),
    }
    model = cabinet.model()
    assert port_designation_in(model, ports[end_key], _node(context_key)) == expected


def test_an_end_without_a_location_prints_short_in_any_context() -> None:
    """An unplaced item has no path: nothing below any ancestor."""
    cabinet = _Cabinet()
    loose = cabinet.plant.item("loose", designation="Q9")
    port = cabinet.plant.port(cabinet.plant.function(loose, "f"), "1")
    model = cabinet.model()
    assert port_designation_in(model, port, cabinet.c1.id) == "-Q9:1"


def test_an_unknown_port_is_a_schema_error_not_a_key_error() -> None:
    """`port_designation` reads the port first, so its `SchemaError` comes before any lookup."""
    cabinet = _Cabinet()
    with pytest.raises(SchemaError):
        port_designation_in(cabinet.model(), make_id(Port, ("nowhere",)), cabinet.c1.id)


def test_port_designation_in_is_built_on_the_drawings_location_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The prefix comes from `drawing_text.location_prefix`, not a second rule."""
    cabinet = _Cabinet()
    model = cabinet.model()
    assert port_designation_in(model, cabinet.b12_port, cabinet.c1.id) == "-B12:2/T1"
    monkeypatch.setattr(drawing_text_module, "location_prefix", lambda *_: ("X",))
    assert port_designation_in(model, cabinet.b12_port, cabinet.c1.id) == "+X-B12:2/T1"


def test_port_designation_in_with_no_context_prints_the_whole_location_path() -> None:
    """`None` is the empty context path: the whole path in front, none for an unplaced item."""
    cabinet = _Cabinet()
    sub_item = cabinet.plant.item("s1", designation="S1")
    cabinet.plant.add(make_placement("s1-loc", sub_item, cabinet.sub.id))
    sub_port = cabinet.plant.port(cabinet.plant.function(sub_item, "f"), "1")
    loose = cabinet.plant.item("loose", designation="Q9")
    loose_port = cabinet.plant.port(cabinet.plant.function(loose, "f"), "1")
    model = cabinet.model()
    assert port_designation_in(model, cabinet.m1_port, None) == "+EXT-M1:U1"
    assert port_designation_in(model, sub_port, None) == "+C1+SUB-S1:1"
    assert port_designation_in(model, loose_port, None) == port_designation(model, loose_port)


def _ends(rows: tuple[WireRow, ...]) -> list[frozenset[str]]:
    """Each row's two ends as an unordered pair, in row order."""
    return [frozenset({row.from_, row.to}) for row in rows]


def test_wire_rows_print_each_end_in_context() -> None:
    """`w-in` runs terminal to `B12` (both in `C1`), `w-out` terminal to `M1` (at `EXT`)."""
    cabinet = _Cabinet()
    model = cabinet.model()
    assert set(_ends(wire_rows(model, context=cabinet.c1.id))) == {
        frozenset({"-B12:2/T1", "-X3:L:1"}),
        frozenset({"+EXT-M1:U1", "-X3:L:1"}),
    }
    assert set(_ends(wire_rows(model))) == {
        frozenset({"+EXT-M1:U1", "+C1-X3:L:1"}),
        frozenset({"+C1-B12:2/T1", "+C1-X3:L:1"}),
    }


def test_wire_rows_without_context_leave_an_unlocated_end_bare() -> None:
    """`context=None` prefixes a located end with its whole path, an unlocated one with none."""
    plant = Plant()
    here = make_node("here", None)
    plant.add(here)
    placed = plant.item("placed", designation="A1")
    loose = plant.item("loose", designation="Q9")
    plant.add(make_placement("placed-loc", placed, here.id))
    ports = {
        name: plant.port(plant.function(item, "f"), "1")
        for name, item in (("placed", placed), ("loose", loose))
    }
    make_labelled(plant, "w", ports["placed"], ports["loose"], "L")
    (row,) = wire_rows(plant.model())
    assert {row.from_, row.to} == {"+HERE-A1:1", "-Q9:1"}


def test_wire_rows_seen_from_the_far_location_prefix_the_cabinet_ends() -> None:
    """From `EXT` the terminal's own end is the outside one: `+C1-X3:L:1`."""
    cabinet = _Cabinet()
    rows = wire_rows(cabinet.model(), context=cabinet.ext.id)
    assert frozenset({"-M1:U1", "+C1-X3:L:1"}) in _ends(rows)


def test_wire_rows_sort_by_the_text_the_row_holds() -> None:
    """Same `to`, `from_` texts differing only by the location prefix: `+EXT-...` sorts first.

    Both `from_` items are `A1`, so the unprefixed `port_designation` ties and the conductor id
    (the inside wire's id is the lower one) would put the inside wire first; only the printed
    text puts the `+EXT-A1:1` row before the `-A1:1` row. A conductor stores its ends in id
    order, so the keys are picked by id: the shared `Z1` port has the highest id (it is
    `b` of both wires), and the inside wire has the lowest conductor id.
    """
    plant = Plant()
    here, ext = make_node("here", None), make_node("ext", None)
    plant.add(here, ext)
    low_a, high_a, far_key = sorted(("i1", "i2", "i3"), key=lambda k: make_id(Port, (k, "f", "1")))
    inside = plant.item(low_a, designation="A1")
    outside = plant.item(high_a, designation="A1")
    far = plant.item(far_key, designation="Z1")
    first_wire, second_wire = sorted(("w1", "w2"), key=lambda k: make_id(Conductor, (k,)))
    plant.add(
        make_placement("in-loc", inside, here.id),
        make_placement("out-loc", outside, ext.id),
        make_placement("far-loc", far, here.id),
    )
    ports = {
        name: plant.port(plant.function(item, "f"), "1")
        for name, item in (("in", inside), ("out", outside), ("far", far))
    }
    make_labelled(plant, first_wire, ports["in"], ports["far"], "L")
    make_labelled(plant, second_wire, ports["out"], ports["far"], "L")
    rows = wire_rows(plant.model(), context=here.id)
    assert [(row.from_, row.to) for row in rows] == [
        ("+EXT-A1:1", "-Z1:1"),
        ("-A1:1", "-Z1:1"),
    ]


def test_a_connector_mate_pin_prints_in_context() -> None:
    """Board `JB1` at `C1`; its mate `H1` at `EXT` prints `+EXT-H1:1`, short from `EXT`."""
    plant = Plant()
    c1, ext = make_node("c1", None), make_node("ext", None)
    plant.add(c1, ext)
    board = plant.item("jb1", designation="JB1")
    housing = plant.item("h1", designation="H1")
    plant.add(make_placement("jb1-loc", board, c1.id), make_placement("h1-loc", housing, ext.id))
    j1, _ = make_connector(plant, ("jb1", "J1"), ("1",))
    p1, _ = make_connector(plant, ("h1", "P1"), ("1",))
    plant.mate(j1, p1)
    model = plant.model()
    (row,) = connector_rows(model, board, context=c1.id)
    (pin,) = row.pins
    assert pin.mate_port_designation == "+EXT-H1:1"
    assert row.mate_designation == "-H1"  # an item, not an end: unchanged
    (pin,) = connector_rows(model, board, context=ext.id)[0].pins
    assert pin.mate_port_designation == "-H1:1"
    (pin,) = connector_rows(model, board)[0].pins
    assert pin.mate_port_designation == "+EXT-H1:1"  # no context: the whole path


def test_a_connector_mate_pin_without_context_leaves_an_unlocated_mate_bare() -> None:
    """A mate with no location has no prefix, even with no context."""
    plant = Plant()
    c1 = make_node("c1", None)
    plant.add(c1)
    board = plant.item("jb1", designation="JB1")
    plant.item("h1", designation="H1")
    plant.add(make_placement("jb1-loc", board, c1.id))
    j1, _ = make_connector(plant, ("jb1", "J1"), ("1",))
    p1, _ = make_connector(plant, ("h1", "P1"), ("1",))
    plant.mate(j1, p1)
    (pin,) = connector_rows(plant.model(), board)[0].pins
    assert pin.mate_port_designation == "-H1:1"


def test_item_location_is_the_effective_location_node() -> None:
    """Own placement, inherited from the strip for a terminal, `None` for an unplaced item."""
    cabinet = _Cabinet()
    loose = cabinet.plant.item("loose", designation="Q9")
    model = cabinet.model()
    assert item_location(model, cabinet.strip) == cabinet.c1.id
    assert item_location(model, cabinet.terminal.item) == cabinet.c1.id
    assert item_location(model, cabinet.m1) == cabinet.ext.id
    assert item_location(model, loose) is None


def test_list_context_prefers_the_document_location() -> None:
    """A given `location` wins over the subject's own."""
    cabinet = _Cabinet()
    model = cabinet.model()
    assert list_context(model, cabinet.strip, location=cabinet.ext.id) == cabinet.ext.id


def test_list_context_falls_back_to_the_subjects_own_location() -> None:
    """No document location: the subject's, own or inherited."""
    cabinet = _Cabinet()
    model = cabinet.model()
    assert list_context(model, cabinet.strip) == cabinet.c1.id
    assert list_context(model, cabinet.terminal.item) == cabinet.c1.id


def test_list_context_of_an_unlocated_subject_is_none() -> None:
    """Neither a location nor a placement: no context, which lists read as "full path"."""
    cabinet = _Cabinet()
    loose = cabinet.plant.item("loose", designation="Q9")
    assert list_context(cabinet.model(), loose) is None


def test_item_location_refuses_an_id_that_is_not_an_item() -> None:
    """Like `effective_placement`: an unknown item is a `SchemaError`."""
    cabinet = _Cabinet()
    with pytest.raises(SchemaError):
        item_location(cabinet.model(), make_id(Item, ("nope",)))
