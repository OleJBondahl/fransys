"""The conventions the builder needs and `Options` lacks, and the options it passes on (E4)."""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, cast

from electrical_symbols import G_PER_MODULE, MARKER_FACING
from fransys_layout.core import Options, Size
from fransys_layout.symbols import outline_room
from fransys_model.layout import Side

from .placement_forms import TRUNK_FORMS
from .placement_syms import PLAIN
from .placement_views import marker_boxes

if TYPE_CHECKING:
    from collections.abc import Mapping

    from electrical_symbols import Library
    from fransys_model.layout import SheetFormat

__all__ = ["Conventions", "house_conventions", "options", "sheet_area"]

#: The `[layout]` keys `house_conventions` takes for itself; every other key is an `Options` field.
GENERAL = ("step", "pad")


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
        flip_turn=PLAIN[1],  # the turn that flips a chain cell
        driver_first=True,
        bundle_direction=True,
        tag_across_body=True,  # rule row CROSS-HALF-TAGS
        trunk_forms=TRUNK_FORMS,
        arrow_sides=("E", "W"),
        marker_facing=cast("Any", MARKER_FACING),
    )


@dataclass(frozen=True, slots=True)
class Conventions:
    """Text values for `fransys_el.footprints`, the tag side, and the core options."""

    options: Options
    text_height: int
    step: int
    pad: int
    tag_side: Side = Side.W


def options(conventions: Conventions, library: Library) -> Options:
    """The core options of `conventions`: the lane step is `library.grid.wire_pitch` (Ruling 62).

    The marker and the unit frame's room are read from `library` (layout-0316, R900).
    """
    chosen = replace(conventions.options, wiring_grid=library.grid.wire_pitch)
    if chosen.marker is None:
        chosen = replace(chosen, marker=marker_boxes(library))
    return replace(chosen, outline=chosen.outline or outline_room(library))


def sheet_area(sheet: SheetFormat) -> Size:
    """The content box of `sheet` in G: its content mm over one grid division (the page and the solve area)."""
    per_mm = G_PER_MODULE / sheet.module_mm
    return Size(int(sheet.content_width_mm * per_mm), int(sheet.content_height_mm * per_mm))


def house_conventions(layout: Mapping[str, object], library: Library, *, text_height: int) -> Conventions:
    """The house conventions: the text values and core options Fransys draws with.

    `text_height` is the profile's text room in G (`text_room_on`), a value the facade passes.

    `GENERAL` names the table's own keys; the rest are `Options`.
    """
    general = {key: layout[key] for key in GENERAL}
    rest = {key: value for key, value in layout.items() if key not in GENERAL}
    return Conventions(
        core_options(rest, library.grid.wire_pitch),
        text_height=text_height,
        step=cast("int", general["step"]),
        pad=cast("int", general["pad"]),
    )
