"""A unit instance's tag, and what a container prints for an item inside it.

Reached as `fransys_model.derive.instance_tag.<name>`, not re-exported from `derive/__init__.py`.
"""

lazy from collections.abc import Iterable, Sequence

from fransys_model.derive.facts.units import (
    enclosing_boards,
    is_sole_unit_root,
    unit_items,
    unit_own_roots,
)
from fransys_model.derive.indexes import build_indexes
from fransys_model.derive.lookups import unit_chain
from fransys_model.vocab.designation_scheme import DESIGNATION_SCHEME
from fransys_model.vocab.enums import Aspect
from fransys_model.vocab.facets.assigned_unit_tag import AssignedUnitTagFacet
from fransys_model.vocab.tables import facets_of
from fransys_model.vocab.tables import units as units_table
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Item, Unit


def unit_tag(model: Model, unit: Id[Unit]) -> str | None:
    """The instance's own tag: the written one, else the numbering pass's, else `None`."""
    record = units_table(model)[unit]
    if record.tag is not None:
        return record.tag
    assigned = facets_of(model, AssignedUnitTagFacet)
    for facet in build_indexes(model).facets_by_subject.get(unit, ()):
        if facet in assigned:
            return assigned[facet].text
    return None


def dashed(text: str) -> str:
    """The printed form of a designation: its text behind the dash (`-U3`, `-Q11`)."""
    return DESIGNATION_SCHEME.signed(Aspect.PRODUCT, text)


def instance_name(tags: Iterable[str]) -> str:
    """How a listing names an instance: `-U3`, nested `-U1-U3`."""
    sign = DESIGNATION_SCHEME.sign(Aspect.PRODUCT)
    return DESIGNATION_SCHEME.join((sign, tag) for tag in tags)


def below[T](owners: Sequence[T], through: T | None) -> Sequence[T]:
    """`owners` (outermost first) after `through`; all of them when `through` is not among them."""
    if through is None or through not in owners:
        return owners
    return owners[owners.index(through) + 1 :]


def instance_tags(model: Model, item_unit: Id[Unit], view: Id[Unit] | None) -> tuple[str, ...]:
    """Tags of the instances from `view` (exclusive) down to `item_unit`, outermost first."""
    chain = tuple(unit_chain(model, item_unit))[::-1]
    if not chain or unit_tag(model, unit_chain(model, item_unit)[0]) is None:
        return ()
    tags = (unit_tag(model, unit) for unit in below(chain, view))
    return tuple(tag for tag in tags if tag is not None)


def stands_for_instance(model: Model, item: Id[Item]) -> bool:
    """Whether `item` is the sole board root of its unit: the instance tag names it."""
    return is_sole_unit_root(model, item) and item in enclosing_boards(model, item)


def unit_root(model: Model, item: Id[Item], unit: Id[Unit]) -> Id[Item] | None:
    """`unit`'s sole root when `item` is below it, else `None` (its document drops it)."""
    if item not in unit_items(model, unit):
        return None
    roots = unit_own_roots(model, unit)
    root = roots[0] if len(roots) == 1 else None
    return None if root == item else root
