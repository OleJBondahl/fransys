"""Open cores' texts and where they land (CC1, CC6; model-0204).

Kept apart from `open_cores` (the rows) so `wiring` can list an open core's end without
importing `reports`.
"""

from fransys_model.kernel import DIGEST_CACHE_SIZE, Id, Model, digest_cached
from fransys_model.vocab.facets.cable import OpenCoreFacet
from fransys_model.vocab.tables import facets_of
lazy from fransys_model.vocab.core import Item, Unit
lazy from fransys_model.vocab.enums import PortRole

from .core_pairs import _product_colours, open_core_is_spare
from .designation import printed_designation
from .facts.roles import port_role
from .indexes import build_indexes
from .texts.core_text import join_words
lazy from .rows_cores import OpenCoreRow


@digest_cached(DIGEST_CACHE_SIZE)
def _open_by_cable(model: Model) -> frozendict[Id[Item], tuple[OpenCoreFacet, ...]]:
    """Every `OpenCoreFacet` grouped by its cable, each cable's by core number."""
    grouped: dict[Id[Item], list[OpenCoreFacet]] = {}
    for facet in facets_of(model, OpenCoreFacet).values():
        grouped.setdefault(facet.subject, []).append(facet)
    return frozendict(
        {cable: tuple(sorted(found, key=lambda f: f.index)) for cable, found in grouped.items()}
    )


def open_core_text(row: OpenCoreRow, mark: str = "") -> str:
    """An open core's text on the cable drawing: index, colour, its pair mark, then `spare`.

    Example: `3 GY spare`, or `5 SH screen P1` for a screen.
    """
    return join_words(str(row.index), row.colour, mark, "spare" if row.spare else "")


def open_ends_at(
    model: Model, terminal: Id[Item], role: PortRole, *, unit: Id[Unit] | None
) -> tuple[str, ...]:
    """The end text of each open core landing on `terminal`'s ports of `role`: `-W1 GY spare`.

    The terminal list appends these after the far ends of its conductors (CC6); they have no
    conductor, so no `TerminalRow.internal` or `external` entry stands beside them.
    """
    idx = build_indexes(model)
    near = {
        port
        for function in idx.functions_by_item.get(terminal, ())
        for port in idx.ports_by_function.get(function, ())
        if port_role(model, port) is role
    }
    found = []
    for cable, facets in sorted(_open_by_cable(model).items()):
        colours = _product_colours(model, cable)
        for facet in facets:
            if facet.at not in near:
                continue
            colour = colours[facet.index - 1] if 1 <= facet.index <= len(colours) else ""
            designation = printed_designation(model, cable, unit=unit)
            found.append(
                join_words(
                    designation,
                    colour,
                    "spare" if open_core_is_spare(model, colour, facet.at) else "",
                )
            )
    return tuple(found)
