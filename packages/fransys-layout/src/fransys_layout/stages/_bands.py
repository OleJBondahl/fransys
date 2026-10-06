"""Band keys (T5): where a cell stands in its column, and the band key that follows."""

from fransys_layout.conventions import FACTS, fact, first_match, validate
from fransys_layout.conventions.order import BANDS


@fact("first_in_row", kind="drawing")
def _first_in_row(place: tuple[int, int]) -> bool:
    """The cell is in the first row of its column; `place` is (row index, row count)."""
    return place[0] == 0


@fact("last_in_row", kind="drawing")
def _last_in_row(place: tuple[int, int]) -> bool:
    """The cell is in the last row of its column; `place` is (row index, row count)."""
    return place[0] == place[1] - 1


validate(BANDS, FACTS)


def band_of(kind: str, ranks: frozendict[str, int], *, index: int, of: int) -> str | None:
    """The band key of a cell of `kind` at row `index` of `of` rows, or `None`."""
    # a one-row column is first and last: the table's row order gives it `.first`
    row = first_match(BANDS, (index, of), FACTS)
    keyed = kind + str(row.then if row else "")
    return keyed if keyed in ranks else kind if kind in ranks else None
