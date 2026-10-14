"""The bar lint: `BAR_SYMBOL`, a bar is never drawn, so it names no symbol."""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import _toml

if TYPE_CHECKING:
    from fransys_model.kernel import Finding


def check(entry: _toml.Table, path: str, line: int) -> list[Finding]:
    """`BAR_SYMBOL`: a `bar` function sets a `symbol`, but a bar is never drawn."""
    if entry.get("kind") != "bar" or entry.get("symbol") is None:
        return []
    return [_toml.finding("BAR_SYMBOL", path, line, "a bar is never drawn: remove symbol")]
