"""`external=` on `item`, `strip`, `cable` and `harness`."""

import pytest
from fransys_author.design import Design

from fransys_model import derive
from fransys_model.kernel import Draft, freeze, merge
from fransys_model.vocab import Conductor
from fransys_model.vocab import Item as ModelItem


def _items(draft: Draft) -> dict[tuple[str, ...], ModelItem]:
    found: dict[tuple[str, ...], ModelItem] = {r.key: r for r in draft.records() if isinstance(r, ModelItem)}
    assert len(found) > 0
    return found


@pytest.mark.parametrize(
    ("method", "args", "on", "off"),
    [("item", ("TEST-RLY-2CO",), "K1", "K2"), ("item", (None,), "A1", "A2"), ("harness", (), "WH1", "WH2")],
)
def test_item_carries_external_and_defaults_to_false(parts, method, args, on, off):
    d = Design(parts)
    getattr(d, method)(*args, tag=on, external=True)
    getattr(d, method)(*args, tag=off)
    items = _items(d.draft())
    assert items[(on,)].external is True
    assert items[(off,)].external is False


def test_external_part_item_flags_the_item_record_only(parts):
    d = Design(parts)
    d.item("TEST-RLY-2CO", tag="K1", external=True)
    records = tuple(r for r in d.draft().records() if isinstance(r, ModelItem))
    assert len(records) == 1
    assert records[0].external is True


def test_external_strip_is_external_for_its_terminals_through_the_parent_chain(parts):
    d = Design(parts)
    x1 = d.strip("X1", external=True)
    x2 = d.strip("X2")
    ext_terminals = [x1.terminal("TEST-TB"), x1.terminal("TEST-TB")]
    plain_terminals = [x2.terminal("TEST-TB"), x2.terminal("TEST-TB")]
    assert len(ext_terminals) == 2
    assert len(plain_terminals) == 2
    items = _items(d.draft())
    assert items[("X1",)].external is True
    assert items[("X2",)].external is False
    for terminal in ext_terminals:
        assert items[terminal.key].external is False
    model = freeze(merge(parts, d.draft()))
    assert all(derive.external(model, t.id) for t in ext_terminals)
    assert not any(derive.external(model, t.id) for t in plain_terminals)


def test_external_cable_flags_its_item_and_not_its_conductors(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    w1 = d.cable("TEST-CBL-2", tag="W1", external=True)
    w2 = d.cable("TEST-CBL-2", tag="W2")
    w1.core(1, t1.outer, t2.outer)
    items = _items(d.draft())
    assert items[("W1",)].external is True
    assert items[("W2",)].external is False
    conductors = tuple(r for r in d.draft().records() if isinstance(r, Conductor))
    assert len(conductors) == 1
    assert conductors[0].carrier == w1.id
    assert w2.id != w1.id
    model = freeze(merge(parts, d.draft()))
    assert derive.external(model, w1.id) is True
    assert derive.external(model, x1.id) is False
    assert derive.external(model, t1.id) is False


def test_scope_and_unit_scope_pass_external_through(parts):
    d = Design(parts)
    for scope in (d.scope("p1"), d.unit("u1", revision=1, interface="x")):
        scope.item("TEST-RLY-2CO", tag="K1", external=True)
        scope.item(None, tag="A1", external=True)
        scope.strip("X1", external=True)
        scope.cable("TEST-CBL-2", tag="W1", external=True)
        scope.harness(tag="WH1", external=True)
    items = _items(d.draft())
    flagged = [item for item in items.values() if item.tag is not None]
    assert len(flagged) == 10
    assert all(item.external for item in flagged)
