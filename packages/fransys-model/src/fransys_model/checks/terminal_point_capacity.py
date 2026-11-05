"""Validator: a terminal point takes at most the conductors its part states (R1266, KI-482 sibling of terminal_two_pins)."""

from typing import TYPE_CHECKING, Final

from fransys_model.checks._finding import ordered
from fransys_model.derive.facts.roles import function_role
from fransys_model.derive.facts.terminal_points import conductors_per_point, point_conductors
from fransys_model.vocab.codes import finding
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import functions, items, ports
lazy from fransys_model.kernel import Finding

if TYPE_CHECKING:
    from fransys_model.kernel import Model

TERMINAL_POINT_OVERFILLED: Final[str] = "TERMINAL_POINT_OVERFILLED"


def check_terminal_point_capacity(model: Model) -> tuple[Finding, ...]:
    """Check no terminal point has more wires and cable cores than its part states; `TERMINAL_POINT_OVERFILLED` (`ERROR`).

    A bridge counts none. A part-less terminal takes one per point.
    """
    landed = point_conductors(model)
    return ordered(
        [
            finding(
                TERMINAL_POINT_OVERFILLED,
                (port.id,),
                f"terminal point {port.name!r} of {ref(items(model)[function.item])} has {landed[port.id]} conductors "
                f"but its part takes {conductors_per_point(model, function.id)}; "
                "use a part that states more conductors_per_clamp (DEMO-TB-2.5-TWIN takes 2), or bridge a second terminal to this one",
            )
            for port in ports(model).values()
            if landed.get(port.id, 0) > conductors_per_point(model, port.function) and function_role(model, port.function).terminal
            for function in [functions(model)[port.function]]
        ]
    )
