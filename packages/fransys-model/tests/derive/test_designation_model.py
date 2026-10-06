"""WP14 tests: how designations render, and what refuses (design/derive-text.md and
design/examples.md 11)."""

import re
from decimal import Decimal
from typing import Any, cast

import pytest
from plant import Plant
from query_builders import make_footprint

from fransys_model.derive import (
    board_netlist,
    item_designation,
    port_designation,
    reference_designation,
)
from fransys_model.derive.designation import can_print_designation, designation_refusal
from fransys_model.derive.passes.numbering import number
from fransys_model.kernel import Id, Model, SchemaError, make_id
from fransys_model.vocab.aspects import AspectNode, Placement
from fransys_model.vocab.core import Item, Port, Unit
from fransys_model.vocab.enums import Aspect, PartCategory
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet
from fransys_model.vocab.facets.pcb import PcbFacet
from fransys_model.vocab.facets.terminal import TerminalFacet
from fransys_model.vocab.tables import functions, items, ports
from fransys_model.vocab.templates import Part


def _terminal(  # noqa: PLR0913 -- one param per field the tests vary, kept explicit
    plant: Plant,
    key: str,
    group: str,
    index: int,
    *,
    parent: str | None = None,
    unit: Id[Unit] | None = None,
) -> None:
    """An item keyed `key` carrying a `terminal` facet, optionally under the strip `parent`."""
    item = plant.item(key, parent=None if parent is None else make_id(Item, (parent,)), unit=unit)
    plant.add(
        TerminalFacet(
            id=make_id(TerminalFacet, (key, "terminal")),
            key=(key, "terminal"),
            subject=item,
            group=group,
            index=index,
        )
    )


def _node(
    plant: Plant, key: str, aspect: Aspect, *, label: str, parent: str | None = None
) -> Id[AspectNode]:
    node = AspectNode(
        id=make_id(AspectNode, (key,)),
        key=(key,),
        aspect=aspect,
        parent=None if parent is None else make_id(AspectNode, (parent,)),
        label=label,
        description="Invented",
    )
    plant.add(node)
    return node.id


def _place(plant: Plant, item: str, node: Id[AspectNode], key: str) -> Id[Placement]:
    placement = Placement(
        id=make_id(Placement, (key,)), key=(key,), item=make_id(Item, (item,)), node=node
    )
    plant.add(placement)
    return placement.id


def _item_id(key: str) -> Id[Item]:
    return make_id(Item, (key,))


# ---- item_designation ---------------------------------------------------------------------


def test_an_ordinary_item_renders_its_own_designation() -> None:
    """The `designation` field, as authored."""
    plant = Plant()
    plant.item("k1", designation="K1")
    assert item_designation(plant.model(), _item_id("k1")) == "K1"


def test_a_terminal_renders_group_and_index_whatever_its_designation_field_says() -> None:
    """`L1:1`: derived from the facet, so the field is not read."""
    plant = Plant()
    _terminal(plant, "t1", "L1", 1)
    plant.item("t2", designation="AUTHORED")
    _terminal(plant, "t3", "L1", 3)
    assert item_designation(plant.model(), _item_id("t1")) == "L1:1"
    assert item_designation(plant.model(), _item_id("t3")) == "L1:3"


def test_a_terminal_with_an_empty_group_renders_its_index_alone() -> None:
    """`index` alone, no leading colon."""
    plant = Plant()
    _terminal(plant, "t1", "", 7)
    assert item_designation(plant.model(), _item_id("t1")) == "7"


def test_an_unnumbered_item_is_a_schema_error_naming_it() -> None:
    """No placeholder: the caller must run numbering first."""
    plant = Plant()
    plant.item("k1")
    with pytest.raises(SchemaError, match="no designation") as excinfo:
        item_designation(plant.model(), _item_id("k1"))
    assert (excinfo.value.kind, excinfo.value.record_id) == ("item", _item_id("k1"))


def test_an_id_that_is_not_an_item_is_a_schema_error_naming_it() -> None:
    """Absent, or an id of another kind: not an item of the model."""
    plant = Plant()
    port = plant.pin("a", "f", "1")
    model = plant.model()
    for target in (_item_id("nowhere"), port):
        with pytest.raises(SchemaError, match="is not an item") as excinfo:
            item_designation(model, cast("Any", target))
        assert excinfo.value.record_id == target


