"""Tests for `harness_line_ends`: branch numbering of a harness's line (model-0175)."""

import itertools
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from connector_builders import make_connector
from plant import Plant
from query_builders import make_core, make_part, make_pin

from fransys_model.derive import (
    check_side_hints,
    connector_at_line_end,
    draws_as_line,
    harness_line_ends,
    line_conductors,
)
from fransys_model.kernel import Id, SchemaError, Severity, make_id
from fransys_model.layout import Side, SideHint
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import PartCategory
from fransys_model.vocab.facets.cable import CableFacet, CableProductFacet
from fransys_model.vocab.facets.harness import HarnessFacet

if TYPE_CHECKING:
    from fransys_model.kernel import Model
    from fransys_model.vocab.core import Function, Port


class _Line:
    """Harness `WH1`, cable `W1`, plugs authored in `plugs` order and a plain device `B1`."""

    def __init__(self, plugs: tuple[str, ...]) -> None:
        self.plant = Plant()
        self.harness = self.plant.item("wh1", designation="WH1")
        part = make_part(self.plant, "cab", "MPN-cab", category=PartCategory.CABLE)
        self.plant.add(
            CableProductFacet(
                id=make_id(CableProductFacet, ("cab", "product")),
                key=("cab", "product"),
                subject=part,
                core_colours=tuple(f"c{n}" for n in range(len(plugs))),
                gauge_mm2=Decimal("0.5"),
                shielded=False,
            )
        )
        self.cable = self.plant.item("w1", parent=self.harness, part=part, designation="W1")
        self.plant.add(
            CableFacet(
                id=make_id(CableFacet, ("w1", "cable")),
                key=("w1", "cable"),
                subject=self.cable,
                length_mm=None,
            )
        )
        self.device = self.plant.item("b1", designation="B1")
        self.device_function = self.plant.function(self.device, "f")
        self.plugs: dict[str, Id[Function]] = {}
        for index, name in enumerate(plugs, start=1):
            self.plant.item(name.lower(), parent=self.harness, designation=name)
            function, ports = make_connector(self.plant, (name.lower(), "x"), ("1",))
            self.plugs[name] = function
            far = self.plant.port(self.device_function, f"p{index}")
            make_core(self.plant, f"core-{name}", self.cable, (ports["1"], far), index=index)

    def model(self) -> Model:
        return self.plant.model()

    def ends(self) -> tuple:
        return harness_line_ends(self.model(), self.harness)


def _order(line: _Line) -> list[str | None]:
    """The designation name of each end's plug, `None` for a fan-out, in branch order."""
    names = {function: name for name, function in line.plugs.items()}
    return [names.get(end.plug) for end in line.ends()]


def test_a_three_plug_harness_numbers_branches_in_plug_designation_order() -> None:
    """Authored -P3, -P1, -P2: branches follow the designations, not the authoring order."""
    line = _Line(("P3", "P1", "P2"))
    ends = line.ends()
    assert [end.branch for end in ends] == [1, 2, 3, 4]
    assert _order(line) == ["P1", "P2", "P3", None]


def test_plug_designations_sort_naturally() -> None:
    """-P2 comes before -P10, as a string sort would not have it."""
    assert _order(_Line(("P10", "P2", "P1"))) == ["P1", "P2", "P10", None]


def test_a_fan_out_end_has_no_plug_but_its_ports_and_comes_after_the_plugs() -> None:
    """The plain device the cores land on is last, holds the landed ports, mates nothing."""
    line = _Line(("P2", "P1"))
    *plugs, fan = line.ends()
    assert all(end.plug is not None and end.ports == () for end in plugs)
    assert fan.plug is None
    assert fan.mates is None
    assert len(fan.ports) == 2
    assert {end.harness for end in line.ends()} == {line.harness}


def test_a_mated_plug_names_the_other_function_and_an_unmated_plug_none() -> None:
    """Either side of `d.mate` is found; a plug nobody mates has `mates=None`."""
    line = _Line(("P1", "P2", "P3"))
    line.plant.item("j1", designation="J1")
    j1, _ = make_connector(line.plant, ("j1", "x"), ("1",))
    j2 = make_pin(line.plant, "j2", "J2")
    line.plant.mate(line.plugs["P1"], j1, key="m1")
    line.plant.mate(j1, line.plugs["P3"], key="m3")  # plug on the b side
    by_plug = {end.plug: end.mates for end in line.ends() if end.plug}
    assert by_plug[line.plugs["P1"]] == j1
    assert by_plug[line.plugs["P2"]] is None
    assert by_plug[line.plugs["P3"]] == j1
    assert j2 not in by_plug.values()


def test_a_subject_that_is_no_harness_or_cable_raises() -> None:
    """A plain item, and an id that is no item, are refused."""
    line = _Line(("P1",))
    with pytest.raises(SchemaError):
        harness_line_ends(line.model(), line.device)
    with pytest.raises(SchemaError):
        harness_line_ends(line.model(), make_id(Item, ("nowhere",)))


