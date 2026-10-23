"""The core options a stage test builds: the layout TOML, then what the tests need over it."""

import tomllib
from dataclasses import fields
from pathlib import Path
from typing import Any

import fransys_layout
from fransys_layout.core import Options, Size

_NAMES = {f.name for f in fields(Options)}
_TABLE = tomllib.loads(
    (Path(fransys_layout.__file__).parent / "layout.toml").read_text(encoding="utf-8")
)["layout"]

_GRID = 8

# The core values these tests were recorded on; the house's layout.toml pairs N/S pins and
# leaves card pitch at the footprint (E4), which the core tests do not assume.
RECORDED: dict[str, Any] = {"justify_cards": True, "pin_pairs": ()}


def _plain(value: object) -> object:
    """A TOML list as nested tuples."""
    return tuple(_plain(item) for item in value) if isinstance(value, list) else value


# el's facing views (`facing_views`): the rows keep the flags' room, so no end stands past the page
FACING: dict[str, Any] = {
    "marker_vertical": frozenset({"R90", "R270", "MR90", "MR270"}),
    "marker_above": "R270",
    "marker_below": "R90",
}


def core_options(**given: Any) -> Options:
    """`Options` from the layout TOML keys that are `Options` fields, then `given`."""
    keys: dict[str, Any] = {k: _plain(v) for k, v in _TABLE.items() if k in _NAMES}
    keys["margin"] = Size(*keys["margin"])
    keys = {"wiring_grid": _GRID, **keys, **RECORDED, **FACING, **given}
    return Options(**keys)
