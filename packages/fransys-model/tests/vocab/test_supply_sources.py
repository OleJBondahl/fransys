"""RATINGS-3 acceptance 15 and 16: the source declarations of a supply name (ruling Q3 ii).

A declaration is a source when no other declaration of its name sits in a unit that strictly
encloses its own; a declaration with no unit encloses every unit.
"""

from plant import Plant
from rating_plant import rail, supply

from fransys_model.vocab.supply_sources import source_declarations
lazy from fransys_model.kernel import Id
lazy from fransys_model.vocab.core import Unit


def _keys(plant: Plant, name: str = "s") -> list[tuple[str, ...]]:
    return sorted(d.key for d in source_declarations(plant.model())[name])


def _declare(plant: Plant, key: str, unit: Id[Unit] | None = None) -> None:
    supply(plant, key, {"X": rail("1", 0)}, name="s", unit=unit)


def test_a_container_declaration_hides_the_nested_units() -> None:
    plant = Plant()
    cabinet = plant.unit("cabinet")
    _declare(plant, "top")
    _declare(plant, "in-unit", cabinet)

    assert _keys(plant) == [("top",)]


def test_a_unit_alone_counts() -> None:
    plant = Plant()
    _declare(plant, "in-unit", plant.unit("cabinet"))

    assert _keys(plant) == [("in-unit",)]


def test_a_container_that_declares_nothing_leaves_the_nested_unit_as_source() -> None:
    plant = Plant()
    cabinet = plant.unit("cabinet")
    _declare(plant, "in-unit", plant.unit("panel", parent=cabinet))

    assert _keys(plant) == [("in-unit",)]


def test_two_declarations_in_one_unit_both_count() -> None:
    plant = Plant()
    cabinet = plant.unit("cabinet")
    _declare(plant, "a", cabinet)
    _declare(plant, "b", cabinet)

    assert _keys(plant) == [("a",), ("b",)]


def test_two_declarations_with_no_unit_both_count() -> None:
    plant = Plant()
    _declare(plant, "a")
    _declare(plant, "b")

    assert _keys(plant) == [("a",), ("b",)]


def test_sibling_units_both_count() -> None:
    plant = Plant()
    _declare(plant, "a", plant.unit("left"))
    _declare(plant, "b", plant.unit("right"))

    assert _keys(plant) == [("a",), ("b",)]


def test_only_the_outer_of_two_nested_declarations_counts() -> None:
    plant = Plant()
    outer = plant.unit("outer")
    middle = plant.unit("middle", parent=outer)
    deep = plant.unit("deep", parent=middle)
    _declare(plant, "deep-decl", deep)
    _declare(plant, "outer-decl", outer)

    assert _keys(plant) == [("outer-decl",)]


def test_the_rule_counts_per_name() -> None:
    plant = Plant()
    cabinet = plant.unit("cabinet")
    supply(plant, "top", {"X": rail("1", 0)}, name="s")
    supply(plant, "other", {"Y": rail("1", 0)}, name="t", unit=cabinet)

    assert [d.key for d in source_declarations(plant.model())["t"]] == [("other",)]


def test_each_tuple_is_in_id_order() -> None:
    plant = Plant()
    for key in ("a", "b", "c"):
        _declare(plant, key)
    ids = [d.id for d in source_declarations(plant.model())["s"]]

    assert ids == sorted(ids)
    assert len(ids) == 3
