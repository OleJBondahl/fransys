"""WP13 tests: every finding code of `check_structure`, firing and not firing (design/vocabulary.md
6)."""

import dataclasses
import re
from typing import Any

from fransys_model.kernel import Draft, Finding, Id, Model, Origin, Severity, freeze, make_id
from fransys_model.vocab.aspects import AspectNode, Placement
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import Aspect
from fransys_model.vocab.validators.structure import (
    ASPECT_CROSS_PARENT,
    ASPECT_CYCLE,
    CONTAINMENT_CYCLE,
    PLACEMENT_DUPLICATE,
    check_structure,
)

_ORIGIN = Origin(file="test_structure_findings.py", line=1, note="fixture")


def _freeze(*records: Any) -> Model:
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def _node(key: str, aspect: Aspect = Aspect.LOCATION, *, parent: str | None = None) -> AspectNode:
    return AspectNode(
        id=make_id(AspectNode, (key,)),
        key=(key,),
        aspect=aspect,
        parent=None if parent is None else make_id(AspectNode, (parent,)),
        label=key.upper(),
        description="Invented",
    )


def _item(key: str, *, parent: str | None = None) -> Item:
    return Item(
        id=make_id(Item, (key,)),
        key=(key,),
        part=None,
        parent=None if parent is None else make_id(Item, (parent,)),
        position=None,
        tag=None,
        description="Invented",
    )


def _place(item: Item, node: AspectNode, key: str) -> Placement:
    return Placement(id=make_id(Placement, (key,)), key=(key,), item=item.id, node=node.id)


def _of(model: Model, code: str) -> list[Finding]:
    return [f for f in check_structure(model) if f.code == code]


def _ids(*records: Any) -> tuple[Id[Any], ...]:
    return tuple(sorted(record.id for record in records))


# ---- ASPECT_CYCLE -------------------------------------------------------------------------


def test_a_tree_of_aspect_nodes_has_no_finding() -> None:
    """A root, a child and a grandchild."""
    model = _freeze(_node("a"), _node("b", parent="a"), _node("c", parent="b"))
    assert check_structure(model) == ()


def test_two_nodes_that_are_each_others_parent_are_one_error_naming_both() -> None:
    """One finding per cycle, subjects its members, message the labels."""
    a, b = _node("a", parent="b"), _node("b", parent="a")
    (finding,) = _of(_freeze(a, b), ASPECT_CYCLE)
    assert (finding.severity, finding.subjects) == (Severity.ERROR, _ids(a, b))
    assert "A, B" in finding.message


def test_a_longer_cycle_is_still_one_finding() -> None:
    """Three nodes in a ring."""
    ring = [_node("a", parent="c"), _node("b", parent="a"), _node("c", parent="b")]
    (finding,) = _of(_freeze(*ring), ASPECT_CYCLE)
    assert finding.subjects == _ids(*ring)


def test_a_node_that_is_its_own_parent_is_a_cycle_of_one() -> None:
    """The smallest loop."""
    loner = _node("a", parent="a")
    (finding,) = _of(_freeze(loner), ASPECT_CYCLE)
    assert finding.subjects == (loner.id,)


def test_chains_leading_into_a_cycle_are_not_part_of_it() -> None:
    """Tails hang off the A-B loop at every depth: only A and B are members, whoever is first."""
    a, b = _node("a", parent="b"), _node("b", parent="a")
    tails = [_node(f"t{n}", parent="a") for n in range(8)]
    deeper = [_node(f"u{n}", parent=f"t{n}") for n in range(8)]
    (finding,) = _of(_freeze(a, b, *tails, *deeper), ASPECT_CYCLE)
    assert finding.subjects == _ids(a, b)


def test_two_separate_cycles_are_two_findings() -> None:
    """One per cycle."""
    nodes = [
        _node("a", parent="b"),
        _node("b", parent="a"),
        _node("c", parent="d"),
        _node("d", parent="c"),
    ]
    assert len(_of(_freeze(*nodes), ASPECT_CYCLE)) == 2


# ---- ASPECT_CROSS_PARENT ------------------------------------------------------------------


def test_a_node_under_a_node_of_another_aspect_is_an_error_naming_both() -> None:
    """Subjects: the node and its parent."""
    parent, child = _node("site", Aspect.LOCATION), _node("k1", Aspect.PRODUCT, parent="site")
    (finding,) = _of(_freeze(parent, child), ASPECT_CROSS_PARENT)
    assert (finding.severity, finding.subjects) == (Severity.ERROR, _ids(parent, child))
    assert "product node K1" in finding.message
    assert "location node SITE" in finding.message


def test_each_cross_parented_node_is_its_own_finding() -> None:
    """Two children of one foreign parent: two findings."""
    parent = _node("site", Aspect.LOCATION)
    kids = [_node(name, Aspect.PRODUCT, parent="site") for name in ("k1", "k2")]
    assert len(_of(_freeze(parent, *kids), ASPECT_CROSS_PARENT)) == 2


def test_a_root_and_a_same_aspect_child_are_no_cross_parent() -> None:
    """Only a differing aspect counts."""
    model = _freeze(_node("a"), _node("b", parent="a"), _node("c", Aspect.PRODUCT))
    assert _of(model, ASPECT_CROSS_PARENT) == []


