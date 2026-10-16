"""Twisted pairs of a cable product and the texts they print (CC10, CC11, model-0204).

The pair label (`P1`), the mark on a core's row, the heading's pair form and the cable list's
Cores cell each have one function here; layout, render and the lists call them.
"""

from fransys_model.derive.facts.potentials import on_pe_net
from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached, value
from fransys_model.vocab.facets.cable import CableProductFacet
from fransys_model.vocab.tables import facets_of, items
lazy from fransys_model.vocab.core import Item, Port
lazy from fransys_model.vocab.facets.cable import CorePair
lazy from fransys_model.vocab.templates import Part

SCREEN = "SH"


@digest_cached(DIGEST_CACHE_SIZE)
def _cable_products_by_part(model: Model) -> frozendict[Id[Part], CableProductFacet]:
    """Every `CableProductFacet` by the part it describes, built once per model digest.

    The facet's `unique=True` allows at most one per part, so no first-match tie-break is needed.
    """
    return frozendict(
        {facet.subject: facet for facet in facets_of(model, CableProductFacet).values()}
    )


def _product_colours(model: Model, cable: Id[Item]) -> tuple[str, ...]:
    """The `core_colours` of `cable`'s part's `cable_product`, `()` when it has none.

    Reads `_cable_products_by_part`, an `Id[Part]`-keyed index built once per model digest.
    """
    part = items(model)[cable].part
    if part is None:
        return ()
    facet = _cable_products_by_part(model).get(part)
    return () if facet is None else facet.core_colours


def open_core_is_spare(model: Model, colour: str, at: Id[Port] | None) -> bool:
    """Whether an open core of `colour` landing at `at` is a spare: not a screen, not earthed.

    A core landing on a port of the PE net is a protective core earthed at that port. The author
    joins a PE-role port to the PE net (author-0044), so a PE-role port off it is not earthed.
    """
    return colour != SCREEN and not (at is not None and on_pe_net(model, at))


@value
class DrawnPair:
    """One pair as the cable drawing draws it: its label, its cores, its screen, its bracket.

    `bracket` is true when the two cores are neighbours (their numbers differ by one), so a
    bracket joins their rows; otherwise each row prints the label.
    """

    label: str
    cores: tuple[int, ...]
    screen: int | None
    bracket: bool


def cable_pairs(model: Model, cable: Id[Item]) -> tuple[CorePair, ...]:
    """The pairs of `cable`'s product, `()` when it has none or no part."""
    part = items(model)[cable].part
    facet = None if part is None else _cable_products_by_part(model).get(part)
    return () if facet is None else facet.pairs


def drawn_pairs(model: Model, cable: Id[Item]) -> tuple[DrawnPair, ...]:
    """`cable`'s pairs in pair order, labelled `P1`, `P2`, ..."""
    return tuple(
        DrawnPair(
            label=f"P{n}",
            cores=pair.cores,
            screen=pair.screen,
            bracket=abs(pair.cores[0] - pair.cores[1]) == 1,
        )
        for n, pair in enumerate(cable_pairs(model, cable), 1)
    )


def core_pair_word(pairs: tuple[DrawnPair, ...], index: int) -> str:
    """The pair word of core `index` in a list: `P1`, `screen P1`, or `""` outside a pair."""
    for pair in pairs:
        if pair.screen == index:
            return f"screen {pair.label}"
        if index in pair.cores:
            return pair.label
    return ""


def core_mark(pairs: tuple[DrawnPair, ...], index: int) -> str:
    """The pair word on core `index`'s row: `P1` off a bracket, `screen P1` on a screen, or `""`."""
    bracketed = any(pair.bracket and index in pair.cores for pair in pairs)
    return "" if bracketed else core_pair_word(pairs, index)


def conductor_count(colours: tuple[str, ...]) -> int:
    """The conductor cores among a product's `core_colours`: a screen (`SH`) is not a core."""
    return sum(colour != SCREEN for colour in colours)


def pair_form(pairs: tuple[CorePair, ...], gauge_mm2: object) -> str:
    """The heading's pair form, `2x2x0.75` for two pairs of 0.75 mm2; `""` with no pairs."""
    return f"{len(pairs)}x2x{gauge_mm2}" if pairs else ""


def screened_pairs(pairs: tuple[CorePair, ...]) -> bool:
    """Whether the product has pairs and every one has a screen."""
    return bool(pairs) and all(pair.screen is not None for pair in pairs)


def cores_text(core_count: int | None, pairs: int | None) -> str:
    """The cable list's Cores cell: `2x2` for a paired product, the count otherwise."""
    if core_count is None:
        return ""
    return f"{pairs}x2" if pairs else str(core_count)
