"""Validator: a terminal function has at most two ports (R1202, KI-463, piece MULTI-PIN-TERMINALS)."""

from collections import Counter
from typing import TYPE_CHECKING, Final

from fransys_model.checks._finding import ordered
from fransys_model.derive.facts.roles import function_role
from fransys_model.vocab.codes import finding
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import functions, items, ports
lazy from fransys_model.kernel import Finding

if TYPE_CHECKING:
    from fransys_model.kernel import Model

TERMINAL_MORE_THAN_TWO_PINS: Final[str] = "TERMINAL_MORE_THAN_TWO_PINS"
_MOST_PINS: Final[int] = 2


def check_terminal_two_pins(model: Model) -> tuple[Finding, ...]:
    """Check no `TERMINAL` function has more than two ports; `TERMINAL_MORE_THAN_TWO_PINS` (`ERROR`).

    Part-less terminals count too. The pass goes when multi-pin terminals return (KI-463).
    """
    count = Counter(port.function for port in ports(model).values())
    return ordered(
        [
            finding(
                TERMINAL_MORE_THAN_TWO_PINS,
                (function.id,),
                f"terminal {function.name!r} of {ref(items(model)[function.item])} has {count[function.id]} ports; "
                "use a two-pin terminal part, multi-pin terminals return later",
            )
            for function in functions(model).values()
            if function_role(model, function.id).terminal and count[function.id] > _MOST_PINS
        ]
    )
