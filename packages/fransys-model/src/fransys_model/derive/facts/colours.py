"""The colour facts: each conductor's colour, and the wire and product colours that are no code."""

from fransys_model.derive.facts.cables import cable_product
from fransys_model.derive.facts.cores import core_colour_at, core_colour_list
from fransys_model.elecdef import core_colour
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
from fransys_model.vocab.facets.cable import CableProductFacet, CoreFacet
from fransys_model.vocab.facets.wire import WireFacet
from fransys_model.vocab.tables import conductors, facets_of
lazy from fransys_model.vocab.connectivity import Conductor


def _known(colour: str) -> bool:
    """The empty colour (none recorded) or a code `elecdef` reads."""
    return colour == "" or core_colour(colour) is not None


@digest_cached(DIGEST_CACHE_SIZE)
def _core_colours(model: Model) -> frozendict[Id[Conductor], str]:
    found: dict[Id[Conductor], str] = {}
    for core in facets_of(model, CoreFacet).values():
        carrier = conductors(model)[core.subject].carrier
        product = None if carrier is None else cable_product(model, carrier)
        colour = None if product is None else core_colour_at(product, core.index)
        if colour is not None:
            found[core.subject] = colour
    return frozendict(found)


@digest_cached(DIGEST_CACHE_SIZE)
def coloured_conductors(
    model: Model,
) -> tuple[tuple[Id[Conductor], str, Id[WireFacet] | None], ...]:
    """Each (conductor, colour, wire facet or `None` for a core); a wire-and-core one is twice."""
    wires = [(f.subject, f.colour, f.id) for f in facets_of(model, WireFacet).values()]
    return tuple(wires + [(c, colour, None) for c, colour in _core_colours(model).items()])


def unknown_wire_colours(model: Model) -> tuple[WireFacet, ...]:
    """The wire facets whose colour is no IEC 60757 code; an empty colour is legal."""
    return tuple(f for f in facets_of(model, WireFacet).values() if not _known(f.colour))


def unknown_core_colours(model: Model) -> tuple[tuple[CableProductFacet, int, str], ...]:
    """Each product core colour that is no code, as (product, core index, colour)."""
    return tuple(
        (product, index, colour)
        for product in facets_of(model, CableProductFacet).values()
        for index, colour in core_colour_list(product)
        if not _known(colour)
    )