# ---- port_designation ---------------------------------------------------------------------


def test_a_port_renders_its_items_designation_and_its_own_name() -> None:
    """`-K1:13`, always dashed (decision model-0052)."""
    plant = Plant()
    item = plant.item("k1", designation="K1")
    port = plant.port(plant.function(item, "no_1"), "13")
    assert port_designation(plant.model(), port) == "-K1:13"


def test_a_terminal_port_renders_strip_and_terminal_without_a_port_name() -> None:
    """`-X03:L1:1`: both ports of a terminal are one point; the role says which side."""
    plant = Plant()
    plant.item("x03", designation="X03")
    _terminal(plant, "t1", "L1", 1, parent="x03")
    function = plant.function(_item_id("t1"), "terminal")
    internal = plant.port(function, "internal")
    external = plant.port(function, "external")
    model = plant.model()
    assert port_designation(model, internal) == "-X03:L1:1"
    assert port_designation(model, external) == "-X03:L1:1"


def test_a_terminal_port_without_a_strip_renders_the_terminal_alone() -> None:
    """Never an error for a parentless terminal."""
    plant = Plant()
    _terminal(plant, "t1", "L1", 1)
    port = plant.port(plant.function(_item_id("t1"), "terminal"), "internal")
    assert port_designation(plant.model(), port) == "-L1:1"


def test_a_port_that_is_not_in_the_model_is_a_schema_error_naming_it() -> None:
    """Kind `port`, the id it was given."""
    plant = Plant()
    plant.item("k1", designation="K1")
    absent = make_id(Port, ("nowhere",))
    with pytest.raises(SchemaError, match="is not a port") as excinfo:
        port_designation(plant.model(), absent)
    assert (excinfo.value.kind, excinfo.value.record_id) == ("port", absent)


def test_a_port_of_an_unnumbered_item_is_the_same_error_as_for_the_item() -> None:
    """The refusal comes from the item it belongs to."""
    plant = Plant()
    port = plant.pin("k1", "f", "1")
    with pytest.raises(SchemaError, match="no designation"):
        port_designation(plant.model(), port)


# ---- reference_designation ----------------------------------------------------------------


def _placed(*, function: str | None = None, location: str | None = None) -> Plant:
    plant = Plant()
    plant.item("k1", designation="K1")
    if function is not None:
        _place(plant, "k1", _node(plant, "fn", Aspect.FUNCTION, label=function), "p-fn")
    if location is not None:
        _place(plant, "k1", _node(plant, "loc", Aspect.LOCATION, label=location), "p-loc")
    return plant


def test_function_then_location_then_product() -> None:
    """`=A1+C1-K1`: the order of the signs is fixed, not the order of the placements."""
    assert reference_designation(_placed(function="A1", location="C1").model(), _item_id("k1")) == (
        "=A1+C1-K1"
    )


def test_only_the_aspects_the_item_is_placed_in_appear() -> None:
    """A missing aspect leaves no empty sign."""
    assert reference_designation(_placed(function="A1").model(), _item_id("k1")) == "=A1-K1"
    assert reference_designation(_placed(location="C1").model(), _item_id("k1")) == "+C1-K1"


def test_an_item_with_no_placements_renders_only_its_product_segment() -> None:
    """`-K1`."""
    assert reference_designation(_placed().model(), _item_id("k1")) == "-K1"


def test_a_product_placement_never_contributes_a_segment() -> None:
    """No double dash: the trailing `-K1` is the item's own designation."""
    plant = _placed(function="A1")
    _place(plant, "k1", _node(plant, "prod", Aspect.PRODUCT, label="K9"), "p-prod")
    assert reference_designation(plant.model(), _item_id("k1")) == "=A1-K1"


