"""The readings of a model: the system, then each unit instance by natural designation."""

from functools import partial
from typing import Any

from fransys_model.derive.order import unit_designation_key
from fransys_model.kernel import render_id
from fransys_model.vocab.tables import units
lazy from fransys_model.kernel import Id, Model


def _sheet_key(model: Model, unit: Id[Any]) -> tuple[tuple[Any, ...], str]:
    """A unit sheet's place: its natural designation, then `render_id` for a tie."""
    return unit_designation_key(model, unit), render_id(unit)


def readings(model: Model) -> tuple[Id[Any] | None, ...]:
    """`None` for the system, then every unit instance by natural designation."""
    return (None, *sorted(units(model), key=partial(_sheet_key, model)))
