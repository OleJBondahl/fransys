"""`one_per_row` drops a pole-linked contact in the row of one further left (layout-0235)."""

from types import SimpleNamespace
from typing import Any

from fransys_layout.stages.image_refs import one_per_row

_SHEET: Any = SimpleNamespace(content_height=100, frame_rows=2)


def _at(x: int, y: int, page: int = 1) -> Any:
    return SimpleNamespace(at=SimpleNamespace(x=x, y=y), page=page, drawing_set=0)


def _linked(*names: str) -> Any:
    return frozenset(names)


def _names(contacts: list[Any]) -> list[str]:
    return [c.function for c in contacts]


def test_a_linked_contact_right_of_another_in_one_row_is_dropped() -> None:
    contacts: Any = [SimpleNamespace(function=n) for n in ("a", "b", "c")]
    home: Any = {"a": _at(10, 10), "b": _at(20, 10), "c": _at(30, 10)}
    kept = one_per_row(contacts, home, _linked("a", "b", "c"), _SHEET)
    assert _names(kept) == ["a"]


def test_an_unlinked_contact_or_one_in_another_row_stays() -> None:
    contacts: Any = [SimpleNamespace(function=n) for n in ("a", "b", "c")]
    home: Any = {"a": _at(10, 10), "b": _at(20, 10), "c": _at(30, 90)}
    kept = one_per_row(contacts, home, _linked("a", "c"), _SHEET)
    assert _names(kept) == ["a", "b", "c"]
