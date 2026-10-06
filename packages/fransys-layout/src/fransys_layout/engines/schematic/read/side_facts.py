"""The facts V1's side order reads: a function's energy direction and its current kind."""

from typing import TYPE_CHECKING, Any, NamedTuple

from fransys_layout.conventions import FACTS, fact, validate
from fransys_layout.conventions.sides import V1
from fransys_model.derive import gives_energy, takes_energy

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model


class Subject(NamedTuple):
    """A function of a model: what V1's facts are asked about."""

    model: Model
    function: Id[Any]
    currents: tuple[str | None, ...] = ()  # the V11 current of each port of the function


@fact("takes_energy", kind="electrical", source="passive sign convention (IEC 60375)")
def takes(subject: Subject) -> bool:
    """Whether the function takes energy in."""
    return takes_energy(subject.model, subject.function)


@fact("gives_energy", kind="electrical", source="passive sign convention (IEC 60375)")
def gives(subject: Subject) -> bool:
    """Whether the function gives energy out."""
    return gives_energy(subject.model, subject.function)


@fact("power_function", kind="electrical", source="passive sign convention (IEC 60375)")
def power_function(subject: Subject) -> bool:
    """Whether the function takes energy in or gives it out."""
    return bool(FACTS["takes_energy"].func(subject) or FACTS["gives_energy"].func(subject))


@fact(
    "ac_current",
    kind="electrical",
    source="alternating current (IEC 60050-131); the V11 rail current of the function's ports",
)
def is_ac(subject: Subject) -> bool:
    """Whether a port of the function carries AC and none carries DC (V11 `PortSpec.current`)."""
    return "ac" in subject.currents and "dc" not in subject.currents


validate(V1, FACTS)