def test_a_plug_a_fan_out_pin_and_a_mated_interface_stand_at_a_line_end() -> None:
    """model-0176: `connector_at_line_end` is true for each fact the ends row names."""
    line = _Line(("P1", "P2"))
    line.plant.item("j1", designation="J1")
    j1, _ = make_connector(line.plant, ("j1", "x"), ("1",))
    line.plant.mate(line.plugs["P1"], j1, key="m1")
    model = line.model()
    assert connector_at_line_end(model, line.plugs["P2"])
    assert connector_at_line_end(model, line.device_function)
    assert connector_at_line_end(model, j1)


def test_a_connector_at_no_line_does_not() -> None:
    line = _Line(("P1",))
    line.plant.item("j9", designation="J9")
    j9, _ = make_connector(line.plant, ("j9", "x"), ("1",))
    assert not connector_at_line_end(line.model(), j9)


def test_a_model_without_a_harness_has_no_line_end() -> None:
    plant = Plant()
    plant.item("j1", designation="J1")
    function = make_connector(plant, ("j1", "x"), ("1",))[0]
    assert not connector_at_line_end(plant.model(), function)


def _hint(line: _Line, function: Id[Function], value: str) -> None:
    line.plant.add(
        SideHint(
            id=make_id(SideHint, ("hint", value)),
            key=("hint", value),
            function=function,
            side=Side.N,
        )
    )


def test_a_side_hint_on_a_line_end_gives_no_warning_and_one_off_a_line_does() -> None:
    """HL14: the hint on a plug is kept; the hint on a lone connector warns, naming it."""
    line = _Line(("P1", "P2"))  # two cores: the harness draws as a line
    line.plant.item("j9", designation="J9")
    j9, _ = make_connector(line.plant, ("j9", "x"), ("1",))
    _hint(line, line.plugs["P1"], "a")
    assert check_side_hints(line.model()) == ()
    _hint(line, j9, "b")
    (finding,) = check_side_hints(line.model())
    assert (finding.code, finding.severity, finding.subjects) == (
        "SIDE_HINT_NO_HARNESS_LINE",
        Severity.WARNING,
        (j9,),
    )
    assert "J9" in finding.message


def test_no_side_hint_no_warning() -> None:
    assert check_side_hints(_Line(("P1",)).model()) == ()


def _wired(plugs: tuple[str, ...], *, cable_plug: str | None = None) -> tuple[_Line, Model]:
    """Harness `WH1` marked, plugs `plugs`, each mated to its own `J` and wired to the next plug.

    Two single wires run plug to plug for each neighbouring pair. With `cable_plug`, `_Line`'s
    cable also lands one core on that plug, so cable ends and wire ends share one harness.
    """
    line = _Line((cable_plug,)) if cable_plug else _Line(())
    line.plant.add(
        HarnessFacet(id=make_id(HarnessFacet, ("mark",)), key=("mark",), subject=line.harness)
    )
    pins: dict[str, dict[str, Id[Port]]] = {}
    for name in plugs:
        line.plant.item(name.lower(), parent=line.harness, designation=name)
        function, found = make_connector(line.plant, (name.lower(), "x"), ("1", "2"))
        line.plugs[name], pins[name] = function, found
        line.plant.item(f"j{name.lower()}", designation=f"J{name}")
        mate, _ = make_connector(line.plant, (f"j{name.lower()}", "x"), ("1", "2"))
        line.plant.mate(function, mate, key=f"m-{name}")
    for left, right in itertools.pairwise(plugs):
        for pin in ("1", "2"):
            line.plant.wire(pins[left][pin], pins[right][pin], key=f"w-{left}-{right}-{pin}")
    return line, line.model()


def test_a_harness_of_single_wires_has_two_plug_ends_with_their_mates() -> None:
    """HL1, model-0175 amended: two plugs and two wires give two ends, plugs first, mates set."""
    line, model = _wired(("P2", "P1"))
    ends = harness_line_ends(model, line.harness)
    assert [(end.branch, end.plug) for end in ends] == [
        (1, line.plugs["P1"]),
        (2, line.plugs["P2"]),
    ]
    assert all(end.mates is not None and end.ports == () for end in ends)
    assert draws_as_line(model, line.harness)
    assert connector_at_line_end(model, line.plugs["P1"])


def test_a_mixed_harness_numbers_cable_ends_and_wire_ends_in_one_order() -> None:
    """A cable core on -P3 and wires between -P1 and -P2: plugs -P1, -P2, -P3, then B1's fan-out."""
    line, model = _wired(("P2", "P1"), cable_plug="P3")
    names = {function: name for name, function in line.plugs.items()}
    ends = harness_line_ends(model, line.harness)
    assert [(end.branch, names.get(end.plug)) for end in ends] == [
        (1, "P1"),
        (2, "P2"),
        (3, "P3"),
        (4, None),
    ]


def test_one_conductor_is_no_line_and_two_are() -> None:
    """HL1: a one-core harness does not draw as a line; its cable answers for it."""
    single, double = _Line(("P1",)), _Line(("P1", "P2"))
    assert not draws_as_line(single.model(), single.harness)
    assert not draws_as_line(single.model(), single.cable)
    assert draws_as_line(double.model(), double.cable)
    assert set(line_conductors(double.model())) == {double.harness}
    assert not draws_as_line(double.model(), double.device)
