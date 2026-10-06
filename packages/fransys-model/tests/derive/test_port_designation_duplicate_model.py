"""Decision model-0077: `PORT_DESIGNATION_DUPLICATE`, two ports of one item that print one text.

Why: two ports of one item printing the same designation (`-A1:7` twice, from two functions
each with a pin `7`) meet on one off-stub text in layout, and `_off_ends` raised `LayoutError`.
The numbering pass now reports it as an `ERROR` finding, one per (item, printed text) group of
more than one port, so the fix is made in the model: the part's pin markings.

What is compared is what `derive.designation.port_designation` prints, the one rule for a
port's text; a terminal (its two ports are one point) and an item that cannot print a
designation are left out.
"""

import dataclasses
from typing import TYPE_CHECKING

from connector_builders import make_connector
from plant import Plant
from query_builders import make_terminal

from fransys_model.derive import port_designation
from fransys_model.derive.designation import can_print_designation
from fransys_model.derive.passes.numbering import PORT_DESIGNATION_DUPLICATE, number
from fransys_model.kernel import Finding, Severity, make_id
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import FunctionKind

if TYPE_CHECKING:
    from fransys_model.kernel import Id
    from fransys_model.vocab.core import Port


def _dups(findings: tuple[Finding, ...]) -> list[Finding]:
    return [finding for finding in findings if finding.code == PORT_DESIGNATION_DUPLICATE]


def _device(plant: Plant, key: str = "A1") -> None:
    plant.item(key, designation=key)


def _coil(plant: Plant, item: str, function: str, pin: str = "7") -> Id[Port]:
    """A non-connector function `function` of `item` with one port `pin`."""
    _, ports = make_connector(plant, (item, function), (pin,), gender=None, kind=FunctionKind.COIL)
    return ports[pin]


def _mark(plant: Plant, port: Id[Port], marking: str) -> None:
    """Give the port already added to `plant` this `Port.marking`."""
    index = next(i for i, record in enumerate(plant.records) if record.id == port)
    plant.records[index] = dataclasses.replace(plant.records[index], marking=marking)


def test_two_functions_with_one_pin_name_on_an_item_are_one_finding() -> None:
    """(1) `ch1:7` and `ch2:7` of `A1` both print `-A1:7`: one ERROR, ports sorted, fix named."""
    # MUTATION: the group key `text` -> `port.id` (every port is its own group, no finding)
    plant = Plant()
    _device(plant)
    p1 = _coil(plant, "A1", "ch1")
    p2 = _coil(plant, "A1", "ch2")
    model = plant.model()
    assert port_designation(model, p1) == port_designation(model, p2) == "-A1:7"
    _, findings = number(model)
    (finding,) = _dups(findings)
    assert finding.severity is Severity.ERROR
    assert finding.subjects == tuple(sorted((p1, p2)))
    for part in ("A1", "ch1", "ch2", repr("-A1:7"), "pin markings"):
        assert part in finding.message
    for record_id in (p1, p2, make_id(Item, ("A1",))):
        assert str(record_id) not in finding.message


def test_three_functions_with_one_pin_name_are_still_one_finding() -> None:
    """(2) `ch1:7`, `ch2:7`, `ch3:7`: one finding, three subjects, three function names."""
    # MUTATION: report every pair (`combinations(group, 2)`) instead of the group: three findings
    plant = Plant()
    _device(plant)
    ports = [_coil(plant, "A1", name) for name in ("ch1", "ch2", "ch3")]
    _, findings = number(plant.model())
    (finding,) = _dups(findings)
    assert finding.subjects == tuple(sorted(ports))
    for name in ("ch1", "ch2", "ch3"):
        assert name in finding.message


def test_two_labelled_connectors_with_one_pin_name_print_apart_and_are_no_finding() -> None:
    """(3) `X1:1` and `X2:1` print `-A1-X1:1` and `-A1-X2:1` (model-0071): nothing to report."""
    # MUTATION: compare `port.name` instead of `port_designation` (both pins are `1`: a finding)
    plant = Plant()
    _device(plant)
    _, x1 = make_connector(plant, ("A1", "X1"), ("1",))
    _, x2 = make_connector(plant, ("A1", "X2"), ("1",))
    model = plant.model()
    assert port_designation(model, x1["1"]) == "-A1-X1:1"
    assert port_designation(model, x2["1"]) == "-A1-X2:1"
    _, findings = number(model)
    assert _dups(findings) == []


def test_a_differing_port_marking_does_not_tell_two_equal_names_apart() -> None:
    """(4a) two ports named `7` with markings `A` and `B` still print `-A1:7` twice: one finding.

    The work order's "a marking counts" is read as "as `port_designation` prints it", which is
    the port's name, never `Port.marking`.
    """
    # MUTATION: the group key `text` -> `(port.marking, text)` (the markings differ: no finding)
    plant = Plant()
    _device(plant)
    p1 = _coil(plant, "A1", "ch1")
    p2 = _coil(plant, "A1", "ch2")
    _mark(plant, p1, "A")
    _mark(plant, p2, "B")
    model = plant.model()
    assert port_designation(model, p1) == port_designation(model, p2) == "-A1:7"
    _, findings = number(model)
    (finding,) = _dups(findings)
    assert finding.subjects == tuple(sorted((p1, p2)))
    assert repr("-A1:7") in finding.message


