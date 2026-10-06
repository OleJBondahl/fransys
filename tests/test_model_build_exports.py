"""Pins `fransys.__all__` against MODEL-BUILD PS3's new re-exports.

A consumer needs `Draft`, `Model` (from the kernel) and `PartLibraryError` (from
`fransys_parts`) reachable one layer up through `fransys`; this pins that they are both
listed and actually resolvable, not just named in `__all__` with a stale or missing import.
"""

import fransys as fr

_NEW_NAMES = frozenset({"Draft", "Model", "PartLibraryError"})


def test_fransys_all_lists_the_new_model_build_names() -> None:
    """`fransys.__all__` is a superset of MODEL-BUILD PS3's three new names."""
    assert set(fr.__all__) >= _NEW_NAMES


def test_the_new_names_are_actually_reachable_as_attributes() -> None:
    """Each new name in `fransys.__all__` resolves to a real attribute, not a dangling entry."""
    for name in _NEW_NAMES:
        assert hasattr(fr, name), name
        getattr(fr, name)
