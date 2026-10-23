"""More readings of the core path's page Drawings for the dd_* tests (DEL-4 lane C1, fork B).

The Drawing carries no kind of marker (pair or stub), no port and no owner (R243), so a marker is
told by the text it prints and a drawn item by the tag text beside it.
"""

from typing import TYPE_CHECKING

from _dd_core import designation_of
from _drawn_facts import symbol_subjects
from _drawn_pages import drawn_pages

if TYPE_CHECKING:
    from fransys_layout.drawing import DrawnMarker, DrawnSymbol, DrawnText
    from fransys_model.kernel import Id, Model

__all__ = ["is_stub", "marker_strings", "markers", "tags_of"]

_ARROWS = ("\N{LEFTWARDS ARROW}", "\N{RIGHTWARDS ARROW}")


def markers(model: Model) -> list[tuple[Id, DrawnMarker]]:
    """Every (page, marker) of every page, in drawn order."""
    return [(page, m) for page, drawing in drawn_pages(model).items() for m in drawing.markers]


def marker_strings(marker: DrawnMarker) -> list[str]:
    """The texts of `marker`, in slot order."""
    return [value for _, value in marker.texts]


def is_stub(marker: DrawnMarker) -> bool:
    """Whether the marker prints an off stub's arrow text (`-W3 <- +EXT-K1`)."""
    return any(arrow in text for text in marker_strings(marker) for arrow in _ARROWS)


def tags_of(model: Model, name: str) -> list[tuple[Id, DrawnText]]:
    """(page, tag text) of every tag text printed for the item whose key ends in `name`."""
    des = designation_of(model, name)
    return [
        (page, text)
        for page, drawing in drawn_pages(model).items()
        for text in drawing.texts
        if text.kind == "TAG" and text.text.lstrip("-").split(":")[0] == des
    ]


def symbols_of(model: Model, name: str) -> list[tuple[Id, DrawnSymbol]]:
    """(page, symbol) of every symbol drawn for the item `name`, by (page, x, y).

    A symbol belongs to the item when its subject's item prints the designation of `name`.
    """
    des = designation_of(model, name)
    found = [(p.page, p.drawn) for p in symbol_subjects(model) if p.tag == des]
    return sorted(found, key=lambda f: (f[0].value, f[1].x, f[1].y))