def test_a_shared_port_marking_does_not_join_two_different_names() -> None:
    """(4b) ports named `7` and `8` that both carry the marking `P` print apart: no finding."""
    # MUTATION: the group key `text` -> `port.marking` (both read `P`: a finding)
    plant = Plant()
    _device(plant)
    p1 = _coil(plant, "A1", "ch1", "7")
    p2 = _coil(plant, "A1", "ch2", "8")
    _mark(plant, p1, "P")
    _mark(plant, p2, "P")
    model = plant.model()
    assert port_designation(model, p1) == "-A1:7"
    assert port_designation(model, p2) == "-A1:8"
    _, findings = number(model)
    assert _dups(findings) == []


def test_a_terminal_prints_one_text_on_both_ports_on_purpose() -> None:
    """(5) a terminal's internal and external port are one point: no finding, no raise."""
    # MUTATION: delete the terminal exclusion (both ports print `-X1:L1:1`: a finding)
    plant = Plant()
    plant.item("strip", designation="X1")
    terminal = make_terminal(plant, "strip", "t1", group="L1", index=1)
    model = plant.model()
    assert (
        port_designation(model, terminal.internal)
        == port_designation(model, terminal.external)
        == "-X1:L1:1"
    )
    _, findings = number(model)
    assert _dups(findings) == []


def test_one_pin_name_on_two_different_items_is_no_finding() -> None:
    """(6) `A1:7` and `A2:7` print `-A1:7` and `-A2:7`, and are compared per item at that."""
    # MUTATION: group the ports of the whole model by `port.name` instead of the ports of one
    #   item by `port_designation` (both ports are `7`: a finding)
    plant = Plant()
    _device(plant, "A1")
    _device(plant, "A2")
    p1 = _coil(plant, "A1", "ch1")
    p2 = _coil(plant, "A2", "ch1")
    model = plant.model()
    assert port_designation(model, p1) == "-A1:7"
    assert port_designation(model, p2) == "-A2:7"
    _, findings = number(model)
    assert _dups(findings) == []


def test_an_item_that_cannot_print_is_skipped_and_a_printable_one_still_reports() -> None:
    """(7) a part-less item with no designation and two alike ports: no finding, no raise.

    The second, printable item `A1` with a real duplicate gives exactly one finding, so the skip
    is not a blanket disable.
    """
    # MUTATION: delete the `can_print_designation` skip (`port_designation` raises `SchemaError`
    #   for the ghost); or replace it with `return ()` (the `A1` finding disappears)
    plant = Plant()
    ghost = plant.item("ghost")
    _coil(plant, "ghost", "ch1")
    _coil(plant, "ghost", "ch2")
    _device(plant)
    p1 = _coil(plant, "A1", "ch1")
    p2 = _coil(plant, "A1", "ch2")
    model = plant.model()
    assert not can_print_designation(model, ghost)
    _, findings = number(model)
    (finding,) = _dups(findings)
    assert finding.subjects == tuple(sorted((p1, p2)))


def test_ports_of_different_names_are_no_finding() -> None:
    """(8) a coil `A1`, `A2` beside a second function `B1`, `B2`: four texts, no finding."""
    # MUTATION: group by `port.role` (every port is `GENERIC`, so four ports would collide)
    plant = Plant()
    _device(plant)
    make_connector(plant, ("A1", "coil"), ("A1", "A2"), gender=None, kind=FunctionKind.COIL)
    make_connector(plant, ("A1", "aux"), ("B1", "B2"), gender=None, kind=FunctionKind.COIL)
    _, findings = number(plant.model())
    assert _dups(findings) == []


def _two_duplicated_items(plant: Plant, names: tuple[str, ...]) -> None:
    for item in ("A1", "A2"):
        _device(plant, item)
        for name in names:
            _coil(plant, item, name)


def test_findings_come_back_in_a_fixed_order_whatever_the_order_of_the_records() -> None:
    """(9) two duplicated items: sorted by (subjects, message), the same when added in reverse."""
    # MUTATION: `subjects=tuple(sorted(...))` -> `subjects=tuple(...)` (subjects follow the order
    #   the records were added, so the reversed plant differs)
    forward = Plant()
    _two_duplicated_items(forward, ("ch1", "ch2"))
    backward = Plant()
    _two_duplicated_items(backward, ("ch1", "ch2"))
    backward.records.reverse()
    _, forward_findings = number(forward.model())
    _, backward_findings = number(backward.model())
    forward_dups = _dups(forward_findings)
    assert len(forward_dups) == 2
    assert forward_dups == sorted(forward_dups, key=lambda f: (f.subjects, f.message))
    assert forward_dups == _dups(backward_findings)
