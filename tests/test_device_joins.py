"""`d.device(..., parent=, joins=)` fits a connector item on its parent's own leads (HA5, HA6).

Built through the public API on `DEMO-CTR-LEADS`, a contactor on flying leads, and a housing.
"""

from typing import Any

import fransys as fr
import pytest
from fransys_author import AuthorError

from fransys_model.derive import item_designation
from fransys_model.kernel import Severity
from fransys_model.vocab import ConductorKind
from fransys_model.vocab.tables import conductors, items

_CTR = "DEMO-CTR-LEADS"
_HOUSING = "DEMO-CONN-4P"


def _design() -> fr.Design:
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    return d


def _leads(result: fr.BuildResult) -> list[frozenset]:
    return [
        frozenset((c.a, c.b))
        for c in conductors(result.model).values()
        if c.kind is ConductorKind.LEAD
    ]


def test_the_worked_example_fits_a_housing_on_four_leads() -> None:
    """Can-fail: a `joins=` that writes no link, or a wrong pair, fails the ends or the count."""
    d = _design()
    with d.function("K", "Contactor control"):
        k1 = d.device("K1", _CTR)
        j1 = d.device(
            "J1",
            _HOUSING,
            parent=k1,
            joins={"1": k1.coil["A1"], 2: k1.coil["A2"], "3": k1.aux["13"], "4": k1.aux["14"]},
        )
    result = fr.build(d)
    wanted = [
        frozenset((k1.coil["A1"].id, j1[1].id)),
        frozenset((k1.coil["A2"].id, j1[2].id)),
        frozenset((k1.aux["13"].id, j1[3].id)),
        frozenset((k1.aux["14"].id, j1[4].id)),
    ]
    assert sorted(map(sorted, _leads(result))) == sorted(map(sorted, wanted))
    assert not [f for f in result.findings if f.severity is Severity.ERROR]
    named = {i.tag: item_designation(result.model, i.id) for i in items(result.model).values()}
    assert named["J1"] == "K1-J1"


def _refused(**joins_for: Any) -> AuthorError:
    """The error `d.device("J1", ...)` raises with the given `parent` and `joins`."""
    d = _design()
    with d.function("K", "Contactor control"):
        k1 = d.device("K1", _CTR)
        other = d.device("K2", _CTR)
        strip = d.terminal_strip("X1", "DEMO-TB-2.5")
        scope = {"k1": k1, "other": other, "strip": strip}
        parent = scope[str(joins_for.pop("parent", "k1"))] if "parent" in joins_for else None
        joins = joins_for["joins"]
        resolved = joins(scope) if callable(joins) else joins
        with pytest.raises(AuthorError) as caught:
            d.device("J1", _HOUSING, parent=parent, joins=resolved)
    return caught.value


def test_joins_without_a_parent_device_raises() -> None:
    """Can-fail: skipping the parent check lets a join with no parent write a link."""
    error = _refused(joins=lambda s: {"1": s["k1"].coil["A1"]})
    assert "needs parent=" in str(error)


def test_joins_with_a_strip_parent_raises() -> None:
    """Can-fail: accepting any parent object fits a housing on a strip."""
    error = _refused(parent="strip", joins=lambda s: {"1": s["k1"].coil["A1"]})
    assert "needs parent=" in str(error)


def test_a_port_of_another_device_raises() -> None:
    """Can-fail: not checking the port's owner lets K2's pin join K1's housing."""
    error = _refused(parent="k1", joins=lambda s: {"1": s["other"].coil["A1"]})
    assert "not a pin of K1" in str(error)


def test_a_string_value_raises() -> None:
    """Can-fail: accepting a string as a port names no pin."""
    error = _refused(parent="k1", joins={"1": "A1"})
    assert "'A1' is not a pin of K1" in str(error)


def test_a_key_that_is_no_pin_of_the_new_item_raises() -> None:
    """Can-fail: not resolving the key on the new item lets a missing pin pass."""
    error = _refused(parent="k1", joins=lambda s: {"9": s["k1"].coil["A1"]})
    assert "no pin '9'" in str(error)


def test_one_parent_port_twice_raises() -> None:
    """Can-fail: a missing uniqueness check on the parent's ports writes two leads on one pin."""
    error = _refused(
        parent="k1", joins=lambda s: {"1": s["k1"].coil["A1"], "2": s["k1"].coil["A1"]}
    )
    assert "pin 'A1' of K1 twice" in str(error)


def test_one_new_pin_twice_by_two_spellings_raises() -> None:
    """Can-fail: comparing keys, not pins, lets 1 and "1" name the same pin."""
    error = _refused(
        parent="k1",
        joins=lambda s: {1: s["k1"].coil["A1"], "1": s["k1"].coil["A2"]},
    )
    assert "pin '1' of J1 twice" in str(error)
