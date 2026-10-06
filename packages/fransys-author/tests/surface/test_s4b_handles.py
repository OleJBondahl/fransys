"""EA15 handles and kinds: model ids, a tagless harness, net kind names, a unit child's history."""

from typing import Any

import pytest
from fransys_author import AuthorError
from fransys_author.surface import CONTROL, GENERIC, SIGNAL, design, unit

from fransys_model.vocab import Item as ModelItem
from fransys_model.vocab import NetClass
lazy from fransys_model.kernel import Draft


def _records(d, cls):
    return [r for r in d.draft().records() if isinstance(r, cls)]


def test_device_and_function_ids_are_the_records_ids(parts: Draft) -> None:
    d = design(parts, place="C1")
    k1 = d.device("K1", "TEST-RLY-2CO")
    (item,) = _records(d, ModelItem)
    assert k1.id == item.id
    assert k1.coil.id in {f.id for f in k1._item.functions}


def test_a_tagless_harness_takes_name(parts: Draft) -> None:
    d = design(parts, place="C1")
    w = d.harness(name="w1")
    (item,) = _records(d, ModelItem)
    assert item.tag is None
    assert "w1" in item.key
    assert w.id == item.id


def test_a_harness_with_neither_tag_nor_name_raises(parts: Draft) -> None:
    with pytest.raises(AuthorError, match="give a tag, or name= for a harness with no tag"):
        design(parts).harness()


def test_the_net_kinds_are_the_model_classes() -> None:
    assert (CONTROL, SIGNAL, GENERIC) == (NetClass.CONTROL, NetClass.SIGNAL, NetClass.GENERIC)


def test_net_defaults_to_control(parts: Draft) -> None:
    d = design(parts, place="C1")
    k1 = d.device("K1", "TEST-RLY-2CO")
    d.net("S1", k1.coil["A1"], k1.coil["A2"])
    nets: list[Any] = [r for r in d.draft().records() if type(r).__name__ == "Net"]
    (net,) = nets
    assert net.net_class is NetClass.CONTROL


def test_a_unit_child_refuses_revision_and_the_parent_does_not(parts: Draft) -> None:
    @unit("demo-io-board", revision=1, interface_version=1, date="d", text="t", by="XX")
    def board(d):
        d.revision(1, date="d", text="t", created="XX")
        return {}

    d = design(parts, place="C1")
    d.revision(1, date="d", text="t", created="XX")
    with pytest.raises(AuthorError, match=r"@fr\.unit\(history=\)"):
        d.add(board, "IO")
