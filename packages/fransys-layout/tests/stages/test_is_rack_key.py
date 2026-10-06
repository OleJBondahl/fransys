"""`is_rack_key`: the one test of whether a column key stands in a rack (F1)."""

import pytest

from fransys_layout.stages.columns import is_rack_key


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        (("rack", "a"), True),
        (("rack",), True),
        (("a", "rack"), False),
        ((), False),
        (None, False),
    ],
)
def test_only_a_key_whose_first_segment_is_rack_is_a_rack_key(
    key: tuple[str, ...] | None, *, expected: bool
) -> None:
    # UNDO: stages/columns.py:is_rack_key, return `False`
    assert is_rack_key(key) is expected
