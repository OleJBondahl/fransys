"""The page `Drawing`s of a built model, read from `fr.build`'s result (FLIP-NOW F7, R228, R265).

One place for every test that inspects what `fr.build` drew: it replaces the record reader
`fransys_el` once had (deleted with R228).
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys import BuildResult

    from fransys_layout.drawing import Drawing
    from fransys_model.kernel import Id
    from fransys_model.layout import Page


def page_drawings(result: BuildResult) -> Mapping[Id[Page], Drawing]:
    """The `Drawing` per page that `fr.build` laid out, as `result.drawings` holds them."""
    return result.drawings
