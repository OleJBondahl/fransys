"""Validator: a mate inside one drawing, a harness line and a connected cable screen are refused for now (R1216, R1799, R2223)."""

from typing import TYPE_CHECKING, Any, Final

from fransys_model.checks._finding import ordered
from fransys_model.derive.facts.cables import connected_screens
from fransys_model.derive.facts.held_mates import held_mates
from fransys_model.derive.facts.units import marked_harnesses
from fransys_model.vocab.codes import finding
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import items
lazy from fransys_model.kernel import Finding

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model

MATES_DISABLED: Final[str] = "MATES_DISABLED"
SCREEN_DISABLED: Final[str] = "SCREEN_DISABLED"

_LATER: Final[str] = "remove it, or draw the connection as a cable or wires; mates, boards and harness lines return after 0.22"
_SCREEN_LATER: Final[str] = "remove the screen core(...) call: the cable still prints as shielded; screen connections return later"


def _refuse(subject: Id[Any], what: str) -> Finding:
    return finding(MATES_DISABLED, (subject,), f"{what} is refused in 0.22: {_LATER}")


def _connected_screens(model: Model) -> list[Finding]:
    """One `SCREEN_DISABLED` per open core that lands on a pin where the product's colour is the screen."""
    return [
        finding(
            SCREEN_DISABLED,
            (facet.id,),
            f"core {facet.index} (screen) of {ref(items(model)[facet.subject])} is connected, which is refused: {_SCREEN_LATER}",
        )
        for facet in connected_screens(model)
    ]


def check_mates_disabled(model: Model) -> tuple[Finding, ...]:
    """Check there is no mate inside one drawing, no marked harness and no connected screen; `MATES_DISABLED`, `SCREEN_DISABLED` (`ERROR`).

    A mate between two drawing sets returns (R2223); a mate inside one, or a function on two mates, stays refused. One finding per thing.
    """
    found = [
        _refuse(mate.id, f"the mate of {ref(mate.a)} and {ref(mate.b)}, inside one drawing or on a function that holds two mates,")
        for mate in held_mates(model)
    ]
    found += [_refuse(harness, f"the harness line {ref(harness)}") for harness in marked_harnesses(model)]
    return ordered(found + _connected_screens(model))
