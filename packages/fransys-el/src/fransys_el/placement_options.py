"""The conventions the builder needs and `Options` lacks, and the options it passes on (E4)."""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, cast

from fransys_layout.core import Options, Size
from fransys_model.layout import Side

from .placement_syms import PLAIN
from .placement_views import marker_boxes

if TYPE_CHECKING:
    from collections.abc import Mapping

    from electrical_symbols import Library

__all__ = ["Conventions", "house_conventions", "options"]

#: The `[layout]` keys `house_conventions` takes for itself; every other key is an `Options` field.
GENERAL = ("area", "text_height", "step", "pad", "contact_tables")

#: The turn that flips a chain cell (the second of `placement_syms.PLAIN`).
FLIP_TURN = PLAIN[1]


def _plain(value: object) -> object:
    """A TOML list (or the tuple the settings freeze it to) as nested tuples."""
    if isinstance(value, list | tuple):
        return tuple(_plain(item) for item in value)
    return value


def core_options(layout: Mapping[str, object], wiring_grid: int) -> Options:
    """The core options of the `[layout]` table of the settings (SETTINGS ST1, R319.5).

    The table holds every number; a key `Options` does not know raises. The powers, the flip turn
    and the sides are the placement's own conventions (E4).
    """
    keys = {key: _plain(value) for key, value in layout.items()}
    keys["margin"] = Size(*cast("tuple[int, int]", keys["margin"]))
    return Options(
        **cast("dict[str, Any]", keys),
        wiring_grid=wiring_grid,
        flip_turn=FLIP_TURN,
        driver_first=True,
        bundle_direction=True,
        arrow_sides=("E", "W"),
    )


@dataclass(frozen=True, slots=True)
class Conventions:
    """Page area and text values for `derive.footprints`, the tag side, and the core options."""

    options: Options
    area: Size
    text_height: int
    step: int
    pad: int
    contact_tables: bool
    place_text: str = "/99.99"
    tag_side: Side = Side.W


def options(conventions: Conventions, library: Library) -> Options:
    """The core options of `conventions`: the lane step is `library.grid.wire_pitch` (Ruling 62).

    The marker is read from `library`'s symbol (layout-0316).
    """
    chosen = replace(conventions.options, wiring_grid=library.grid.wire_pitch)
    if chosen.marker is not None:
        return chosen
    return replace(chosen, marker=marker_boxes(library))


def house_conventions(layout: Mapping[str, object], library: Library) -> Conventions:
    """The house conventions: the page area, text values and core options Fransys draws with.

    `GENERAL` names the table's own keys; the rest are `Options`.
    """
    general = {key: layout[key] for key in GENERAL}
    rest = {key: value for key, value in layout.items() if key not in GENERAL}
    return Conventions(
        core_options(rest, library.grid.wire_pitch),
        area=Size(*cast("tuple[int, int]", general["area"])),
        text_height=cast("int", general["text_height"]),
        step=cast("int", general["step"]),
        pad=cast("int", general["pad"]),
        contact_tables=cast("bool", general["contact_tables"]),
    )