def test_nested_nodes_repeat_the_sign_root_to_leaf() -> None:
    """`=A1=B2+C1+D2-K1`: the IEC 81346 form, never a dot."""
    plant = Plant()
    plant.item("k1", designation="K1")
    _node(plant, "a1", Aspect.FUNCTION, label="A1")
    _node(plant, "b2", Aspect.FUNCTION, label="B2", parent="a1")
    _node(plant, "c1", Aspect.LOCATION, label="C1")
    _node(plant, "d2", Aspect.LOCATION, label="D2", parent="c1")
    _place(plant, "k1", make_id(AspectNode, ("b2",)), "p1")
    _place(plant, "k1", make_id(AspectNode, ("d2",)), "p2")
    assert reference_designation(plant.model(), _item_id("k1")) == "=A1=B2+C1+D2-K1"


def test_an_item_placed_twice_in_one_aspect_renders_the_smallest_placement_id() -> None:
    """`PLACEMENT_DUPLICATE` is the validator's; rendering must still be deterministic."""
    plant = Plant()
    plant.item("k1", designation="K1")
    first = _place(plant, "k1", _node(plant, "n1", Aspect.LOCATION, label="C1"), "pa")
    second = _place(plant, "k1", _node(plant, "n2", Aspect.LOCATION, label="C2"), "pb")
    expected = "+C1-K1" if first < second else "+C2-K1"
    assert reference_designation(plant.model(), _item_id("k1")) == expected


def test_a_parent_cycle_among_nodes_ends_the_walk() -> None:
    """`ASPECT_CYCLE` is the validator's; here the render terminates, truncated, root to leaf."""
    plant = Plant()
    plant.item("k1", designation="K1")
    _node(plant, "a", Aspect.LOCATION, label="A", parent="b")
    _node(plant, "b", Aspect.LOCATION, label="B", parent="a")
    _place(plant, "k1", make_id(AspectNode, ("a",)), "p1")
    assert reference_designation(plant.model(), _item_id("k1")) == "+B+A-K1"


def test_a_terminal_reference_ends_with_its_strip_and_own_label() -> None:
    """`=A1+C1-X03:L1:1`, the printed designation (decision model-0064); it was `-L1:1`."""
    plant = Plant()
    plant.item("x03", designation="X03")
    _terminal(plant, "t1", "L1", 1, parent="x03")
    _place(plant, "t1", _node(plant, "fn", Aspect.FUNCTION, label="A1"), "p-fn")
    _place(plant, "t1", _node(plant, "loc", Aspect.LOCATION, label="C1"), "p-loc")
    assert reference_designation(plant.model(), _item_id("t1")) == "=A1+C1-X03:L1:1"


def test_a_terminal_reference_in_a_unit_ends_with_the_unit_relative_terminal_text() -> None:
    """The `unit=` form: `=A1-X03:L1:1`; `+C1` is left out as not the unit's own.

    Another unit's item sits at `+C1`, so `own_nodes` does not keep it; the whole-model form
    still prints it.
    """
    plant = Plant()
    cabinet = plant.unit("cab")
    plant.unit("other", name="other")
    plant.item("x03", designation="X03", unit=cabinet)
    _terminal(plant, "t1", "L1", 1, parent="x03", unit=cabinet)
    plant.item("k9", designation="K9", unit=make_id(Unit, ("other",)))
    fn = _node(plant, "fn", Aspect.FUNCTION, label="A1")
    loc = _node(plant, "loc", Aspect.LOCATION, label="C1")
    _place(plant, "t1", fn, "p-fn")
    _place(plant, "t1", loc, "p-loc")
    _place(plant, "k9", loc, "p-k9")
    model = plant.model()
    assert reference_designation(model, _item_id("t1")) == "=A1+C1-X03:L1:1"
    assert reference_designation(model, _item_id("t1"), unit=cabinet) == "=A1-X03:L1:1"


def test_the_unit_form_renders_own_placements_only_not_an_inherited_one() -> None:
    """R1: `k1` has no placement of its own, its parent `cab` is at `=A1`; both forms read `-K1`.

    The unit form used to read `effective_placement` and print `=A1-K1`.
    """
    plant = Plant()
    unit = plant.unit("u")
    cab = plant.item("cab", designation="C1", unit=unit)
    plant.item("k1", designation="K1", parent=cab, unit=unit)
    _place(plant, "cab", _node(plant, "fn", Aspect.FUNCTION, label="A1"), "p-fn")
    model = plant.model()
    assert reference_designation(model, _item_id("k1")) == "-K1"
    assert reference_designation(model, _item_id("k1"), unit=unit) == "-K1"
    assert reference_designation(model, _item_id("cab"), unit=unit) == "=A1-C1"


