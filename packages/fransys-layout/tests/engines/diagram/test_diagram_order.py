"""Row order in the stage columns (BD5): one pass down, one pass up, on abstract graphs."""

from fransys_layout.engines.diagram.order import order_columns


def _rank(*columns: tuple[str, ...]) -> dict[str, int]:
    """Text rank by alphabetical order of the letters used."""
    return {b: i for i, b in enumerate(sorted(b for c in columns for b in c))}


def test_down_pass_reorders_a_column() -> None:
    """Lines p-y, q-x: y has mean row 0, x has mean row 1, so column 1 becomes (y, x)."""
    cols = (("p", "q"), ("x", "y"))
    out = order_columns(cols, (("p", "y"), ("q", "x")), _rank(*cols))
    assert out == (("p", "q"), ("y", "x"))  # kills: no down pass


def test_up_pass_reorders_columns_before_the_last() -> None:
    """Down keeps (x, y). Up: p = (0+1)/2, q = 0, r = 1, so column 0 becomes (q, p, r)."""
    cols = (("p", "q", "r"), ("x", "y"))
    lines = (("p", "x"), ("p", "y"), ("q", "x"), ("r", "y"))
    out = order_columns(cols, lines, _rank(*cols))
    assert out == (("q", "p", "r"), ("x", "y"))  # kills: no up pass


def test_up_pass_uses_the_next_column_not_the_previous() -> None:
    """Down gives (n, m); up re-sorts column 1 by z (tie: text order m, n), then column 0."""
    cols = (("a", "b"), ("m", "n"), ("z",))
    lines = (("a", "n"), ("b", "m"), ("m", "z"), ("n", "z"))
    out = order_columns(cols, lines, _rank(*cols))
    assert out == (("b", "a"), ("m", "n"), ("z",))  # kills: up pass reading the previous column


def test_parallel_lines_weight_the_mean() -> None:
    """z has lines p, p, q (mean 1/3), y has p, q (1/2): z precedes y; unweighted they tie."""
    cols = (("p", "q"), ("y", "z", "x"))
    lines = (("p", "z"), ("p", "z"), ("q", "z"), ("p", "y"), ("q", "y"), ("q", "x"))
    out = order_columns(cols, lines, _rank(*cols))
    assert out[1] == ("z", "y", "x")  # kills: parallel lines counted once


def test_ties_go_to_text_rank_and_same_column_lines_are_ignored() -> None:
    """a and b both join p; b is listed first but a ranks first. The a-b line changes nothing."""
    cols = (("p",), ("b", "a"))
    out = order_columns(cols, (("p", "a"), ("p", "b"), ("a", "b")), {"p": 0, "a": 1, "b": 2})
    assert out == (("p",), ("a", "b"))  # kills: tie by reverse text rank


def test_box_without_previous_neighbour_keeps_its_row_as_key() -> None:
    """w (row 1) has no line to column 0: key 1, between y (key 0 via p) and x (key 2 via r)."""
    cols = (("p", "q", "r"), ("x", "w", "y"))
    out = order_columns(cols, (("r", "x"), ("p", "y")), _rank(*cols))
    assert out == (("p", "q", "r"), ("y", "w", "x"))  # kills: fallback key at either end


def test_single_column_is_unchanged() -> None:
    assert order_columns((("b", "a"),), (), {"a": 0, "b": 1}) == (("b", "a"),)
