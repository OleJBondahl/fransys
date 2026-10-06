"""Decision model-0071: a device with two or more labelled connectors prints `-A1-X1:1`.

`connector_segment` is the one rule; `port_designation`, `connector_designation`, `connector_rows`,
`stub_far_end` and the numbering pass's product-designation duplicate check all read it.
"""

from typing import TYPE_CHECKING

import pytest
from connector_builders import make_connector
from plant import Plant
from query_builders import make_node, make_placement

from fransys_model.derive import connector_rows, port_designation
from fransys_model.derive.designation import (
    connector_designation,
    connector_segment,
    prints_connector_label,
    product_designation,
)
from fransys_model.derive.drawing_text import stub_far_end
from fransys_model.derive.passes.numbering import PRODUCT_DESIGNATION_DUPLICATE, number
from fransys_model.kernel import SchemaError, make_id
from fransys_model.vocab.core import Function
from fransys_model.vocab.enums import FunctionKind

if TYPE_CHECKING:
    from fransys_model.kernel import Id
    from fransys_model.vocab.core import Item


def _device(plant: Plant, key: str = "a1", designation: str = "A1") -> None:
    plant.item(key, designation=designation)


def test_two_connectors_print_their_pins_behind_the_function_name() -> None:
    """(a) `-A1-X1:1`, `-A1-X2:1`, `-A1-X1:2`: the two same-named pins differ in their text."""
    # MUTATION: connector_segment `return f"-{label}"` -> `return ""` (every pin reads `-A1:1`)
    plant = Plant()
    _device(plant)
    _, x1 = make_connector(plant, ("a1", "X1"), ("1", "2"))
    _, x2 = make_connector(plant, ("a1", "X2"), ("1", "2"))
    model = plant.model()
    assert port_designation(model, x1["1"]) == "-A1-X1:1"
    assert port_designation(model, x2["1"]) == "-A1-X2:1"
    assert port_designation(model, x1["2"]) == "-A1-X1:2"
    assert port_designation(model, x1["1"]) != port_designation(model, x2["1"])


def test_a_facet_marking_wins_over_the_function_name() -> None:
    """(b) `marking="P1"` on X1 prints `-A1-P1:1`; X2 keeps its name."""
    # MUTATION: _connector_label `return function.name if marking is None else marking`
    #   -> `return function.name` (X1 pin 1 reads `-A1-X1:1`)
    plant = Plant()
    _device(plant)
    _, x1 = make_connector(plant, ("a1", "X1"), ("1",), marking="P1")
    _, x2 = make_connector(plant, ("a1", "X2"), ("1",))
    model = plant.model()
    assert port_designation(model, x1["1"]) == "-A1-P1:1"
    assert port_designation(model, x2["1"]) == "-A1-X2:1"


def test_one_labelled_connector_prints_as_before() -> None:
    """(c) a lone connector function: `-J1:1`, no segment."""
    # MUTATION: connector_segment `<= 1` -> `<= 0` (the lone connector reads `-J1-X1:1`)
    plant = Plant()
    _device(plant, "j1", "J1")
    function, pins = make_connector(plant, ("j1", "X1"), ("1",))
    model = plant.model()
    assert port_designation(model, pins["1"]) == "-J1:1"
    assert connector_segment(model, function) == ""


def test_a_connector_with_marking_empty_is_no_label_and_does_not_count() -> None:
    """(c) a labelled connector beside a `marking=""` shell: neither prints a segment."""
    # MUTATION: _connector_label `function.name if marking is None else marking` ->
    #   `function.name if not marking else marking` (the shell counts, X1 reads `-A1-X1:1`)
    plant = Plant()
    _device(plant)
    _, x1 = make_connector(plant, ("a1", "X1"), ("1",))
    _, shell = make_connector(plant, ("a1", "H"), ("PE",), marking="")
    model = plant.model()
    assert port_designation(model, x1["1"]) == "-A1:1"
    assert port_designation(model, shell["PE"]) == "-A1:PE"


def test_two_labelled_connectors_and_a_shell_print_segments_only_for_the_labelled() -> None:
    """(c) X1, X2 labelled, one shell: `-A1-X1:1`, `-A1-X2:1`, the shell `-A1:PE`."""
    # MUTATION: connector_segment `if not label or` -> `if` (the shell prints `-A1-:PE`)
    plant = Plant()
    _device(plant)
    _, x1 = make_connector(plant, ("a1", "X1"), ("1",))
    _, x2 = make_connector(plant, ("a1", "X2"), ("1",))
    _, shell = make_connector(plant, ("a1", "H"), ("PE",), marking="")
    model = plant.model()
    assert port_designation(model, x1["1"]) == "-A1-X1:1"
    assert port_designation(model, x2["1"]) == "-A1-X2:1"
    assert port_designation(model, shell["PE"]) == "-A1:PE"


