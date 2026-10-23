"""`ParallelRow.parts` keeps the natural order across the swap to `refdef.natural_key`.

LIB-ADOPT K1 reorders no circuit structure: the parts of a parallel stay in `series_part_key`
order (TAG O4, as amended by the owner 2026-10-23: the first branch is the first in that order).
The expected order is the hand corpus of the kernel's `natural_orders.json` (old key).
"""

import json
from pathlib import Path

from fransys_model.derive.rows_series_parallel import ParallelRow
from fransys_model.derive.series_parallel_reduce import SINK, SOURCE, reduce_region

_FIXTURE = Path(__file__).resolve().parents[3] / "fransys-kernel/tests/fixtures/natural_orders.json"
_KNOWN_DIFFERENCE = {"A٣"}  # non-ASCII decimal digit: refdef reads it as text (ruling N1)


def test_parallel_parts_of_the_hand_corpus_keep_the_recorded_order() -> None:
    data = json.loads(_FIXTURE.read_text("utf-8"))
    hand = {t for t in data["hand"] if t not in _KNOWN_DIFFERENCE}
    expected = tuple(t for t in data["sorted"] if t in hand)
    arrival = list(reversed(expected))  # X1 arrives before X01: only the raw-text tie orders them
    merged = reduce_region([(SOURCE, SINK, t) for t in arrival])
    assert isinstance(merged, ParallelRow)
    assert merged.parts == expected
    assert len(expected) == len(hand) == 13
