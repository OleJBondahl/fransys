"""`harness_wires` lists a harness's wires beside its cables (HA3, model-0171)."""

from decimal import Decimal
from typing import Any

import fransys as fr
import pytest
from fransys.colours import BK, BU

from fransys_model.derive import WireRow, harness_wires, wire_rows
from fransys_model.kernel import Id, SchemaError
from fransys_model.vocab.tables import items

_PLUG = "DEMO-CONN-2P"


def _loom(d: fr.Design, tag: str, *, wires: bool = True) -> Any:
    """Harness `tag` with plugs J1, J2; `wires` adds a labelled BU and an unlabelled BK wire."""
    with d.function(tag, f"Loom {tag}"):
        loom = d.harness(tag, place="L0")
        near = d.device("J1", _PLUG, parent=loom, place="L0")
        far = d.device("J2", _PLUG, parent=loom, place="L0")
        if wires:
            d.wire(near[1], far[1], wire=(BU, 0.5), label="SIG")
            d.wire(near[2], far[2], wire=(BK, 1.5))


@pytest.fixture(scope="module")
def model() -> fr.Model:
    """W1: two wires. W2: one wire's worth of plugs, none wired. X: a loose wire."""
    d = fr.design("demo_parts")
    d.location("L0", "Workshop")
    _loom(d, "W1")
    _loom(d, "W2", wires=False)
    with d.function("X", "Loose"):
        a = d.device("A1", _PLUG, place="L0")
        b = d.device("A2", _PLUG, place="L0")
    d.wire(a[1], b[1], wire=(BU, 0.5))
    return fr.build(d).model


def _harness(model: fr.Model, tag: str) -> Id[Any]:
    (found,) = [i for i, item in items(model).items() if "/".join(item.key) == f"{tag}/{tag}"]
    return found


def test_a_harness_lists_its_two_wires_with_ends_colour_gauge_and_label(model: fr.Model) -> None:
    rows = harness_wires(model, _harness(model, "W1"))
    assert [type(row) for row in rows] == [WireRow, WireRow]
    assert [(r.from_, r.to, r.colour, r.cross_section_mm2, r.label) for r in rows] == [
        ("+L0-W1-J1:1", "+L0-W1-J2:1", "BU", Decimal("0.5"), "-W1-J1:1 -W1-J2:1"),
        ("+L0-W1-J1:2", "+L0-W1-J2:2", "BK", Decimal("1.5"), "-W1-J1:2 -W1-J2:2"),
    ]


def test_a_wire_not_on_the_harness_is_absent(model: fr.Model) -> None:
    rows = harness_wires(model, _harness(model, "W1"))
    assert all(r.from_.startswith("+L0-W1-") for r in rows)
    assert len(rows) == 2  # the loose wire X/A1-A2 is the third WIRE of the model


def test_a_harness_with_no_wires_returns_empty(model: fr.Model) -> None:
    assert harness_wires(model, _harness(model, "W2")) == ()


def test_a_non_item_raises_schema_error(model: fr.Model) -> None:
    with pytest.raises(SchemaError):
        harness_wires(model, "no-such-item")  # ty: ignore[invalid-argument-type] -- id of the wrong kind on purpose


def test_the_cabinet_wire_list_leaves_harness_wires_out_but_the_harness_keeps_them(
    model: fr.Model,
) -> None:
    """model-0179: `wire_rows` holds the loose wire only; `harness_wires` still lists W1's two."""
    cabinet = wire_rows(model)
    assert len(cabinet) == 1  # X, the loose wire
    assert not any("-W1-" in r.from_ for r in cabinet)
    assert len(harness_wires(model, _harness(model, "W1"))) == 2
