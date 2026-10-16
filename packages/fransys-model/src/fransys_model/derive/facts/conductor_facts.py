"""The conductor facts: a jumper bridges, a jumper or a rail bonds (EL-2 conductors, model-0296).

Both read the conductor's role row. A bridging or bonding conductor is a link, never a wire
(G-POT-20).
"""

from fransys_model.derive.facts.roles import conductor_role
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.connectivity import Conductor


def is_bridge(model: Model, conductor: Id[Conductor]) -> bool:
    """Whether `conductor` bridges two terminals of a strip: a `JUMPER` only."""
    return conductor_role(model, conductor).bridge


def is_bonded(model: Model, conductor: Id[Conductor]) -> bool:
    """Whether `conductor` bonds two terminals of a strip: a `JUMPER` or a `RAIL` (G-TERM-10)."""
    return conductor_role(model, conductor).rail_link
