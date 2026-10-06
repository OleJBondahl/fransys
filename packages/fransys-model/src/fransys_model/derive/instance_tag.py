"""UNIT-TAGS UT1, UT2: a unit instance's tag, and what a container prints for an item inside it.

Reached as `fransys_model.derive.instance_tag.<name>`, not re-exported from `derive/__init__.py`.
"""

lazy from collections.abc import Callable, Iterable

from fransys_model.derive.indexes import build_indexes
from fransys_model.derive.lookups import unit_chain
from fransys_model.vocab.facets.assigned_unit_tag import AssignedUnitTagFacet
from fransys_model.vocab.membership import (
    enclosing_boards,
    is_sole_unit_root,
    unit_items,
    unit_own_roots,
)
from fransys_model.vocab.tables import facets_of, items
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


def tag_chain(parts: Iterable[str]) -> str:
    """The one join of instance tags and own text: `U3-J1` (the printed form adds the dash)."""
    return "-".join(parts)


def instance_name(tags: Iterable[str]) -> str:
    """How a listing names an instance: `-U3`, nested `-U1-U3` (UT2)."""
    return "-" + tag_chain(tags)


def instance_tags(model: Model, item_unit: Id[Unit], view: Id[Unit] | None) -> tuple[str, ...]:
    """Tags of the instances from `view` (exclusive) down to `item_unit`, outermost first."""
    chain = unit_chain(model, item_unit)
    if view in chain:
        chain = chain[: chain.index(view)]
    if not chain or unit_tag(model, chain[0]) is None:
        return ()
    tags = (unit_tag(model, unit) for unit in reversed(chain))
    return tuple(tag for tag in tags if tag is not None)


def _stands_for_instance(model: Model, item: Id[Item]) -> bool:
    """Whether `item` is the sole board root of its unit: the instance tag names it (UT2)."""
    return is_sole_unit_root(model, item) and item in enclosing_boards(model, item)


def instance_designation(
    model: Model,
    item: Id[Item],
    *,
    relative_to: Id[Item] | None,
    unit: Id[Unit] | None,
    own: Callable[..., str],
) -> str | None:
    """The instance tags then `own`'s text (`-U3-J1`), else `None`; `own` avoids an import cycle."""
    record = items(model).get(item)
    if relative_to is not None or record is None or record.unit is None:
        return None
    tags = instance_tags(model, record.unit, unit)
    if not tags:
        return None
    if _stands_for_instance(model, item):
        return tag_chain(tags)
    return tag_chain((*tags, own(model, item, unit=record.unit)))


def unit_root(model: Model, item: Id[Item], unit: Id[Unit]) -> Id[Item] | None:
    """L4 (R2): `unit`'s sole root when `item` is below it, else `None` (its document drops it)."""
    if item not in unit_items(model, unit):
        return None
    roots = unit_own_roots(model, unit)
    root = roots[0] if len(roots) == 1 else None
    return None if root == item else root
