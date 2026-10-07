"""Each drawing set's location path (U7), read from the planned pages."""

from typing import TYPE_CHECKING, Any

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
