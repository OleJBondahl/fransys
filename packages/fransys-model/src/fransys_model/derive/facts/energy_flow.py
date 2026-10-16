"""Which way energy flows through a function's pins (decisions model-0131, model-0133)."""

from fransys_model.derive.facts.roles import function_role
from fransys_model.vocab.enums import Energy
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Function


def takes_energy(model: Model, function: Id[Function]) -> bool:
    """Whether `function` takes energy in: its role's `energy` (a load, actuator, coil or `in`).

    An energy-in function (a load, a motor, a coil, or a supply declared `energy = in`) sits above
    an energy-out one.
    """
    return function_role(model, function).energy is Energy.IN


def gives_energy(model: Model, function: Id[Function]) -> bool:
    """Whether `function` gives energy out: its role's `energy` (a supply, or `energy = out`).

    A power function takes energy in or gives it out.
    """
    return function_role(model, function).energy is Energy.OUT
