"""`fn.pole(n)` names a function that has no poles, at the series line."""

import pytest
from fransys_author import AuthorError
from fransys_author.surface import design

from ..equivalence.series_parts import series_library  # noqa: TID252 -- importlib mode puts tests/ on no path


def test_a_function_without_poles_is_named() -> None:
    d = design(series_library(), place="C1")
    q1, k2 = d.device("Q1", "TEST-MCB-3P"), d.device("K2", "TEST-COIL")
    with pytest.raises(AuthorError, match=r"K2\.coil has no poles: .*`side`"):
        d.series(q1.main.pole(1), k2.coil.pole(1), wire=("BK", 2.5))


def test_a_pole_past_the_count_names_the_count() -> None:
    d = design(series_library(), place="C1")
    q1, k2 = d.device("Q1", "TEST-MCB-3P"), d.device("K2", "TEST-MCB-3P")
    with pytest.raises(
        AuthorError,
        match=r"Q1\.main has 3 poles; pole\(4\) is past the last; use a pole from 1 to 3",
    ):
        d.series(q1.main.pole(4), k2.main.pole(1), wire=("BK", 2.5))
