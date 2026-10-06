"""The `POWER_LOSS_TWICE` lint: a part states its power loss for the part or per function (F8)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import _toml

if TYPE_CHECKING:
    from fransys_model.kernel import Finding


def _rating_of(entry: _toml.Table) -> _toml.Table:
    rating = entry.get("rating")
    return rating if isinstance(rating, dict) else {}


def check_power_loss_twice(data: _toml.Table, path: str, origins: _toml.Origins) -> list[Finding]:
    """`POWER_LOSS_TWICE`: `power_loss_w` in `[rating]` and in some `[function.rating]`."""
    part_rating = data.get("rating")
    functions = data.get("function")
    if type(part_rating) is not dict or "power_loss_w" not in part_rating:
        return []
    if type(functions) is not list:
        return []
    return [
        _toml.finding(
            "POWER_LOSS_TWICE",
            path,
            origins.get(("function", index), 1),
            f"function {entry.get('name')!r} states power_loss_w and so does the part's [rating]: "
            "state it once, or a heat sum counts it twice",
        )
        for index, entry in enumerate(functions)
        if isinstance(entry, dict) and "power_loss_w" in _rating_of(entry)
    ]