# ---- PLACEMENT_DUPLICATE ------------------------------------------------------------------


def test_an_item_placed_twice_in_one_aspect_is_one_error_naming_the_placements() -> None:
    """Subjects: the item and both placements."""
    item, first, second = _item("k1"), _node("c1"), _node("c2")
    p1, p2 = _place(item, first, "p1"), _place(item, second, "p2")
    (finding,) = _of(_freeze(item, first, second, p1, p2), PLACEMENT_DUPLICATE)
    assert (finding.severity, finding.subjects) == (Severity.ERROR, _ids(item, p1, p2))
    assert "2 times" in finding.message
    assert "location" in finding.message


def test_three_placements_are_one_finding() -> None:
    """One per item and aspect, however many."""
    item = _item("k1")
    nodes = [_node(name) for name in ("c1", "c2", "c3")]
    placed = [_place(item, node, f"p{n}") for n, node in enumerate(nodes)]
    (finding,) = _of(_freeze(item, *nodes, *placed), PLACEMENT_DUPLICATE)
    assert "3 times" in finding.message


def test_one_placement_per_aspect_is_fine() -> None:
    """A product and a location placement of one item."""
    item, product, location = _item("k1"), _node("k1n", Aspect.PRODUCT), _node("c1")
    placed = (_place(item, product, "p1"), _place(item, location, "p2"))
    assert _of(_freeze(item, product, location, *placed), PLACEMENT_DUPLICATE) == []


def test_two_items_in_one_node_are_fine() -> None:
    """Different items may share a node."""
    first, second, node = _item("k1"), _item("k2"), _node("c1")
    placed = (_place(first, node, "p1"), _place(second, node, "p2"))
    assert _of(_freeze(first, second, node, *placed), PLACEMENT_DUPLICATE) == []


def test_duplicates_in_two_aspects_are_two_findings() -> None:
    """One finding per (item, aspect)."""
    item = _item("k1")
    nodes = [
        _node("l1"),
        _node("l2"),
        _node("f1", Aspect.FUNCTION),
        _node("f2", Aspect.FUNCTION),
    ]
    placed = [_place(item, node, f"p{n}") for n, node in enumerate(nodes)]
    assert len(_of(_freeze(item, *nodes, *placed), PLACEMENT_DUPLICATE)) == 2


# ---- CONTAINMENT_CYCLE --------------------------------------------------------------------


def test_items_in_a_chain_have_no_containment_cycle() -> None:
    """A strip, a terminal and a terminal's part."""
    model = _freeze(_item("strip"), _item("t1", parent="strip"), _item("t1a", parent="t1"))
    assert check_structure(model) == ()


def test_items_that_contain_each_other_are_one_error_naming_both() -> None:
    """One finding per cycle."""
    a, b = _item("a", parent="b"), _item("b", parent="a")
    (finding,) = _of(_freeze(a, b), CONTAINMENT_CYCLE)
    assert (finding.severity, finding.subjects) == (Severity.ERROR, _ids(a, b))
    assert "a, b" in finding.message


def test_an_item_inside_itself_and_a_tail_into_a_cycle() -> None:
    """A loner is a cycle of one; a child hanging off a cycle is not a member."""
    loner = _item("loner", parent="loner")
    a, b, tail = _item("a", parent="b"), _item("b", parent="a"), _item("tail", parent="a")
    findings = _of(_freeze(loner, a, b, tail), CONTAINMENT_CYCLE)
    assert sorted(f.subjects for f in findings) == sorted([(loner.id,), _ids(a, b)])


# ---- the shape of the result --------------------------------------------------------------


def _mixed() -> Model:
    item, first, second = _item("k1"), _node("c1"), _node("c2")
    return _freeze(
        item,
        first,
        second,
        _place(item, first, "p1"),
        _place(item, second, "p2"),
        _node("x", parent="y"),
        _node("y", parent="x"),
        _node("k", Aspect.PRODUCT, parent="c1"),
        _item("i", parent="j"),
        _item("j", parent="i"),
    )


def test_findings_come_back_sorted_and_all_four_codes_are_there() -> None:
    """Sorted by `(code, subjects, message)`."""
    findings = check_structure(_mixed())
    assert {f.code for f in findings} == {
        ASPECT_CYCLE,
        ASPECT_CROSS_PARENT,
        PLACEMENT_DUPLICATE,
        CONTAINMENT_CYCLE,
    }
    assert findings == tuple(sorted(findings, key=lambda f: (f.code, f.subjects, f.message)))


def test_the_findings_do_not_depend_on_the_order_of_a_models_tables() -> None:
    """Tables backwards, under another digest: the same findings."""
    model = _mixed()
    backwards = dataclasses.replace(
        model,
        digest="reversed-tables-test-structure-findings",  # unique: the caches key on digest
        tables=frozendict(
            {
                kind: frozendict(reversed(table.items()))
                for kind, table in reversed(model.tables.items())
            }
        ),
    )
    assert check_structure(backwards) == check_structure(model)


def test_no_message_prints_an_id() -> None:
    """Messages name labels and keys."""
    for finding in check_structure(_mixed()):
        assert finding.message
        assert not re.search(r"[0-9a-f]{32}", finding.message)


def test_an_empty_model_has_no_finding() -> None:
    """Nothing to check."""
    assert check_structure(_freeze()) == ()
