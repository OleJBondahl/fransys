"""Row shapes of `derive.series_parallel`: a series and a parallel of symbols (SP2)."""

from fransys_model.kernel import value

__all__ = ["ParallelRow", "SeriesParallel", "SeriesRow", "SeriesRowPart"]


@value
class SeriesRow:
    """Parts in signal direction, source first; a part is a symbol key, a series or a parallel."""

    parts: tuple[SeriesRowPart, ...]


@value
class ParallelRow:
    """Parts side by side, joined at both ends, in `derive.order.series_part_key` order."""

    parts: tuple[SeriesRowPart, ...]


type SeriesRowPart = str | SeriesRow | ParallelRow


@value
class SeriesParallel:
    """One series per region of two symbols or more, and the symbols of each region that is no tree.

    A region that does not reduce (a bridge) has no series; `bridges` lists its symbols.
    """

    regions: tuple[SeriesRow, ...]
    bridges: tuple[tuple[str, ...], ...]
