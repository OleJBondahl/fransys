"""Private to `write/`: the `DrawingSet` and `Page` builders.

Refs: engine.md 7, model layout-namespace.md.

Every key is `("layout", "schematic", <kind>)` plus the key of the record the new record is
about plus its discriminator, and never holds a page number or a position, so ids survive
repagination. Each builder returns records only; `write/__init__.py` puts them in one `evolve` call.
"""

from collections import Counter
from typing import TYPE_CHECKING, Any

from fransys_layout.engines.schematic.write.keys import PREFIX
from fransys_model.kernel import make_id
from fransys_model.layout import DrawingSet, Page, PageGroup, PageRole

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.engines.schematic.write.keys import PageId, WriteKeys
    from fransys_layout.stages import PagePlan
    from fransys_model.kernel import AuthoringKey, Id


def drawing_sets(keys: WriteKeys, plans: tuple[PagePlan, ...], stamp: str) -> dict[int, DrawingSet]:
    """One `DrawingSet` per drawing set index, with its plan's unit and location."""
    nodes = keys.aspect_node
    unit_table = keys.unit
    found: dict[int, DrawingSet] = {}
    for plan in plans:
        if plan.drawing_set not in found:
            where = nodes[plan.location] if plan.location is not None else ("unlocated",)
            unit_where = () if plan.unit is None else ("unit", *unit_table[plan.unit])
            key = (*PREFIX, "drawing_set", *unit_where, *where)
            found[plan.drawing_set] = DrawingSet(
                id=make_id(DrawingSet, key),
                key=key,
                unit=plan.unit,
                location=plan.location,
                number=plan.drawing_set,
                produced_by=stamp,
            )
    return found


def pages(
    keys: WriteKeys,
    plans: tuple[PagePlan, ...],
    sets: Mapping[int, DrawingSet],
    sheet_format: Id[Any] | None,
    stamp: str,
) -> dict[PageId, Page]:
    """One `Page` per plan, keyed by `(drawing set, page number)`."""
    nodes = keys.aspect_node
    seen: Counter[tuple[int, AuthoringKey, PageRole]] = Counter()
    found: dict[PageId, Page] = {}
    for plan in sorted(plans, key=lambda plan: (plan.drawing_set, plan.number)):
        first = plan.groups[0].group if plan.groups else None
        where = nodes[first] if first is not None else plan.columns[0].column
        role = PageRole[plan.role.name]
        ordinal = seen[plan.drawing_set, where, role]
        seen[plan.drawing_set, where, role] += 1
        drawing_set = sets[plan.drawing_set]
        key = (*drawing_set.key, *where, role.value, str(ordinal))
        found[plan.drawing_set, plan.number] = Page(
            id=make_id(Page, key),
            key=key,
            drawing_set=drawing_set.id,
            number=plan.number,
            role=role,
            sheet_format=sheet_format,
            groups=tuple(
                PageGroup(group=planned.group, index=planned.index)
                for planned in plan.groups
                if planned.group is not None
            ),
            produced_by=stamp,
        )
    return found
