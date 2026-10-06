"""The one reader of a unit's release facts (schema spec SC2, decision model-0087)."""

from fransys_model.vocab.tables import unit_releases, units
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Unit, UnitRelease

from .lookups import require


def unit_release(model: Model, unit: Id[Unit]) -> UnitRelease:
    """The `UnitRelease` record `unit` is an instance of, the one reader of its release facts.

    Raises:
        SchemaError: `unit` names no `Unit` of `model`.
    """
    record = require(units(model).get(unit), "unit", unit)
    return unit_releases(model)[record.release]
