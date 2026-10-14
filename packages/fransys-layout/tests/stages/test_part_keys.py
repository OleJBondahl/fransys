"""A column part is keyed by its column's key, a kind word and its first line (layout-0230)."""

from fransys_layout.stages.part_keys import base_and_first, part_key_of


def test_a_part_is_keyed_by_the_column_a_kind_word_and_its_first_line() -> None:
    """The part from line 3 of column ("a",) is ("a", "lane", "0003")."""
    # UNDO: stages/part_keys.py:part_key_of, `{at + first:04d}` -> `{first:04d}` with at 0 only
    assert part_key_of(("a",), "lane", 3) == ("a", "lane", "0003")


def test_a_part_cut_again_counts_from_its_base() -> None:
    """A lane part starting at 2, cut at its line 3, is keyed from base line 5."""
    # UNDO: stages/part_keys.py:part_key_of, `at + first` -> `first`
    assert part_key_of(("a", "lane", "0002"), "lane", 3) == ("a", "lane", "0005")


def test_another_kind_word_is_not_a_part_of_this_kind() -> None:
    """A row part is a base column for the lane scheme."""
    # UNDO: stages/part_keys.py:base_and_first, `key[-2] == kind` -> `True`
    assert base_and_first(("a", "row", "0002"), "lane") == (("a", "row", "0002"), 0)
    assert base_and_first(("a", "row", "0002"), "row") == (("a",), 2)
