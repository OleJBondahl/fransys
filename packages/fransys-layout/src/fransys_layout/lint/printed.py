"""Which pages a look finding may name: only those of a drawing set some document prints.

`printed` is the numbers of the printed sets, or `None` for every set (decision model-0201).
The geometric codes below are the readability findings; `PAGE_UNDERFILLED` and `LONE_CELL` are
look findings in full. Every other finding stays as it is.
"""

from .codes import TEXT_OVERLAP, WIRE_OVER_LABEL

__all__ = ("LOOK_GEOMETRY", "on_printed")

LOOK_GEOMETRY = frozenset({WIRE_OVER_LABEL, TEXT_OVERLAP})


def on_printed(here: tuple[int, int], printed: frozenset[int] | None) -> bool:
    """Whether the page `here` (`(drawing set, page)`) is in a printed set."""
    return printed is None or here[0] in printed
