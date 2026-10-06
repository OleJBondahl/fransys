"""Pins `fransys_model.derive.__all__` against MODEL-BUILD PS3's new re-exports.

A consumer needs `unit_releases`, `supply_systems`, `UnitRelease`, `SupplySystem` reachable one
layer up through `derive`; this pins that they are both listed and actually resolvable, not just
named in `__all__` with a stale or missing import.
"""

from fransys_model import derive

_NEW_NAMES = frozenset({"UnitRelease", "SupplySystem", "unit_releases", "supply_systems"})


def test_derive_all_lists_the_new_model_build_names() -> None:
    """`derive.__all__` is a superset of MODEL-BUILD PS3's four new names."""
    assert set(derive.__all__) >= _NEW_NAMES


def test_the_new_names_are_actually_reachable_as_attributes() -> None:
    """Each new name in `derive.__all__` resolves to a real attribute, not a dangling entry."""
    for name in _NEW_NAMES:
        assert hasattr(derive, name), name
        getattr(derive, name)