def test_a_terminal_with_no_placement_takes_its_strips_in_both_forms() -> None:
    """Decision model-0064: `+C1` comes through the strip, whole-model and `unit=` alike."""
    plant = Plant()
    cabinet = plant.unit("cab")
    plant.item("x03", designation="X03", unit=cabinet)
    _terminal(plant, "t1", "L1", 1, parent="x03", unit=cabinet)
    _place(plant, "x03", _node(plant, "loc", Aspect.LOCATION, label="C1"), "p-loc")
    model = plant.model()
    assert reference_designation(model, _item_id("t1")) == "+C1-X03:L1:1"
    assert reference_designation(model, _item_id("t1"), unit=cabinet) == "+C1-X03:L1:1"


def test_a_terminal_keeps_its_own_placement_in_an_aspect_and_takes_the_strips_in_the_other() -> (
    None
):
    """Own `=A1` wins over the strip's `=B9`; the strip's `+C1` fills the location aspect."""
    plant = Plant()
    plant.item("x03", designation="X03")
    _terminal(plant, "t1", "L1", 1, parent="x03")
    _place(plant, "x03", _node(plant, "strip-fn", Aspect.FUNCTION, label="B9"), "p-strip-fn")
    _place(plant, "x03", _node(plant, "loc", Aspect.LOCATION, label="C1"), "p-strip-loc")
    _place(plant, "t1", _node(plant, "fn", Aspect.FUNCTION, label="A1"), "p-fn")
    assert reference_designation(plant.model(), _item_id("t1")) == "=A1+C1-X03:L1:1"


def test_the_strip_exception_is_one_hop_and_terminals_only() -> None:
    """A terminal does not read past its strip; a non-terminal under a placed item reads nothing."""
    plant = Plant()
    rack = plant.item("rack", designation="R1")
    strip = plant.item("x03", designation="X03", parent=rack)
    _terminal(plant, "t1", "L1", 1, parent="x03")
    plant.item("k1", designation="K1", parent=strip)
    _place(plant, "rack", _node(plant, "loc", Aspect.LOCATION, label="C1"), "p-rack")
    model = plant.model()
    assert reference_designation(model, _item_id("t1")) == "-X03:L1:1"
    assert reference_designation(model, _item_id("k1")) == "-K1"


def test_an_unnumbered_or_absent_item_is_the_same_schema_error() -> None:
    """Raised through `item_designation`."""
    plant = Plant()
    plant.item("k1")
    model = plant.model()
    with pytest.raises(SchemaError, match="no designation"):
        reference_designation(model, _item_id("k1"))
    with pytest.raises(SchemaError, match="is not an item"):
        reference_designation(model, _item_id("nowhere"))


def test_a_label_with_a_dot_or_a_sign_is_rendered_as_it_is() -> None:
    """Labels are opaque: nothing is split or escaped."""
    plant = _placed(function="A1.B", location="+C1")
    assert reference_designation(plant.model(), _item_id("k1")) == "=A1.B++C1-K1"


def test_a_terminal_port_under_an_unnumbered_strip_raises_through_the_strip() -> None:
    """A missing parent is fine; a parent with no designation is the parent's refusal."""
    plant = Plant()
    plant.item("x03")
    _terminal(plant, "t1", "L1", 1, parent="x03")
    port = plant.port(plant.function(_item_id("t1"), "terminal"), "internal")
    with pytest.raises(SchemaError, match="no designation") as excinfo:
        port_designation(plant.model(), port)
    assert excinfo.value.record_id == _item_id("x03")


# ---- board designations (model-0040, spec B3) ----------------------------------------------


def _board_part(plant: Plant, key: str) -> Id[Part]:
    """A part that carries the `pcb` facet, keyed distinctly so a test can add several."""
    part = Part(
        id=make_id(Part, (key,)),
        key=(key,),
        mpn=f"MPN-{key}",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.BOARD,
        class_code="A",
    )
    facet = PcbFacet(
        id=make_id(PcbFacet, (key, "pcb")), key=(key, "pcb"), subject=part.id, revision="A"
    )
    plant.add(part, facet)
    return part.id


