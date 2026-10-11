"""Each drawing set's location path and unit path, read from the planned pages."""

from typing import TYPE_CHECKING, Any

from fransys_model.kernel import parent_chain
from fransys_model.vocab.tables import units

from . import reading

if TYPE_CHECKING:
    from fransys_layout.stages.types import PagePlan
    from fransys_model.kernel import Model


def location_paths(model: Model, plans: tuple[PagePlan, ...]) -> dict[int, tuple[Any, ...]]:
    """Each drawing set's location path, of every plan with a location."""
    return {
        plan.drawing_set: reading.location_path(model, plan.location)
        for plan in plans
        if plan.location is not None
    }


def unit_paths(model: Model, plans: tuple[PagePlan, ...]) -> dict[int, tuple[Any, ...]]:
    """Each drawing set's unit path, root first: `()` for the top, then its unit's ancestors."""
    table = units(model)
    return {
        plan.drawing_set: tuple(reversed(list(parent_chain(lambda u: table[u].parent, plan.unit))))
        for plan in plans
    }
