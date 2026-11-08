"""The page Drawings a built result's core layout drew: one door for the tests (DEL-4 R237).

A test that needs a drawn fact (symbol, wire, text, outline, marker) calls `drawn_pages(model)`.
`fr.build` is wrapped on import to note each result's `drawings` under its model's digest, so a
"""

import functools
from typing import TYPE_CHECKING, Any
lazy from collections.abc import Mapping

import fransys
from fransys import pipeline

from electrical_symbols import MARKER_SLOT, MARKER_TURNED, marker_symbol
lazy from fransys_layout.drawing import Drawing, DrawnSymbol, DrawnText

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model

__all__ = ["drawn_pages", "markers_in", "reads_tag", "ref_texts", "tag_texts"]

RUN_TAG_REACH = 16  # G: a run's tag may stand this far right of the first point of its run (a tag above or below it)

_NOTED: dict[str, Mapping[Id[Any], Drawing]] = {}


def _noting(build):
    @functools.wraps(build)
    def noted(*args, **kwargs):
        result = build(*args, **kwargs)
        _NOTED.pop(result.model.digest, None)
        _NOTED[result.model.digest] = result.drawings
        return result

    return noted


if not getattr(pipeline.build, "__wrapped__", None):
    pipeline.build = fransys.build = _noting(pipeline.build)


def drawn_pages(model: Model) -> Mapping[Id[Any], Drawing]:
    """The page Drawings `fransys.build` made for `model`; LookupError if it never built it."""
    try:
        return _NOTED[model.digest]
    except KeyError:
        msg = "no drawings for this model: only a model `fransys.build` laid out has them"
        raise LookupError(msg) from None


_MARKER_KEYS = frozenset({marker_symbol("tag"), MARKER_TURNED})


def markers_in(drawing: Drawing) -> list[DrawnSymbol]:
    """The reference markers and stubs of a page: its symbols of a marker key (layout-0444)."""
    return [s for s in drawing.symbols if s.key in _MARKER_KEYS]


def ref_texts(marker: DrawnSymbol) -> list[str]:
    """The reference text of a marker symbol: the values of its `ref` slot."""
    return [value for slot, value in marker.slots if slot == MARKER_SLOT]


def _nearest(sym: DrawnSymbol, texts: list[DrawnText]) -> DrawnText | None:
    """The TAG text nearest `sym`'s origin."""
    return min(texts, key=lambda t: abs(sym.x - t.box.x) + abs(sym.y - t.box.y), default=None)


def tag_texts(drawing: Drawing, designation: str) -> list[DrawnText]:
    """The TAG texts that print `designation`: the whole text, or for a strip terminal (`-X1:2`) its point `2` under the run tag `-X1`.

    A point belongs to the run tag nearest it among those that stand left of it (or within `RUN_TAG_REACH` right of it).
    """
    tags = [t for t in drawing.texts if t.kind == "TAG"]
    runs = [t for t in tags if t.owner is None]
    strip, _, point = designation.partition(":")

    def run_of(text: DrawnText) -> DrawnText | None:
        left = [r for r in runs if r.box.x <= text.box.x + RUN_TAG_REACH]
        return min(left, key=lambda r: abs(text.box.x - r.box.x) + abs(text.box.y - r.box.y), default=None)

    return [t for t in tags if t.text == designation] + [
        t for t in tags if point and t.owner and t.text == point and getattr(run_of(t), "text", None) == strip
    ]


def reads_tag(sym: DrawnSymbol, drawing: Drawing, tag: str) -> bool:
    """Whether `sym` prints `tag`: its nearest TAG text reads it, or (a strip terminal `-X1:2`) its own point text stands under the run tag `-X1`."""
    near = _nearest(sym, [t for t in drawing.texts if t.kind == "TAG" and t.text[:2] == tag[:2]])
    return (near is not None and near.text == tag) or any(t.owner == sym.id for t in tag_texts(drawing, tag))
