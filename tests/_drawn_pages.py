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
lazy from fransys_layout.drawing import Drawing, DrawnSymbol

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model

__all__ = ["drawn_pages", "markers_in", "ref_texts"]

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
