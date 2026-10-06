"""`external=` on `item`, `strip`, `cable` and `harness` (external-items spec Y1, Y2)."""

from fransys_author import Design

from fransys_model import derive
from fransys_model.kernel import Draft, freeze, merge
from fransys_model.vocab import Conductor
from fransys_model.vocab import Item as ModelItem


def _items(draft: Draft) -> dict[tuple[str, ...], ModelItem]:
    found = {r.key: r for r in draft.records() if isinstance(r, ModelItem)}
    assert len(found) > 0
    return found


def test_item_with_a_part_carries_external_and_defaults_to_false(parts):
    d = Design(parts)
    d.item("TEST-RLY-2CO", tag="K1", external=True)
    d.item("TEST-RLY-2CO", tag="K2")
    items = _items(d.draft())
    assert items[("K1",)].external is True
    assert items[("K2",)].external is False


def test_external_part_item_flags_the_item_record_only(parts):
    d = Design(parts)
    d.item("TEST-RLY-2CO", tag="K1", external=True)
    records = tuple(r for r in d.draft().records() if isinstance(r, ModelItem))
    assert len(records) == 1
    assert records[0].external is True


def test_part_less_item_carries_external_and_defaults_to_false(parts):
    d = Design(parts)
    d.item(None, tag="A1", external=True)
    d.item(None, tag="A2")
    items = _items(d.draft())
    assert items[("A1",)].external is True
    assert items[("A2",)].external is False


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


def test_external_harness_carries_the_flag(parts):
    d = Design(parts)
    d.harness(tag="WH1", external=True)
    d.harness(tag="WH2")
    items = _items(d.draft())
    assert items[("WH1",)].external is True
    assert items[("WH2",)].external is False


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
