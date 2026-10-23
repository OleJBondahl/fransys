"""The `DrawingSet` and `Page` records of a core layout (P6.1 D)."""

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fransys_model.derive import group_role
from fransys_model.kernel import make_id, render_id
from fransys_model.layout import DrawingSet, Page, PageGroup, PageRole

from .placement_kit import refuse

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.core import PagePlan
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import AspectNode, Unit

__all__ = ["SetPlace", "write_pages"]


@dataclass(frozen=True, slots=True)
class SetPlace:
    """Where a drawing set stands: the location it draws and its number (PAGE-02)."""

    location: Id[AspectNode] | None = None
    number: int = 1


def drawing_set(unit: Id[Unit] | None, stamp: str, where: SetPlace) -> DrawingSet:
    """The drawing set of this layout: the unit's (all when `unit` is None) at a location."""
    here = () if where.location is None else (render_id(where.location),)
    key = ("layout", "core", "drawing_set", "all" if unit is None else render_id(unit), *here)
    return DrawingSet(
        id=make_id(DrawingSet, key),
        key=key,
        location=where.location,
        unit=unit,
        number=where.number,
        produced_by=stamp,
    )


def _groups(plan: PagePlan, texts: Mapping[str, Id[object]]) -> tuple[PageGroup, ...]:
    found = []
    for index, text in enumerate(plan.groups):
        if text not in texts:
            refuse(
                f"page {plan.page}, group {text}", "the group is no aspect node label of the model"
            )
        found.append(PageGroup(group=texts[text], index=index))  # ty: ignore[invalid-argument-type] - the text names an aspect node
    return tuple(found)


def _role(model: Model, plan: PagePlan, texts: Mapping[str, Id[object]]) -> PageRole:
    """The role of the page's first group (layout-0048); a page with no group is CONTROL."""
    if not plan.groups:
        return PageRole.CONTROL
    return group_role(model, texts[plan.groups[0]])  # ty: ignore[invalid-argument-type] - the text names an aspect node


def write_pages(  # noqa: PLR0913, PLR0917 - the set's unit and place join the page plan's four
    model: Model,
    plans: tuple[PagePlan, ...],
    unit: Id[Unit] | None,
    texts: Mapping[str, Id[object]],
    stamp: str,
    where: SetPlace | None = None,
) -> tuple[tuple[DrawingSet, ...], dict[int, Page]]:
    """The set and each page by its number; keys hold no page number."""
    owner = drawing_set(unit, stamp, where or SetPlace())
    seen: Counter[str] = Counter()
    pages: dict[int, Page] = {}
    for plan in plans:
        first = plan.groups[0] if plan.groups else "ungrouped"
        key = (*owner.key, "page", first, str(seen[first]))
        seen[first] += 1
        groups = _groups(plan, texts)
        role = _role(model, plan, texts)
        page = Page(
            id=make_id(Page, key),
            key=key,
            drawing_set=owner.id,
            number=plan.page,
            role=role,
            sheet_format=None,
            groups=groups,
            produced_by=stamp,
        )
        pages[plan.page] = page
    return (owner,), pages
