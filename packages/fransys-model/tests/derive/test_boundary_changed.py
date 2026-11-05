"""`baseline.boundary_changed` compares the boundary field for field."""

import dataclasses

from fransys_model.derive.baseline import boundary_changed
from fransys_model.derive.rows_baseline import (
    BaselineBoundary,
    BaselineItem,
    BaselineUnit,
    Listing,
)


def _item(key: str | None) -> BaselineItem:
    return BaselineItem(
        designation="X1",
        mpn="M",
        manufacturer="Demo",
        installed=True,
        external=False,
        position=None,
        key=key,
    )


def _entry(ports: tuple[str, ...], key: str | None, pin: str | None) -> BaselineBoundary:
    return BaselineBoundary(designation="X1", ports=ports, rating=None, operating=None, key=key, pin=pin)


def _listing(item_key: str | None, *entries: BaselineBoundary) -> Listing:
    unit = BaselineUnit(name="u", version=1, revision=1, interface="i")
    return Listing(
        unit=unit,
        items=(_item(item_key),),
        units=(),
        boundary=entries,
        conductors=(),
        mates=(),
        nets=(),
    )


def test_a_previous_compares_the_key_too() -> None:
    old = _listing("k", _entry(("1",), "k", "1"))
    moved = dataclasses.replace(old, boundary=(_entry(("1",), "other", "1"),))
    assert boundary_changed(old, moved)
    assert not boundary_changed(old, old)
