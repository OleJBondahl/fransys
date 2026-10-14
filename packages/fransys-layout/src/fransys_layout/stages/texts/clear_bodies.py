"""layout-0093: a page's markers placed clear of foreign symbols, box and stub."""

from dataclasses import replace
from typing import TYPE_CHECKING

from fransys_layout.geometry import Box, port_page_at, translate
from fransys_layout.stages.space import Shape, Space
from fransys_layout.stages.stub_runs import functions_through, solids

from .place_texts import place_texts

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from fransys_layout.stages import LinkMarker, PlacedFunction
    from fransys_model.kernel import Finding

    from .candidates import TextTable
    from .place_texts import Place, PlacedText, TextToPlace


def _stub_clear(
    texts: tuple[TextToPlace, ...],
    rows: Mapping[int, Sequence[tuple[LinkMarker, Place]]],
    here: Sequence[PlacedFunction],
) -> tuple[TextToPlace, ...]:
    """`texts` with each place refused whose marker's stub runs through a foreign function."""
    bodies = {one.function: translate(one.geometry.body, dx=one.at.x, dy=one.at.y) for one in here}
    ports = {
        one.function: tuple(port_page_at(one.at, g) for g in one.geometry.ports) for one in here
    }
    page = solids(bodies, ports)
    return tuple(
        replace(
            text,
            places=tuple(
                replace(place, fits=False) if functions_through(marker, page) else place
                for marker, place in rows[int(text.slot)]
            ),
        )
        for text in texts
    )


def place_clear_of_bodies(
    texts: tuple[TextToPlace, ...],
    rows: Mapping[int, Sequence[tuple[LinkMarker, Place]]],
    here: Sequence[PlacedFunction],
    ground: Space,
    table: TextTable,
) -> tuple[tuple[PlacedText, ...], tuple[Finding, ...]]:
    """The page's texts clear of foreign symbols, never stranding a marker.

    `ground` holds the page's other ink as shapes and the content box the texts stay in.
    """
    # the lint's `_foreign` counts a port on the body's side edge as the body: grown by one in x
    bodies = tuple(
        Shape(
            owner=one.function, box=_grown(translate(one.geometry.body, dx=one.at.x, dy=one.at.y))
        )
        for one in here
    )
    space = Space(shapes=(*bodies, *ground.shapes), content=ground.content)
    done, findings = place_texts(_stub_clear(texts, rows, here), space, table)
    if findings:
        return place_texts(texts, ground, table)
    return done, findings


def _grown(box: Box) -> Box:
    """`box` one unit wider on each side: an E or W port stands on the body's side edge."""
    return Box(x=box.x - 1, y=box.y, width=box.width + 2, height=box.height)
