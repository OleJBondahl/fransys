"""Which way energy flows through a function's pins (decisions model-0131, model-0133)."""

lazy from fransys_model.kernel import Id, Model

from .enums import Energy, FunctionKind
from .tables import function_templates, functions
lazy from .core import Function


def _declared(model: Model, function: Id[Function]) -> tuple[Energy | None, FunctionKind]:
    record = functions(model)[function]
    template = None if record.template is None else function_templates(model)[record.template]
    return (None if template is None else template.energy), record.kind


def takes_energy(model: Model, function: Id[Function]) -> bool:
    """Whether `function` takes energy in: its template's `energy`, else `kind = load`.

    An energy-in function (a load, or a supply declared `energy = in`) sits above an energy-out one.
    """
    energy, kind = _declared(model, function)
    return kind is FunctionKind.LOAD if energy is None else energy is Energy.IN


def gives_energy(model: Model, function: Id[Function]) -> bool:
    """Whether `function` gives energy out: its template's `energy`, else `kind = supply`.

    A power function takes energy in or gives it out.
    """
    energy, kind = _declared(model, function)
    return kind is FunctionKind.SUPPLY if energy is None else energy is Energy.OUT
