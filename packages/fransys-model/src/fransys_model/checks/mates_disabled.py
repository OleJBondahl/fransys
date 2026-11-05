"""Validator: a mate and a harness line are refused for 0.22 (R1216, KI row MATES-DISABLED, piece MATES-RETURN)."""

from typing import TYPE_CHECKING, Any, Final

from fransys_model.checks._finding import ordered
from fransys_model.derive.facts.units import marked_harnesses
from fransys_model.vocab.codes import finding
from fransys_model.vocab.finding_ref import ref
from fransys_model.vocab.tables import mates
lazy from fransys_model.kernel import Finding

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model

MATES_DISABLED: Final[str] = "MATES_DISABLED"

_LATER: Final[str] = "remove it, or draw the connection as a cable or wires; mates, boards and harness lines return after 0.22"


def _refuse(subject: Id[Any], what: str) -> Finding:
    return finding(MATES_DISABLED, (subject,), f"{what} is refused in 0.22: {_LATER}")


def check_mates_disabled(model: Model) -> tuple[Finding, ...]:
    """Check there is no mate and no marked harness; `MATES_DISABLED` (`ERROR`).

    One finding per thing. The code paths stay for their return (KI row MATES-DISABLED).
    """
    found = [_refuse(mate.id, f"the mate of {ref(mate.a)} and {ref(mate.b)}") for mate in mates(model).values()]
    found += [_refuse(harness, f"the harness line {ref(harness)}") for harness in marked_harnesses(model)]
    return ordered(found)
