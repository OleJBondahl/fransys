"""Tests for `derive.facts.unit_names`: matching a unit instance by its release's name."""

import pytest
from plant import Plant

from fransys_model.derive.facts.unit_names import unit_name_unresolved
from fransys_model.vocab.finding_ref import ref

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


def test_case_c_names_where_a_parented_instance_sits() -> None:
    """The `under <parent>` clause is appended to the instance's own text (key and revision),
    never a replacement of it: pins the FACT that a parented instance is still identifiable by
    name, not merely by where it sits (accepted-prose separators aside, model-0094)."""
    plant = Plant()
    outer = plant.unit("outer", name="cabinet")
    inner = plant.unit("a", name="board", parent=outer)
    plant.unit("b", name="board")
    text = unit_name_unresolved(plant.model(), "board")
    assert "under" in text
    assert f"{ref(inner)} (1.1) under {ref(outer)}" in text


def test_exactly_one_match_raises_value_error() -> None:
    plant = Plant()
    plant.unit("a", name="relay-board")
    with pytest.raises(ValueError, match="resolves to exactly one unit"):
        unit_name_unresolved(plant.model(), "relay-board")