def test_the_board_connectors_designation_is_a1_x1() -> None:
    """The owner's own preview text (model-0040, spec B3)."""
    plant = Plant()
    board = plant.item("board", part=_board_part(plant, "board"), designation="A1")
    x1 = plant.item("x1", parent=board, designation="X1")
    assert reference_designation(plant.model(), x1) == "-A1-X1"


def test_two_boards_each_with_an_unplaced_k1_read_a1_k1_and_a2_k1() -> None:
    """B3's own can-fail case, closed: two boards' unplaced components no longer both read
    `-K1` (units spec worked example)."""
    plant = Plant()
    board1 = plant.item("board1", part=_board_part(plant, "board1"), designation="A1")
    board2 = plant.item("board2", part=_board_part(plant, "board2"), designation="A2")
    k1_on_1 = plant.item("k1-on-1", parent=board1, designation="K1")
    k1_on_2 = plant.item("k1-on-2", parent=board2, designation="K1")
    model = plant.model()
    assert reference_designation(model, k1_on_1) == "-A1-K1"
    assert reference_designation(model, k1_on_2) == "-A2-K1"
    assert item_designation(model, k1_on_1) == "A1-K1"
    assert item_designation(model, k1_on_2) == "A2-K1"


def test_a_board_inside_a_board_prefixes_outermost_first() -> None:
    """The chain is every enclosing `pcb`-faceted item, outermost first (spec B3)."""
    plant = Plant()
    outer = plant.item("outer", part=_board_part(plant, "outer"), designation="A2")
    inner = plant.item("inner", part=_board_part(plant, "inner"), parent=outer, designation="B1")
    leaf = plant.item("leaf", parent=inner, designation="K1")
    assert item_designation(plant.model(), leaf) == "A2-B1-K1"


def test_a_terminal_on_a_strip_reads_as_today_unaffected_by_board_chains() -> None:
    """A parent chain with no `pcb` facet (a terminal on a strip) is rendered as before,
    unchanged by model-0040 -- the existing designation tests prove the rest."""
    plant = Plant()
    plant.item("x03", designation="X03")
    _terminal(plant, "t1", "L1", 1, parent="x03")
    assert item_designation(plant.model(), _item_id("t1")) == "L1:1"


def test_a_strip_and_its_terminal_under_a_board_give_the_chain_once() -> None:
    """`-A1-X03:L1:1`, not `-A1-X03:A1-L1:1` (model-0040, spec B3's refinement): the chain is
    the strip's `item_designation` alone, the terminal contributes only its own label."""
    plant = Plant()
    board = plant.item("board", part=_board_part(plant, "board"), designation="A1")
    plant.item("x03", parent=board, designation="X03")
    _terminal(plant, "t1", "L1", 1, parent="x03")
    function = plant.function(_item_id("t1"), "terminal")
    internal = plant.port(function, "internal")
    model = plant.model()
    assert port_designation(model, internal) == "-A1-X03:L1:1"


def test_the_spec_literal_shape_a1_x1_colon_3() -> None:
    """The spec's own literal text (acceptance 3): a strip `X1` and an empty-group,
    index-3 terminal under board `A1` read `-A1-X1:3`. `port_designation` always renders the
    leading dash (decision model-0052, owner ruling 2026-09-24: "the dash is always there"),
    matching `reference_designation`'s own `-A1-X1` form for the strip."""
    plant = Plant()
    board = plant.item("board", part=_board_part(plant, "board"), designation="A1")
    plant.item("x1", parent=board, designation="X1")
    _terminal(plant, "t1", "", 3, parent="x1")
    function = plant.function(_item_id("t1"), "terminal")
    internal = plant.port(function, "internal")
    model = plant.model()
    assert port_designation(model, internal) == "-A1-X1:3"