def test_a_function_that_is_no_connector_prints_plain_on_a_multi_connector_item() -> None:
    """(d) a coil on an item with two connectors: `-A1:A1`, its pin name, never a segment."""
    # MUTATION: _connector_label delete the `FunctionKind.CONNECTOR` guard (the coil, whose
    #   template also carries a connector facet here, reads `-A1-K1:A1`)
    plant = Plant()
    _device(plant)
    make_connector(plant, ("a1", "X1"), ("1",))
    make_connector(plant, ("a1", "X2"), ("1",))
    _, coil = make_connector(plant, ("a1", "K1"), ("A1",), kind=FunctionKind.COIL)
    assert port_designation(plant.model(), coil["A1"]) == "-A1:A1"


def test_a_connector_with_no_facet_is_labelled_by_its_function_name() -> None:
    """(e) `gender=None` (no facet) counts, and prints its name: `-A1-J3:1`."""
    # MUTATION: _connector_label `marking = None if facet is None else facet.marking` ->
    #   `marking = "" if facet is None else facet.marking` (J3 stops counting: `-A1:1`)
    plant = Plant()
    _device(plant)
    _, x1 = make_connector(plant, ("a1", "X1"), ("1",))
    _, j3 = make_connector(plant, ("a1", "J3"), ("1",), gender=None)
    model = plant.model()
    assert port_designation(model, j3["1"]) == "-A1-J3:1"
    assert port_designation(model, x1["1"]) == "-A1-X1:1"


def test_prints_connector_label_says_which_functions_a_harness_end_may_read_its_facts_from() -> (
    None
):
    """(e2) a labelled connector prints a label; a `marking=""` shell and a coil do not."""
    # MUTATION: prints_connector_label `return bool(_connector_label(...))` -> `return True`
    plant = Plant()
    _device(plant)
    x1, _ = make_connector(plant, ("a1", "X1"), ("1",))
    shell, _ = make_connector(plant, ("a1", "shell"), ("PE",), marking="")
    coil, _ = make_connector(plant, ("a1", "K1"), ("A1",), kind=FunctionKind.COIL)
    model = plant.model()
    assert [prints_connector_label(model, f) for f in (x1, shell, coil)] == [True, False, False]


def test_an_unknown_function_is_a_schema_error_for_both_connector_readers() -> None:
    """(e3) neither `connector_segment` nor `prints_connector_label` guesses at an unknown id."""
    # MUTATION: either reader's `record is None` check removed (a `KeyError` or a wrong answer)
    plant = Plant()
    _device(plant)
    model = plant.model()
    missing = make_id(Function, ("nope",))
    for reader in (connector_segment, prints_connector_label):
        with pytest.raises(SchemaError):
            reader(model, missing)


def test_connector_rows_name_each_connector_and_its_mate_behind_the_device() -> None:
    """(f) rows `-A1-X1`, `-A1-X2` sorted; the mate's row and pin read `-A1-X1`, `-A1-X1:1`."""
    # MUTATION: connectors.py `designation=connector_designation(model, function.id, unit=unit)`
    #   -> `printed_designation(model, function.item, unit=unit)` (both rows read `-A1`)
    plant = Plant()
    board = plant.item("jb1", designation="JB1")
    plant.item("a1", parent=board, designation="A1")
    x1, _ = make_connector(plant, ("a1", "X1"), ("1", "2"))
    make_connector(plant, ("a1", "X2"), ("1", "2"))
    housing = plant.item("h1", designation="H1")
    p1, p1_pins = make_connector(plant, ("h1", "P1"), ("1", "2"))
    plant.mate(x1, p1)
    model = plant.model()
    assert [row.designation for row in connector_rows(model, board)] == ["-A1-X1", "-A1-X2"]
    (housing_row,) = connector_rows(model, housing)
    assert housing_row.mate_designation == "-A1-X1"
    assert housing_row.pins[0].mate_port_designation == "-A1-X1:1"
    assert housing_row.pins[0].port == p1_pins["1"]


def test_stub_far_end_heads_a_sub_part_pin_with_the_device_and_connector() -> None:
    """(g) `+C1-A1-X1` / `:1`, `+C1-A1-X2` / `:1`; a single-connector item keeps `+C1-J1`."""
    # MUTATION: drawing_text.stub_far_end `if segment:` -> `if False:` (the old head/tail split
    #   runs; the heads no longer read `+C1-A1-X1` / `+C1-A1-X2`)
    plant = Plant()
    node = make_node("c1", None)
    plant.add(node)
    for key, designation in (("a1", "A1"), ("j1", "J1")):
        item = plant.item(key, designation=designation)
        plant.add(make_placement(f"loc-{key}", item, node.id))
    _, x1 = make_connector(plant, ("a1", "X1"), ("1",))
    _, x2 = make_connector(plant, ("a1", "X2"), ("1",))
    _, j1 = make_connector(plant, ("j1", "X1"), ("1",))
    model = plant.model()
    assert stub_far_end(model, x1["1"]) == ("+C1-A1-X1", ":1")
    assert stub_far_end(model, x2["1"]) == ("+C1-A1-X2", ":1")
    assert stub_far_end(model, j1["1"]) == ("+C1-J1", ":1")


