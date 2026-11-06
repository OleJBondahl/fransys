"""The conductor facts: a jumper bridges, a jumper or a rail bonds (EL-2 conductors, model-0296).

Both read the conductor's role row. A bridging or bonding conductor is a link, never a wire
(G-POT-20). `conductor_ends` gives a conductor's two ports (model-0340).
"""

from fransys_model.derive.facts.house_settings import export_form_of
from fransys_model.derive.facts.roles import conductor_role
from fransys_model.kernel import DIGEST_CACHE_SIZE, digest_cached
from fransys_model.vocab.tables import conductors
lazy from fransys_model.derive.lookups import item_of_port
lazy from fransys_model.derive.power import is_rail_terminal, port_power_kind
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.connectivity import Conductor
lazy from fransys_model.vocab.core import Port
lazy from fransys_model.vocab.enums import PowerKind


def is_bridge(model: Model, conductor: Id[Conductor]) -> bool:
    """Whether `conductor` bridges two terminals of a strip: a `JUMPER` only."""
    return conductor_role(model, conductor).bridge


def is_pe_conductor(model: Model, conductor: Id[Conductor]) -> bool:
    """Whether an end of `conductor` is a pin of a rail terminal on the PE net: the PE rail's own wire or link.

    The one home of what the hide-PE option leaves off the drawing sheets.
    """
    return any(
        is_rail_terminal(model, item_of_port(model, p)) and port_power_kind(model, p) is PowerKind.PE for p in conductor_ends(model, conductor)
    )


@digest_cached(DIGEST_CACHE_SIZE)
def drawn_conductors(model: Model) -> frozenset[Id[Conductor]]:
    """The conductors a drawing may join: every one but a bridge (the terminal table carries bridges).

    With `[export] hide_pe` a PE conductor is left out too. The one source of what drawing reads; the list sites read `conductors` whole.
    """
    hide = export_form_of(model).hide_pe
    return frozenset(c for c in conductors(model) if not (is_bridge(model, c) or (hide and is_pe_conductor(model, c))))


def conductor_ends(model: Model, conductor: Id[Conductor]) -> tuple[Id[Port], Id[Port]]:
    """The two ports `conductor` joins, as authored: `(a, b)`.

    Layout and the drawing builders read a conductor's ends here and never from the table.
    An id that is no conductor of `model` raises `KeyError`.
    """
    found = conductors(model)[conductor]
    return found.a, found.b
