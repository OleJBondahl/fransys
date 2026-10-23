"""A drawn symbol with its subject, and the page facts: the tests' reading of a built Drawing.

The core Drawing names no model thing (R467 C1). `symbol_subjects` joins each `DrawnSymbol` to
its function through `fransys_el.drawn_subjects`; `document_facts` gives each drawn page's
record (number, drawing set); `wire_nets` and `marker_symbols` give a wire's and a marker's net
as the port value its `net` string names. One home: the field cases copy none of this.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from _drawn_pages import drawn_pages
from fransys_el import drawn_subjects, symbol_kit

from electrical_symbols import LIBRARY
from fransys_layout.geometry import GENERIC_BOX_KEY
from fransys_model.derive import function_item, item_designation
from fransys_model.layout import Page, layout_of

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_layout.drawing import DrawnSymbol, DrawnText, DrawnWire
    from fransys_model.kernel import Id, Model

__all__ = [
    "Placed",
    "PlacedText",
    "document_facts",
    "item_box",
    "marker_symbols",
    "symbol_subjects",
    "text_subjects",
    "wire_nets",
]


@dataclass(frozen=True)
class Placed:
    """A `DrawnSymbol` on a page, with the function and item tag its pick gives.

    Reads fall through to the drawn symbol. `symbol` is its library key, `owner` the value of
    its function's id, `tag` its item's printed designation (`fransys_model.derive`); `offsets`,
    `sides` and `slots` are dicts.
    """

    drawn: DrawnSymbol
    page: Id
    function: Id
    tag: str
    drawing_set: Id

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


def document_facts(model: Model) -> Mapping[Id, Page]:
    """Each drawn page's record: its `number` and `drawing_set`; the key is the Drawing's page."""
    pages = layout_of(model, Page)
    return {page: pages[page] for page in drawn_pages(model)}


def _subjects(model: Model) -> dict[str, Id]:
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
    page: Id
    function: Id

    def __getattr__(self, name: str):
        return getattr(self.drawn, name)


def text_subjects(model: Model) -> list[PlacedText]:
    """Every drawn text that annotates a symbol with a subject; a free text is left out."""
    subjects = _subjects(model)
    return [
        PlacedText(t, page, subjects[t.owner])
        for page, d in drawn_pages(model).items()
        for t in d.texts
        if t.owner in subjects
    ]


def marker_symbols(model: Model) -> list[Placed]:
    """The reference markers (symbols with a net and a `ref` slot) among `symbol_subjects`."""
    return [p for p in symbol_subjects(model) if p.drawn.net and "ref" in p.slots]


def wire_nets(model: Model) -> list[tuple[Id, DrawnWire]]:
    """Each drawn wire with the page it is on; its `net` is the port value of its net."""
    return [(page, w) for page, d in drawn_pages(model).items() for w in d.wires]


def item_box(model: Model, tag: str) -> Placed:
    """The one generic box drawn for the item whose printed designation is `tag`."""
    boxes = [s for s in symbol_subjects(model) if s.key == GENERIC_BOX_KEY and s.tag == tag]
    assert len(boxes) == 1, f"{tag} draws {len(boxes)} boxes, not one"
    return boxes[0]