def test_a_strip_and_its_terminal_under_a_board_can_fail_with_the_chain_twice() -> None:
    """Can-fail: adding the board chain a second time -- calling `item_designation` on the
    terminal instead of `_own_designation`, a scratch stand-in for the deleted line, not a
    monkeypatch of model code -- gives `A1-X03:A1-L1:1`, not the fixed `-A1-X03:L1:1`."""
    plant = Plant()
    board = plant.item("board", part=_board_part(plant, "board"), designation="A1")
    plant.item("x03", parent=board, designation="X03")
    _terminal(plant, "t1", "L1", 1, parent="x03")
    function = plant.function(_item_id("t1"), "terminal")
    internal = plant.port(function, "internal")
    model = plant.model()

    def with_the_chain_twice(model: Any, port: Id[Port]) -> str:
        record = ports(model)[port]
        owner = items(model)[functions(model)[record.function].item]
        assert owner.parent is not None
        return f"{item_designation(model, owner.parent)}:{item_designation(model, owner.id)}"

    assert with_the_chain_twice(model, internal) == "A1-X03:A1-L1:1"
    assert port_designation(model, internal) == "-A1-X03:L1:1"


# ---- harness designations (H1, H2, H3; decision model-0043, spec 2026-09-23-harness-designation)


def _cable_facet(plant: Plant, key: str, item: Id[Item]) -> None:
    """A bare `cable` facet on `item` (no length, no product): H2's only requirement."""
    plant.add(
        CableFacet(
            id=make_id(CableFacet, (key, "cable")),
            key=(key, "cable"),
            subject=item,
            length_mm=None,
        )
    )


def _cable_part(plant: Plant, key: str) -> Id[Part]:
    """A part that carries the `cable_product` facet (decision model-0108's `is_cable` rule),
    keyed distinctly so a test can add several."""
    part = Part(
        id=make_id(Part, (key, "part")),
        key=(key, "part"),
        mpn=f"MPN-{key}",
        manufacturer="Example Co",
        description="Invented",
        category=PartCategory.CABLE,
        class_code="W",
    )
    facet = CableProductFacet(
        id=make_id(CableProductFacet, (key, "part", "product")),
        key=(key, "part", "product"),
        subject=part.id,
        core_colours=(),
        gauge_mm2=Decimal("0.5"),
        shielded=False,
    )
    plant.add(part, facet)
    return part.id


def test_the_spec_worked_example_asserts_verbatim() -> None:
    """H1+H2 on the spec's own worked example: harness `W3` holds plugs `X1`, `X2` and cable
    `W1`; a parentless strip `X1'` placed at `+C1` is unaffected (spec's six results)."""
    plant = Plant()
    w3 = plant.item("w3", designation="W3")
    x1 = plant.item("x1", parent=w3, designation="X1")
    plant.item("x2", parent=w3, designation="X2")
    w1 = plant.item("w1", parent=w3, part=_cable_part(plant, "w1"), designation="W1")
    _cable_facet(plant, "w1", w1)
    x1_pin_1 = plant.port(plant.function(x1, "f"), "1")
    strip = plant.item("x1p", designation="X1")
    _place(plant, "x1p", _node(plant, "c1", Aspect.LOCATION, label="C1"), "p-loc")
    model = plant.model()
    assert item_designation(model, w1) == "W3"
    assert item_designation(model, x1) == "W3-X1"
    assert port_designation(model, x1_pin_1) == "-W3-X1:1"
    assert reference_designation(model, x1) == "-W3-X1"
    assert reference_designation(model, strip) == "+C1-X1"
    assert item_designation(model, w3) == "W3"


def test_a_rack_with_no_cable_child_is_not_a_harness_and_reads_flat() -> None:
    """H2's edge case (the spec's rack line): a part-less container with children is not a
    harness unless one of them carries a `cable` facet."""
    plant = Plant()
    rack = plant.item("a1", designation="A1")
    di1 = plant.item("di1", parent=rack, designation="DI1")
    plant.item("do1", parent=rack, designation="DO1")
    model = plant.model()
    assert reference_designation(model, di1) == "-DI1"


def test_a_board_inside_a_harness_prefixes_both_ways_board_netlist_stays_relative() -> None:
    """`W3-A1-K1` (H1 widens B3); `board_netlist(model, A1)` still reads `K1` (acceptance 4):
    `relative_to` drops the board and everything outside it, the harness included."""
    plant = Plant()
    w3 = plant.item("w3", designation="W3")
    w1 = plant.item("w1", parent=w3, part=_cable_part(plant, "w1"), designation="W1")
    _cable_facet(plant, "w1", w1)
    board = plant.item("board", part=_board_part(plant, "board"), parent=w3, designation="A1")
    k1 = plant.item("k1", parent=board, part=make_footprint(plant, "k", "K_0603"), designation="K1")
    model = plant.model()
    assert item_designation(model, k1) == "W3-A1-K1"
    netlist = board_netlist(model, board)
    assert [part.designation for part in netlist.parts] == ["K1"]


