"""A wire on a harness plug belongs to that harness (HA2, model-0171, model-0148)."""

from typing import TYPE_CHECKING, Any

import fransys as fr
import pytest
from fransys.colours import BU

from fransys_model.derive import item_designation, printed_designation
from fransys_model.derive.wire_harness import harness_of_wire
from fransys_model.vocab.enums import ConductorKind
from fransys_model.vocab.tables import conductors, functions, items, ports

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.connectivity import Conductor
    from fransys_model.vocab.core import Item

_PLUG = "DEMO-CONN-2P"
_CABLE = "DEMO-CBL-4G1.5"
_TWO = "WIRE_ON_TWO_HARNESSES"


def _loom(d: fr.Design, tag: str, *, cable: bool = False, wire: bool = False) -> Any:
    """Harness `tag` with plugs J1, J2; an optional cable on pin 1 and an optional wire on pin 2.

    Returns the plug J1.
    """
    with d.function(tag, f"Loom {tag}"):
        loom = d.harness(tag, place="L0")
        near = d.device("J1", _PLUG, parent=loom, place="L0")
        far = d.device("J2", _PLUG, parent=loom, place="L0")
        if cable:
            d.cable(tag, _CABLE, parent=loom, name=f"cable{tag}", place="L0").core(
                1, near[1], far[1]
            )
        if wire:
            d.wire(near[2], far[2], wire=(BU, 0.5))
    return near, far


@pytest.fixture(scope="module")
def built() -> fr.BuildResult:
    """W1: cable and wire. W2: cable only. W3 and W4: plugs only. X: a loose wire."""
    d = fr.design("demo_parts")
    d.location("L0", "Workshop")
    _loom(d, "W1", cable=True, wire=True)
    _loom(d, "W2", cable=True)
    _loom(d, "W3")
    _loom(d, "W4")
    with d.function("X", "Loose"):
        a = d.device("A1", _PLUG, place="L0")
        b = d.device("A2", _PLUG, place="L0")
    d.wire(a[1], b[1], wire=(BU, 0.5))
    return fr.build(d)


def _key(model: Model, item: Id[Item]) -> str:
    return "/".join(items(model)[item].key)


def _wires(model: Model) -> dict[frozenset[str], Conductor]:
    """Every WIRE conductor by the key texts of the items at its two ends."""
    return {
        frozenset(
            _key(model, functions(model)[ports(model)[end].function].item) for end in (c.a, c.b)
        ): c
        for c in conductors(model).values()
        if c.kind is ConductorKind.WIRE
    }


def test_a_wire_on_a_harness_plug_is_that_harness_wire_and_has_no_carrier(
    built: fr.BuildResult,
) -> None:
    model = built.model
    wire = _wires(model)[frozenset({"W1/J1", "W1/J2"})]
    harness = harness_of_wire(model, wire.id)
    assert harness is not None
    assert _key(model, harness) == "W1/W1"
    assert wire.carrier is None


def test_a_wire_with_no_end_on_a_harness_has_none(built: fr.BuildResult) -> None:
    wire = _wires(built.model)[frozenset({"X/A1", "X/A2"})]
    assert harness_of_wire(built.model, wire.id) is None


def test_a_wire_between_plugs_of_two_harnesses_is_an_error(built: fr.BuildResult) -> None:
    d = fr.design("demo_parts")
    d.location("L0", "Workshop")
    d.wire(_loom(d, "W3")[0][1], _loom(d, "W4")[0][1], wire=(BU, 0.5))
    result = fr.build(d)
    (finding,) = [f for f in result.findings if f.code == _TWO]
    wire = next(iter(_wires(result.model).values()))
    assert finding.subjects == (wire.id,)
    assert harness_of_wire(result.model, wire.id) is None  # two harnesses name none
    assert "W3" in finding.message
    assert "W4" in finding.message
    assert not [f for f in built.findings if f.code == _TWO]


def _lone_print(model: Model, cable: str) -> str:
    (id_,) = [i for i, item in items(model).items() if "/".join(item.key) == cable]
    return printed_designation(model, id_)


def test_a_cable_prints_long_beside_a_single_wire_and_short_alone(built: fr.BuildResult) -> None:
    assert _lone_print(built.model, "W1/cableW1") == "-W1-W1"
    assert _lone_print(built.model, "W2/cableW2") == "-W2"


def test_a_cable_less_harness_prints_its_plugs_under_its_tag(built: fr.BuildResult) -> None:
    """Can-fail: an unmarked cable-less harness prints its plugs `J1`, not `W3-J1`."""
    named = {
        "/".join(i.key): item_designation(built.model, i.id) for i in items(built.model).values()
    }
    assert named["W3/J1"] == "W3-J1"
    assert named["W4/J2"] == "W4-J2"
