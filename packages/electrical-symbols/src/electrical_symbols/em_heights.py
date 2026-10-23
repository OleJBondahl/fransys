"""Each capital height a build prints at, as the font size that draws it (es-0089, es-0090)."""

lazy from collections.abc import Iterable, Mapping

from symdef import Library, em_height

__all__ = ["em_heights"]


def em_heights(library: Library, capital_heights_mm: Iterable[float]) -> Mapping[float, float]:
    """The em in mm of each capital height, by `symdef.em_height` of `library`'s font.

    A text is drawn and measured at its em, and the cap-to-em conversion is symdef's font measure.
    The facade asks for every height the build prints at, from the build's own library. An empty
    mapping when the library has no font.
    """
    font = library.font
    if font is None:
        return dict[float, float]()
    return {cap: em_height(font, cap) for cap in capital_heights_mm}
