"""T5: the band key of a cell, by its row in the column: first, last, middle, a single row."""

import pytest

from fransys_layout.stages._bands import band_of

RANKS = frozendict({"relay": 1, "relay.first": 0, "relay.last": 2, "plain": 3, "lone.last": 4})


@pytest.mark.parametrize(
    ("kind", "index", "of", "band"),
    [
        ("relay", 0, 3, "relay.first"),
        ("relay", 2, 3, "relay.last"),
        ("relay", 1, 3, "relay"),
        ("relay", 0, 1, "relay.first"),
        ("plain", 0, 3, "plain"),
        ("plain", 2, 3, "plain"),
        ("lone", 1, 2, "lone.last"),
        ("lone", 0, 1, None),
        ("none", 1, 3, None),
    ],
)
def test_the_band_key_follows_the_row_of_the_cell(
    kind: str, index: int, of: int, band: str | None
) -> None:
    """T5.1 first, T5.2 last, T5.3 neither; one row is first; a missing rank falls back."""
    assert band_of(kind, RANKS, index=index, of=of) == band
