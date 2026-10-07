"""Stage columns on abstract graphs (BD5): boxes are single letters, already in text order."""

import itertools

from fransys_layout.engines.diagram.columns import assign_columns


def test_star_centre_first_leaves_in_text_order() -> None:
    """Centre c has three lines, so it is column 0; leaves a, b, d follow in text order."""
    cols = assign_columns(("a", "b", "c", "d"), (("c", "a"), ("c", "b"), ("c", "d")))
    assert cols == (("c",), ("a", "b", "d"))  # kills: first box = fewest lines


def test_path_tie_goes_to_lowest_text_rank() -> None:
    """b and c both have two lines; b is earlier in text, so columns are [b], [a, c], [d]."""
    cols = assign_columns(("a", "b", "c", "d"), (("a", "b"), ("b", "c"), ("c", "d")))
    assert cols == (("b",), ("a", "c"), ("d",))  # kills: tie by reverse text


def test_parallel_lines_raise_a_box_count() -> None:
    """Without the doubled c-d line b would win the tie; with it c has three lines."""
    lines = (("a", "b"), ("b", "c"), ("c", "d"), ("c", "d"))
    assert assign_columns(("a", "b", "c", "d"), lines) == (("c",), ("b", "d"), ("a",))
    # kills: parallel lines counted once


def test_second_component_starts_after_the_last_column() -> None:
    """d has the most lines: c-d-e takes columns 0..1, the component a-b columns 2 and 3."""
    lines = (("a", "b"), ("c", "d"), ("d", "e"))
    cols = assign_columns(("a", "b", "c", "d", "e"), lines)
    assert cols == (("d",), ("c", "e"), ("a",), ("b",))  # kills: new component restarts at column 0


def test_same_column_line_keeps_both_ends() -> None:
    """In a triangle all boxes have two lines; a is first and b, c share column 1."""
    cols = assign_columns(("a", "b", "c"), (("a", "b"), ("b", "c"), ("a", "c")))
    assert cols == (("a",), ("b", "c"))


def test_box_without_a_line_is_its_own_column() -> None:
    """A lineless box does not crash; it forms a first column of its own after the others."""
    assert assign_columns(("a", "b", "c"), (("a", "b"),)) == (("a",), ("b",), ("c",))
    assert assign_columns((), ()) == ()


def test_lines_input_permutation_does_not_matter() -> None:
    """The same graph with lines permuted and their ends swapped gives the same columns."""
    boxes = tuple("abcdefgh")
    lines = (("a", "b"), ("b", "c"), ("c", "d"), ("c", "d"), ("e", "f"), ("f", "g"), ("g", "e"))
    want = assign_columns(boxes, lines)
    for shuffled in itertools.islice(itertools.permutations(lines), 0, None, 397):
        assert assign_columns(boxes, shuffled) == want
        assert assign_columns(boxes, tuple((b, a) for a, b in shuffled)) == want
