"""Tests for `vocab.unit_by_name`: matching a unit instance by its release's name (UN2, UN3)."""

import pytest
from plant import Plant

from fransys_model.vocab.unit_by_name import unit_name_unresolved, units_named


def test_one_matching_instance_is_the_one_id() -> None:
    plant = Plant()
    unit = plant.unit("a", name="relay-board")
    assert units_named(plant.model(), "relay-board") == (unit,)


def test_an_unknown_name_matches_nothing() -> None:
    plant = Plant()
    plant.unit("a", name="relay-board")
    assert units_named(plant.model(), "ghost") == ()


def test_two_instances_of_one_release_are_both_matches_sorted() -> None:
    plant = Plant()
    a = plant.unit("a", name="board")
    b = plant.unit("b", name="board")
    assert units_named(plant.model(), "board") == tuple(sorted((a, b)))


def test_two_releases_of_one_name_each_contribute_their_instance() -> None:
    plant = Plant()
    a = plant.unit("a", name="board", version=1, revision=1)
    b = plant.unit("b", name="board", version=1, revision=2)
    assert units_named(plant.model(), "board") == tuple(sorted((a, b)))


def test_a_release_with_no_instance_matches_nothing() -> None:
    plant = Plant()
    plant.release(name="board")
    assert units_named(plant.model(), "board") == ()


# ---- unit_name_unresolved: case (a), no release of that name ---------------------------------


def test_case_a_names_the_release_names_the_model_has() -> None:
    plant = Plant()
    plant.unit("a", name="io-board")
    text = unit_name_unresolved(plant.model(), "relay-board")
    assert "no unit release is named 'relay-board'" in text
    assert "'io-board'" in text
    assert "build the unit alone, or pass the instance's scope" in text.lower()


def test_case_a_with_no_releases_at_all_says_so() -> None:
    """Pins the exact word `none`, not a bare substring match that a mangled separator
    (`"XXnoneXX"` still contains the letters `n-o-n-e`) could slip past."""
    text = unit_name_unresolved(Plant().model(), "relay-board")
    assert "no unit release is named 'relay-board'" in text
    assert "the model has none." in text
    assert "build the unit alone, or pass the instance's scope" in text.lower()


# ---- unit_name_unresolved: case (b), releases exist but no instance ---------------------------


def test_case_b_names_the_versions_and_revisions() -> None:
    plant = Plant()
    plant.release(name="board", version=1, revision=1)
    plant.release(name="board", version=1, revision=2)
    text = unit_name_unresolved(plant.model(), "board")
    assert "1.1" in text
    assert "1.2" in text
    assert "no unit in the model is an instance of it" in text
    assert "build the unit alone, or pass the instance's scope" in text.lower()


# ---- unit_name_unresolved: case (c), several instances -----------------------------------------


def test_case_c_names_each_instance_with_its_revision() -> None:
    plant = Plant()
    plant.unit("a", name="board", version=1, revision=1)
    plant.unit("b", name="board", version=1, revision=2)
    text = unit_name_unresolved(plant.model(), "board")
    assert "1.1" in text
    assert "1.2" in text
    assert "2 units are instances of 'board'" in text
    assert "build the unit alone, or pass the instance's scope" in text.lower()


def test_case_c_names_where_a_parented_instance_sits() -> None:
    """The `under <parent>` clause is appended to the instance's own text (key and revision),
    never a replacement of it: pins the FACT that a parented instance is still identifiable by
    name, not merely by where it sits (accepted-prose separators aside, model-0094)."""
    plant = Plant()
    outer = plant.unit("outer", name="cabinet")
    plant.unit("a", name="board", parent=outer)
    plant.unit("b", name="board")
    text = unit_name_unresolved(plant.model(), "board")
    assert "under" in text
    assert "outer" in text
    assert "a (1.1) under outer" in text


def test_exactly_one_match_raises_value_error() -> None:
    plant = Plant()
    plant.unit("a", name="relay-board")
    with pytest.raises(ValueError, match="resolves to exactly one unit"):
        unit_name_unresolved(plant.model(), "relay-board")
