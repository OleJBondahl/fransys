"""WP18 tests: authored layout kinds carry no position (ROADMAP WP18,
design/layout-namespace.md)."""

import dataclasses

from fransys_model.layout import AUTHORED_KINDS, DERIVED_KINDS

FORBIDDEN_FIELDS = frozenset({"x", "y", "page", "number", "points"})


def _field_names(cls: type) -> set[str]:
    return set(vars(cls)["__dataclass_fields__"])


def _position_fields(cls: type) -> set[str]:
    """The fields of `cls` that would let an author pin a position or a page."""
    return _field_names(cls) & FORBIDDEN_FIELDS


def test_no_authored_kind_has_a_position_or_page_field() -> None:
    """No authored layout kind declares `x`, `y`, `page`, `number` or `points`."""
    offenders = {cls.__name__: _position_fields(cls) for cls in AUTHORED_KINDS}
    assert offenders == {cls.__name__: set() for cls in AUTHORED_KINDS}


def test_position_check_fails_on_a_synthetic_pinning_kind() -> None:
    """The check catches an authored kind that pins `x` and `page`."""

    @dataclasses.dataclass(frozen=True)
    class PinnedHint:
        function: str
        x: int
        page: int

    assert _position_fields(PinnedHint) == {"x", "page"}


def test_every_derived_kind_names_its_producer() -> None:
    """Every derived layout kind declares `produced_by`; no authored kind does."""
    assert all("produced_by" in _field_names(cls) for cls in DERIVED_KINDS)
    assert not any("produced_by" in _field_names(cls) for cls in AUTHORED_KINDS)


def test_every_layout_kind_is_in_the_layout_namespace() -> None:
    """Every kind in either tuple is named `layout.*`, and no kind is listed twice."""
    kinds = [vars(cls)["__kind__"] for cls in (*AUTHORED_KINDS, *DERIVED_KINDS)]
    assert all(kind.startswith("layout.") for kind in kinds)
    assert len(set(kinds)) == len(kinds)
