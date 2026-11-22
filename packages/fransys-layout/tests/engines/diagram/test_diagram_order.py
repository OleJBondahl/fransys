"""Row order in the stage columns: one pass down, one pass up, on abstract graphs."""

import pytest

from fransys_layout.engines.overview.order import order_columns


def _rank(*columns: tuple[str, ...]) -> dict[str, int]:
    """Text rank by alphabetical order of the letters used."""
    return {b: i for i, b in enumerate(sorted(b for c in columns for b in c))}


_PASSES = [  # (columns, lines, expected, id): the id names the pass or fallback a wrong order would kill
    ((("p", "q"), ("x", "y")), (("p", "y"), ("q", "x")), (("p", "q"), ("y", "x")), "down-pass"),  # y mean row 0, x mean row 1
    ((("p", "q", "r"), ("x", "y")), (("p", "x"), ("p", "y"), ("q", "x"), ("r", "y")), (("q", "p", "r"), ("x", "y")), "up-pass"),  # p 1/2, q 0, r 1
    (
        (("a", "b"), ("m", "n"), ("z",)),
        (("a", "n"), ("b", "m"), ("m", "z"), ("n", "z")),
        (("b", "a"), ("m", "n"), ("z",)),
        "up-pass-reads-next-column",
    ),
    ((("p", "q", "r"), ("x", "w", "y")), (("r", "x"), ("p", "y")), (("p", "q", "r"), ("y", "w", "x")), "no-previous-neighbour-keeps-row-as-key"),
]


@pytest.mark.parametrize(("cols", "lines", "expected"), [pytest.param(*row[:3], id=row[3]) for row in _PASSES])
def test_a_down_pass_then_an_up_pass_orders_the_columns(cols, lines, expected) -> None:
    """Down pass orders by mean row of the previous column, up pass by the next; text rank breaks ties."""
    assert order_columns(cols, lines, _rank(*cols)) == expected


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


def test_single_column_is_unchanged() -> None:
    assert order_columns((("b", "a"),), (), {"a": 0, "b": 1}) == (("b", "a"),)
