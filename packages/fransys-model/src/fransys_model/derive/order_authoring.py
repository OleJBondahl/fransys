"""The authoring-key order of functions: a leaf, so `facts.unit_index` reads it without an import cycle."""

lazy from collections.abc import Iterable

from fransys_model.vocab.tables import HasTables, functions
lazy from fransys_model.kernel import Id
lazy from fransys_model.vocab.core import Function

__all__ = ["functions_by_authoring_key"]


def functions_by_authoring_key(model: HasTables, keys: Iterable[Id[Function]]) -> tuple[Id[Function], ...]:
    """Functions by authoring key: the order for a reader that runs before the numbering pass, when no designation prints (a draft view)."""
    return tuple(sorted(keys, key=lambda function: functions(model)[function].key))
