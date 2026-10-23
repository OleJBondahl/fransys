"""The conductor facts: a jumper bridges, a jumper or a rail bonds (EL-2 conductors, model-0296).

Both read the conductor's role row. A bridging or bonding conductor is a link, never a wire
(G-POT-20). `conductor_ends` gives a conductor's two ports (model-0340).
"""

from fransys_model.derive.facts.roles import conductor_role
from fransys_model.vocab.tables import conductors
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.connectivity import Conductor
lazy from fransys_model.vocab.core import Port


def is_bridge(model: Model, conductor: Id[Conductor]) -> bool:
    """Whether `conductor` bridges two terminals of a strip: a `JUMPER` only."""
    return conductor_role(model, conductor).bridge


def is_bonded(model: Model, conductor: Id[Conductor]) -> bool:
    """Whether `conductor` bonds two terminals of a strip: a `JUMPER` or a `RAIL` (G-TERM-10)."""
    return conductor_role(model, conductor).rail_link


def conductor_ends(model: Model, conductor: Id[Conductor]) -> tuple[Id[Port], Id[Port]]:
    """The two ports `conductor` joins, as authored: `(a, b)`.

    Layout and the drawing builders read a conductor's ends here and never from the table.
    An id that is no conductor of `model` raises `KeyError`.
    """
    found = conductors(model)[conductor]
    return found.a, found.b
