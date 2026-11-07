"""A drawn symbol with its subject, and the page facts: the tests' reading of a built Drawing.

The core Drawing names no model thing (R467 C1). `symbol_subjects` joins each `DrawnSymbol` to
its function through `fransys_el.drawn_subjects`; `document_facts` gives each drawn page's
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from _drawn_pages import drawn_pages
from fransys_el import symbol_kit
from fransys_el.drawn_subjects import drawn_subjects

from electrical_symbols import GENERIC_BOX_KEY, LIBRARY, box_marking_widths, generic_box
from fransys_layout.geometry import Box as GeoBox
from fransys_layout.symbols import library_symbol, symbol_shape, turned_view
from fransys_model.derive import function_item, item_designation
from fransys_model.layout import Page, layout_of

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.core import Orientation
    from fransys_layout.drawing import DrawnSymbol, DrawnText, DrawnWire
    from fransys_model.kernel import Id, Model

__all__ = [
    "Placed",
    "PlacedText",
    "box_boxes",
    "box_pins",
    "document_facts",
    "item_box",
    "marker_symbols",
    "pin_turn",
    "pin_turns",
    "symbol_boxes",
    "symbol_subjects",
    "text_subjects",
    "wire_nets",
]


@dataclass(frozen=True)
class Placed:
    """A `DrawnSymbol` on a page, with the function and item tag its pick gives.

    Reads fall through to the drawn symbol. `symbol` is its library key, `owner` the value of
    its function's id, `tag` its item's printed designation (`fransys_model.derive`); `offsets`,
    """

    drawn: DrawnSymbol
    page: Id[Any]
    function: Id[Any]
    tag: str
    drawing_set: Id[Any]

    def __getattr__(self, name: str):
        return getattr(self.drawn, name)

    @property
    def symbol(self) -> str:
        return self.drawn.key

    @property
    def owner(self) -> str:
        return self.function.value

    @property
    def offsets(self) -> dict[str, int]:
        return dict(self.drawn.offsets)

    @property
    def sides(self) -> dict[str, str]:
        return dict(self.drawn.sides)

    @property
    def slots(self) -> dict[str, str]:
        return dict(self.drawn.slots)


def document_facts(model: Model) -> Mapping[Id[Any], Page]:
    """Each drawn page's record: its `number` and `drawing_set`; the key is the Drawing's page."""
    pages = layout_of(model, Page)
    return {page: pages[page] for page in drawn_pages(model)}


def _subjects(model: Model) -> dict[str, Id[Any]]:
    """The lead function of each drawn id, for the kit `fransys.build` made (deterministic)."""
    return drawn_subjects(model, symbol_kit(model, LIBRARY))


def symbol_subjects(model: Model) -> list[Placed]:
    """Every drawn symbol of every page that has a subject, in page then drawing order."""
    facts = document_facts(model)
    subjects = _subjects(model)
    found = []
    for page, drawing in drawn_pages(model).items():
        found.extend(
            Placed(
                s,
                page,
                subjects[s.id],
                item_designation(model, function_item(model, subjects[s.id])),
                facts[page].drawing_set,
            )
            for s in drawing.symbols
            if s.id in subjects
        )
    return found


@dataclass(frozen=True)
class PlacedText:
    """A `DrawnText` on a page with the function of the symbol it annotates (`owner`)."""

    drawn: DrawnText
    page: Id[Any]
    function: Id[Any]

    def __getattr__(self, name: str):
        return getattr(self.drawn, name)


def text_subjects(model: Model) -> list[PlacedText]:
    """Every drawn text that annotates a symbol with a subject; a free text is left out."""
    subjects = _subjects(model)
    return [PlacedText(t, page, subjects[t.owner]) for page, d in drawn_pages(model).items() for t in d.texts if t.owner in subjects]


def marker_symbols(model: Model) -> list[Placed]:
    """The reference markers (symbols with a net and a `ref` slot) among `symbol_subjects`."""
    return [p for p in symbol_subjects(model) if p.drawn.net and "ref" in p.slots]


def wire_nets(model: Model) -> list[tuple[Id[Any], DrawnWire]]:
    """Each drawn wire with the page it is on; its `net` is the port value of its net."""
    return [(page, w) for page, d in drawn_pages(model).items() for w in d.wires]


def item_box(model: Model, tag: str) -> Placed:
    """The one generic box drawn for the item whose printed designation is `tag`."""
    boxes = [s for s in symbol_subjects(model) if s.key == GENERIC_BOX_KEY and s.tag == tag]
    assert len(boxes) == 1, f"{tag} draws {len(boxes)} boxes, not one"
    return boxes[0]


def pin_turn(key: str, port: str, *, poles: int = 1, orient: Orientation = "R0"):
    """The offset and side of `port` of symbol `key` repeated `poles` times at `orient`."""
    return turned_view(library_symbol(LIBRARY, key, poles), LIBRARY, orient, (port,)).pins[0]


def _boxes(symbol) -> tuple[GeoBox, GeoBox]:
    view = turned_view(symbol, LIBRARY, "R0")
    body, keepout = (GeoBox(x=b.x, y=b.y, width=b.w, height=b.h) for b in (view.body, view.keepout))
    return body, keepout


def symbol_boxes(key: str, *, poles: int = 1, orient: Orientation = "R0") -> tuple[GeoBox, GeoBox]:
    """The body and the keep-out of symbol `key` repeated `poles` times at `orient`, relative to its origin."""
    view = turned_view(library_symbol(LIBRARY, key, poles), LIBRARY, orient)
    body, keepout = (GeoBox(x=b.x, y=b.y, width=b.w, height=b.h) for b in (view.body, view.keepout))
    return body, keepout


def box_boxes(names: tuple[str, ...], sides: tuple[str, ...] = (), offsets: tuple[float, ...] = ()) -> tuple[GeoBox, GeoBox]:
    """The body and the keep-out of the generic box with ports `names`, relative to its origin."""
    return _boxes(generic_box(names, sides, offsets, 0, marking_widths=box_marking_widths(LIBRARY, names)))


def pin_turns(key: str, *, orient: Orientation = "R0"):
    """Every pin of symbol `key` at `orient`: its offset from the origin and the side it faces."""
    symbol = library_symbol(LIBRARY, key)
    return turned_view(symbol, LIBRARY, orient, tuple(symbol_shape(symbol, LIBRARY).pins)).pins


def box_pins(names: tuple[str, ...]):
    """The pins of the generic box with ports `names`, in that order."""
    symbol = generic_box(names, marking_widths=box_marking_widths(LIBRARY, names))
    return turned_view(symbol, LIBRARY, "R0", names).pins
