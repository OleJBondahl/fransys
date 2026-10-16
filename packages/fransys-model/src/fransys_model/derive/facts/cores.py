"""The cable-core fact: the one reader of `CableProductFacet.core_colours` and core kinds.

A product lists the colour of each core; a conductor is a core when its role carries but is no
wire. Checks and derives read these functions, never the field (EL-3, model-0288).
"""

from typing import TYPE_CHECKING

from fransys_model.derive.facts.roles import conductor_role

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.connectivity import Conductor
    from fransys_model.vocab.facets.cable import CableProductFacet


def core_count(product: CableProductFacet) -> int:
    """The number of cores `product` lists, a screen included."""
    return len(product.core_colours)


def core_colour_at(product: CableProductFacet, index: int) -> str | None:
    """The colour of core `index` (1-based) of `product`, `None` when it has no such core."""
    if 1 <= index <= len(product.core_colours):
        return product.core_colours[index - 1]
    return None


def core_colour_list(product: CableProductFacet) -> tuple[tuple[int, str], ...]:
    """Each core of `product` as `(index, colour)`, indexes from 1."""
    return tuple(enumerate(product.core_colours, start=1))


def is_core(model: Model, conductor: Id[Conductor]) -> bool:
    """Whether `conductor` is a cable core: its role carries and is not a single wire."""
    role = conductor_role(model, conductor)
    return role.carries and not role.wire