def test_relative_to_naming_a_harness_changes_nothing() -> None:
    """`relative_to` only ever matches a board (H1): naming the enclosing harness is a no-op,
    unchanged from `relative_to` naming any other non-board ancestor."""
    plant = Plant()
    w3 = plant.item("w3", designation="W3")
    w1 = plant.item("w1", parent=w3, part=_cable_part(plant, "w1"), designation="W1")
    _cable_facet(plant, "w1", w1)
    x1 = plant.item("x1", parent=w3, designation="X1")
    model = plant.model()
    assert item_designation(model, x1, relative_to=w3) == "W3-X1"


# ---- a harness or board with no designation (harness-tag-required work order, model-0043's
# amendment): the chain's own refusal, naming the ancestor, not the item's "run numbering"


def test_a_part_less_harness_with_no_designation_raises_naming_the_harness() -> None:
    """A part-less harness has no class letter, so numbering never gives it one (spec H2's
    amendment): `item_designation` on a member now refuses with the harness's own key and
    text, not the item's generic "run numbering" refusal."""
    plant = Plant()
    w3 = plant.item("w3")
    w1 = plant.item("w1", parent=w3, part=_cable_part(plant, "w1"), designation="W1")
    _cable_facet(plant, "w1", w1)
    x1 = plant.item("x1", parent=w3, designation="X1")
    model = plant.model()
    expected = "harness w3 has no designation: give it a tag"
    with pytest.raises(SchemaError, match=expected) as excinfo:
        item_designation(model, x1)
    assert excinfo.value.record_id == w3


def test_a_board_with_no_designation_raises_naming_the_board() -> None:
    """Same refusal shape, board wording: a board still gets a designation from numbering
    (it carries a `Part`), but until that pass runs, a member's `item_designation` now names
    the board and says to run numbering, not the item's own generic message."""
    plant = Plant()
    board = plant.item("board", part=_board_part(plant, "board"))
    k1 = plant.item("k1", parent=board, designation="K1")
    model = plant.model()
    expected = "board board has no designation: run numbering; its part needs a class code"
    with pytest.raises(SchemaError, match=re.escape(expected)) as excinfo:
        item_designation(model, k1)
    assert excinfo.value.record_id == board


def test_a_harness_with_a_part_and_no_tag_is_numbered_by_its_class_code() -> None:
    """PART 2 (harness-tag-required work order): `tag` is required only at authoring time
    (author-0003) -- the model itself numbers a part-carrying harness exactly like any other
    class-lettered item. Built through `passes.numbering.number`, the pass that really
    assigns designations, not a hand-authored string: three earlier class-`W` items already
    take `W1`-`W3` in the harness's own sibling group, so the harness itself is numbered
    `W4`, and its member `X1` reads through it."""
    plant = Plant()

    def _w_part(key: str) -> Id[Part]:
        part = Part(
            id=make_id(Part, (key,)),
            key=(key,),
            mpn=f"MPN-{key}",
            manufacturer="Example Co",
            description="Invented",
            category=PartCategory.GENERIC,
            class_code="W",
        )
        plant.add(part)
        return part.id

    plant.item("cbl-a", part=_w_part("cbl-a"))
    plant.item("cbl-b", part=_w_part("cbl-b"))
    plant.item("cbl-c", part=_w_part("cbl-c"))
    harness = plant.item("harness", part=_w_part("harness-part"))
    cable = plant.item(
        "cable", parent=harness, part=_cable_part(plant, "cable"), designation="CBL1"
    )
    _cable_facet(plant, "cable", cable)
    x1 = plant.item("x1", parent=harness, designation="X1")
    model, findings = number(plant.model())
    assert not findings
    assert item_designation(model, x1) == "W4-X1"
    assert reference_designation(model, x1) == "-W4-X1"


