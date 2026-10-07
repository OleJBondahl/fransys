"""The readings of a model: the system, then each unit instance by render id."""

from typing import Any

from fransys_model.kernel.ids import render_id
from fransys_model.vocab.tables import units
lazy from fransys_model.kernel import Id, Model


def readings(model: Model) -> tuple[Id[Any] | None, ...]:
    """`None` for the system, then every unit instance sorted by `render_id`."""
    return (None, *sorted(units(model), key=render_id))
