"""Row shape of `derive.series_pairs`: one pole's wired north and south pins (design 2.1)."""

from fransys_model.kernel import Id, value
from fransys_model.vocab.core import Port

__all__ = ["SeriesPair"]


@value
class SeriesPair:
    """Pole `pole` (0-based) of a function, with its one wired N pin `north` and S pin `south`."""

    pole: int
    north: Id[Port]
    south: Id[Port]