def _holder(plant: Plant, kind: str, tag: str | None) -> str:
    """A `board` or a `harness` item keyed `holder`, designated `tag` (`None`: no designation)."""
    if kind == "board":
        plant.item("holder", part=_board_part(plant, "board-part"), designation=tag)
    else:
        plant.item("holder", designation=tag)
        cable = plant.item(
            "cable", parent=_item_id("holder"), part=_cable_part(plant, "cable"), designation="C1"
        )
        _cable_facet(plant, "cable", cable)
    return "holder"


def _strip_case(kind: str | None, tag: str | None, strip_tag: str | None) -> tuple[Model, str]:
    plant = Plant()
    holder = None if kind is None else _holder(plant, kind, tag)
    plant.item("strip", parent=None if holder is None else _item_id(holder), designation=strip_tag)
    return plant.model(), "strip"


def _terminal_case(kind: str | None, tag: str | None, strip_tag: str | None) -> tuple[Model, str]:
    plant = Plant()
    holder = None if kind is None else _holder(plant, kind, tag)
    plant.item("strip", parent=None if holder is None else _item_id(holder), designation=strip_tag)
    _terminal(plant, "t1", "L1", 1, parent="strip")
    return plant.model(), "t1"


def test_designation_refusal_is_none_when_the_item_prints() -> None:
    """A numbered strip has nothing to refuse."""
    model, key = _strip_case(None, None, "X1")
    assert designation_refusal(model, _item_id(key)) is None


def test_designation_refusal_names_an_unknown_item() -> None:
    model, _ = _strip_case(None, None, "X1")
    refusal = designation_refusal(model, _item_id("nowhere"))
    assert refusal is not None
    assert str(refusal) == "the id is not an item of the model"


def test_designation_refusal_names_an_undesignated_board_ancestor() -> None:
    model, key = _strip_case("board", None, "X1")
    refusal = designation_refusal(model, _item_id(key))
    assert refusal is not None
    assert (
        str(refusal)
        == "board holder has no designation: run numbering; its part needs a class code"
    )


def test_designation_refusal_names_an_undesignated_harness_ancestor() -> None:
    model, key = _strip_case("harness", None, "X1")
    refusal = designation_refusal(model, _item_id(key))
    assert refusal is not None
    assert str(refusal) == "harness holder has no designation: give it a tag"


def test_designation_refusal_names_an_undesignated_holder() -> None:
    """A part-less strip (no `designation`, no `terminal` facet) is the label holder itself."""
    model, key = _strip_case(None, None, None)
    refusal = designation_refusal(model, _item_id(key))
    assert refusal is not None
    assert str(refusal) == (
        "the item has no designation; run the numbering pass, which needs a part class code"
    )


def test_designation_refusal_is_none_for_a_terminal_with_no_designation_of_its_own() -> None:
    """A terminal is its own label holder (a `terminal` facet stands in for `designation`)."""
    model, key = _terminal_case(None, None, "X1")
    assert designation_refusal(model, _item_id(key)) is None


@pytest.mark.parametrize(
    "case",
    [
        lambda: _strip_case(None, None, "X1"),
        lambda: _strip_case(None, None, None),
        lambda: _strip_case("board", "A1", "X1"),
        lambda: _strip_case("board", None, "X1"),
        lambda: _strip_case("harness", "W1", "X1"),
        lambda: _strip_case("harness", None, "X1"),
        lambda: _terminal_case(None, None, "X1"),
        lambda: _terminal_case(None, None, None),
        lambda: _terminal_case("board", None, "X1"),
        lambda: _terminal_case("harness", None, "X1"),
    ],
)
def test_item_designation_raises_exactly_what_designation_refusal_returns(
    case: Any,
) -> None:
    """`item_designation` raises `designation_refusal`'s return value, message included."""
    model, key = case()
    item = _item_id(key)
    refusal = designation_refusal(model, item)
    if refusal is None:
        assert item_designation(model, item)
    else:
        with pytest.raises(SchemaError) as excinfo:
            item_designation(model, item)
        assert str(excinfo.value) == str(refusal)


def test_can_print_designation_is_false_for_an_unknown_item() -> None:
    model, _ = _strip_case(None, None, "X1")
    assert can_print_designation(model, _item_id("nowhere")) is False
    with pytest.raises(SchemaError):
        item_designation(model, _item_id("nowhere"))
