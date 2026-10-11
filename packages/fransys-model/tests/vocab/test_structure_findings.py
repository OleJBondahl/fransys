"""Tests: every finding code of `check_structure`, firing and not firing."""

from typing import Any

from fransys_model.kernel import Draft, Finding, Id, Model, Origin, Severity, freeze, make_id
from fransys_model.vocab.aspects import AspectNode, Placement
from fransys_model.vocab.core import Item
from fransys_model.vocab.enums import Aspect
from fransys_model.vocab.validators.structure import (
    ASPECT_CYCLE,
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


def test_two_nodes_that_are_each_others_parent_are_one_error_naming_both() -> None:
    """One finding per cycle, subjects its members, message the labels."""
    a, b = _node("a", parent="b"), _node("b", parent="a")
    (finding,) = _of(_freeze(a, b), ASPECT_CYCLE)
    assert (finding.severity, finding.subjects) == (Severity.ERROR, _ids(a, b))
    assert "A, B" in finding.message


# ---- ASPECT_CROSS_PARENT ------------------------------------------------------------------


# ---- PLACEMENT_DUPLICATE ------------------------------------------------------------------


# ---- CONTAINMENT_CYCLE --------------------------------------------------------------------


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
