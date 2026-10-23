"""The page Drawings a built result's core layout drew: one door for the tests (DEL-4 R237).

A test that needs a drawn fact (symbol, wire, text, outline, marker) calls `drawn_pages(model)`.
`fr.build` is wrapped on import to note each result's `drawings` under its model's digest, so a
helper that holds only the model still finds them. When a public `fr` call takes a result
(FRAMES p4c) the callers pass the result and this memo goes.
"""

import functools
from typing import TYPE_CHECKING
lazy from collections.abc import Mapping

import fransys
from fransys import pipeline

lazy from fransys_layout.drawing import Drawing

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model

__all__ = ["drawn_pages"]

_NOTED: dict[str, Mapping[Id, Drawing]] = {}


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


def drawn_pages(model: Model) -> Mapping[Id, Drawing]:
    """The page Drawings `fransys.build` made for `model`; LookupError if it never built it."""
    try:
        return _NOTED[model.digest]
    except KeyError:
        msg = "no drawings for this model: only a model `fransys.build` laid out has them"
        raise LookupError(msg) from None
