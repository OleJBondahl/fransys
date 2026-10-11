"""`cut_runs` starts a run only where a cut lies strictly between two neighbours."""

from fransys_layout.geometry import cut_runs


def test_cut_strictly_between_starts_a_run() -> None:
    assert cut_runs([1, 3, 5, 8], lambda n: n, [4]) == [[1, 3], [5, 8]]


def test_cut_on_a_neighbour_does_not_cut() -> None:
    assert cut_runs([1, 3, 5], lambda n: n, [3, 5]) == [[1, 3, 5]]


def test_empty_gives_no_runs() -> None:
    assert cut_runs([], lambda n: n, [1]) == []


def test_key_and_tuple_cuts() -> None:
    ends = [((0, 1), "a"), ((2, 0), "b")]
    assert cut_runs(ends, lambda end: end[0], [(1,)]) == [[ends[0]], [ends[1]]]
