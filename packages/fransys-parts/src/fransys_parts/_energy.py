"""The `energy` fact of a function entry: a supply or load names which way energy flows."""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import _toml

if TYPE_CHECKING:
    from fransys_model.kernel import Finding

_POWER = ("supply", "load")


def check_energy(entry: _toml.Table, path: str, line: int) -> list[Finding]:
    """`ENERGY_ON_NON_POWER`: the model refuses an energy direction on any other kind."""
    if entry.get("energy") is None or entry.get("kind") in _POWER:
        return []
    text = f"a {entry.get('kind')} function declares an energy direction"
    return [_toml.finding("ENERGY_ON_NON_POWER", path, line, text)]
