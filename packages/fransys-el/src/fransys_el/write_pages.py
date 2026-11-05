"""The `DrawingSet` and `Page` records of a core layout (P6.1 D)."""

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fransys_model.derive import group_role
from fransys_model.kernel import make_id, render_id
from fransys_model.layout import DrawingSet, Page, PageGroup, PageRole, sheet_for
from fransys_model.vocab import PageKind

from .placement_kit import refuse

if TYPE_CHECKING:
    from collections.abc import Mapping

    from electrical_symbols import Library
    from fransys_layout.core import CoreLayout, PagePlan, PlacementProblem
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import AspectNode, Unit

    from .placement_kit import SymbolKit

__all__ = ["STAMP", "SetPlace", "Written", "write_pages"]

STAMP = "fransys-el/write_layout"


@dataclass(frozen=True, slots=True)
class SetPlace:
    """Where a drawing set stands: the location it draws and its number (PAGE-02)."""

    location: Id[AspectNode] | None = None
    number: int = 1


@dataclass(frozen=True, slots=True)
class Written:
    """What the markers, memberships and drawing of one written set read: its pages and owner."""

    model: Model
    layout: CoreLayout
    problem: PlacementProblem
    kit: SymbolKit
    library: Library
    pages: Mapping[int, Page]
    owner: DrawingSet
    within: Id[Unit] | None


def drawing_set(unit: Id[Unit] | None, where: SetPlace) -> DrawingSet:
    """The drawing set of this layout: the unit's (all when `unit` is None) at a location."""
    here = () if where.location is None else (render_id(where.location),)
    key = ("layout", "core", "drawing_set", "all" if unit is None else render_id(unit), *here)
    return DrawingSet(
        id=make_id(DrawingSet, key),
        key=key,
        location=where.location,
        unit=unit,
        number=where.number,
        produced_by=STAMP,
    )


def _groups(plan: PagePlan, texts: Mapping[str, Id[AspectNode]]) -> tuple[PageGroup, ...]:
    found = []
    for index, text in enumerate(plan.groups):
        if text not in texts:
            refuse(f"page {plan.page}, group {text}", "the group is no aspect node label of the model")
        found.append(PageGroup(group=texts[text], index=index))
    return tuple(found)


def _role(model: Model, plan: PagePlan, texts: Mapping[str, Id[AspectNode]]) -> PageRole:
    """The role of the page's first group (layout-0048); a page with no group is CONTROL."""
    if not plan.groups:
        return PageRole.CONTROL
    return group_role(model, texts[plan.groups[0]])


def write_pages(
    model: Model,
    plans: tuple[PagePlan, ...],
    unit: Id[Unit] | None,
    texts: Mapping[str, Id[AspectNode]],
    where: SetPlace | None = None,
) -> tuple[tuple[DrawingSet, ...], dict[int, Page]]:
    """The set and each page by its number; keys hold no page number."""
    owner = drawing_set(unit, where or SetPlace())
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
            sheet_format=sheet_for(model, PageKind.SCHEMATIC).id,
            groups=groups,
            produced_by=STAMP,
        )
        pages[plan.page] = page
    return (owner,), pages
