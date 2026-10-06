"""One entry point for the per-function electrical-fact lints: rest state, protection and energy."""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import _energy, _protection, _rest

if TYPE_CHECKING:
    from fransys_model.kernel import Finding

    from . import _toml


def check(entry: _toml.Table, path: str, line: int) -> list[Finding]:
    """Every rest-state, protection and energy fact lint of one function entry."""
    return [
        *_rest.check_rest(entry, path, line),
        *_protection.check_protection_links(entry, path, line),
        *_protection.check_protection_type(entry, path, line),
        *_energy.check_energy(entry, path, line),
    ]