def test_an_own_root_drops_its_tag_and_keeps_the_connector_segment() -> None:
    """(h) unit `U2` with X1, X2: `-X1:1` in its own set, `-U2-X1:1` outside; child `K1` as ever."""
    # MUTATION: connector_designation `if segment and is_own_unit_root(...)` -> `if False and ...`
    #   (the own set reads `-U2-X1:1`)
    plant = Plant()
    unit = plant.unit("u")
    board = plant.item("u2", part=plant.board_part(), designation="U2", unit=unit)
    x1, x1_pins = make_connector(plant, ("u2", "X1"), ("1",))
    make_connector(plant, ("u2", "X2"), ("1",))
    plant.item("k1", parent=board, designation="K1", unit=unit)
    _, k1_pins = make_connector(plant, ("k1", "J1"), ("1",))
    model = plant.model()
    assert port_designation(model, x1_pins["1"], unit=unit) == "-X1:1"
    assert port_designation(model, x1_pins["1"]) == "-U2-X1:1"
    assert connector_designation(model, x1, unit=unit) == "-X1"
    assert connector_designation(model, x1) == "-U2-X1"
    assert port_designation(model, k1_pins["1"], unit=unit) == "-K1:1"
    assert port_designation(model, k1_pins["1"]) == "-U2-K1:1"


def test_only_the_root_drops_its_tag_a_child_with_two_connectors_keeps_it() -> None:
    """(h2) in `U2`'s own set the child `K1`'s connectors read `-K1-X1:1`, not `-X1:1`."""
    # MUTATION: connector_designation `if segment and is_own_unit_root(...)` -> `if segment` (the
    #   child's connector loses `-K1`)
    plant = Plant()
    unit = plant.unit("u")
    board = plant.item("u2", part=plant.board_part(), designation="U2", unit=unit)
    plant.item("k1", parent=board, designation="K1", unit=unit)
    _, x1 = make_connector(plant, ("k1", "X1"), ("1",))
    make_connector(plant, ("k1", "X2"), ("1",))
    model = plant.model()
    assert port_designation(model, x1["1"], unit=unit) == "-K1-X1:1"
    assert port_designation(model, x1["1"]) == "-U2-K1-X1:1"


def test_a_root_with_one_connector_keeps_its_tag_on_its_own_set() -> None:
    """(h3) a root's single connector adds no segment, so `-U2:1` stays (model-0071's limit)."""
    # MUTATION: connector_designation drops `segment and` from its condition (the single
    #   connector would print an empty text after the dash)
    plant = Plant()
    unit = plant.unit("u")
    plant.item("u2", part=plant.board_part(), designation="U2", unit=unit)
    _, j1 = make_connector(plant, ("u2", "J1"), ("1",))
    model = plant.model()
    assert port_designation(model, j1["1"], unit=unit) == "-U2:1"
    assert port_designation(model, j1["1"]) == "-U2:1"


def _board_with_child(child_designation: str) -> tuple[Plant, Id[Item], Id[Item]]:
    """Board `A1` (a `pcb` part) with connectors X1, X2 and a child item `child_designation`."""
    plant = Plant()
    board = plant.item("a1", part=plant.board_part(), designation="A1")
    make_connector(plant, ("a1", "X1"), ("1",))
    make_connector(plant, ("a1", "X2"), ("1",))
    child = plant.item("child", parent=board, designation=child_designation)
    return plant, board, child


def test_a_connector_label_equal_to_a_child_designation_is_one_duplicate() -> None:
    """(i) board `-A1` with connector X1 and a child `-X1` both print `-A1-X1`: one finding."""
    # MUTATION: numbering._connector_prints `return [product + segment for ...]` -> `return []`
    plant, board, child = _board_with_child("X1")
    _, findings = number(plant.model())
    (finding,) = [f for f in findings if f.code == PRODUCT_DESIGNATION_DUPLICATE]
    assert set(finding.subjects) == {board, child}
    assert "'-A1-X1'" in finding.message


def test_a_child_designation_that_matches_no_connector_label_is_no_duplicate() -> None:
    """(i) a child `-X3` prints `-A1-X3`: no finding, and the texts differ."""
    # MUTATION: numbering._connector_prints `product + segment` -> `product` (the board's own
    #   text is compared once per connector, so `-A1` collides with itself: a false finding)
    plant, _, child = _board_with_child("X3")
    model = plant.model()
    _, findings = number(model)
    assert [f for f in findings if f.code == PRODUCT_DESIGNATION_DUPLICATE] == []
    assert product_designation(model, child) == "-A1-X3"
