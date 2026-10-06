"""`fransys_model.derive`'s top-level read surface (decision model-0074).

`docs/specs/2026-09-25-model-review.md`, section READ: a script reads the model's tables and
their record and enum types from `fr.derive` alone.
"""

import pytest
from plant import Plant

from fransys_model import derive, vocab
from fransys_model.vocab import tables

ACCESSORS = (
    "items",
    "functions",
    "ports",
    "conductors",
    "nets",
    "placements",
    "aspect_nodes",
    "units",
    "boundaries",
)
RECORDS = (
    "Item",
    "Function",
    "Port",
    "Net",
    "Conductor",
    "AspectNode",
    "Placement",
    "Unit",
    "Boundary",
)
ENUMS = ("Aspect", "FunctionKind", "PortRole", "NetClass", "ConductorKind")
NOT_EXPORTED = ("Id", "facets_of")


@pytest.mark.parametrize("name", [*ACCESSORS, *RECORDS, *ENUMS])
def test_every_read_name_is_listed_and_is_an_attribute(name: str) -> None:
    """Each name of the read surface is in `__all__` and reachable as `derive.<name>`."""
    assert name in derive.__all__
    assert hasattr(derive, name)


@pytest.mark.parametrize("name", ACCESSORS)
def test_each_accessor_is_the_one_in_vocab_tables(name: str) -> None:
    """The accessor is re-exported, never copied: `derive.items is tables.items`."""
    assert getattr(derive, name) is getattr(tables, name)


@pytest.mark.parametrize("name", [*RECORDS, *ENUMS])
def test_each_type_is_the_vocab_type(name: str) -> None:
    """The record or enum a table value carries is the `vocab` class itself."""
    assert getattr(derive, name) is getattr(vocab, name)


@pytest.mark.parametrize("name", NOT_EXPORTED)
def test_id_and_facets_of_stay_unexported(name: str) -> None:
    """`Id` stays unexported (ids are opaque keys) and `facets_of` stays internal."""
    assert name not in derive.__all__
    assert not hasattr(derive, name)


def test_units_is_the_table_and_unit_ids_is_gone() -> None:
    """`derive.units` is the table; the sorted-keys alias `unit_ids` is dropped (O15)."""
    plant = Plant()
    root = plant.unit("root", name="root-board")
    leaf = plant.unit("leaf", parent=root)
    model = plant.model()
    assert derive.units is tables.units
    assert "unit_ids" not in derive.__all__
    assert not hasattr(derive, "unit_ids")
    table = derive.units(model)
    assert set(table) == {root, leaf}
    assert derive.unit_release(model, root).name == "root-board"


def test_all_has_no_duplicates_and_every_name_resolves() -> None:
    """`__all__` lists each name once and each one is an attribute of `derive`."""
    assert len(derive.__all__) == len(set(derive.__all__))
    for name in derive.__all__:
        assert getattr(derive, name) is not None
