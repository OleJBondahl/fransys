"""Electrical graphical symbols as data, drawn after the conventions of IEC 60617."""

from symdef import LIBRARY_VERSION as _SYMDEF_LIBRARY_VERSION

from electrical_symbols._library import LIBRARY
from electrical_symbols._version import LIBRARY_VERSION
from electrical_symbols.box_ports import (
    G_PER_MODULE,
    GENERIC_BOX_KEY,
    NORTH,
    PORT_PITCH,
    PORT_PITCH_G,
    SOUTH,
    WIRING_GRID,
    box_port_marking,
    box_port_name,
    default_order,
    default_sides,
    draw_order,
    is_generic_box,
)
from electrical_symbols.bridge_mark import BridgePiece, bridge_mark, bridge_mark_room
from electrical_symbols.generic_box import box_pitch, generic_box
from electrical_symbols.natural import Natural, natural
from electrical_symbols.sheet import (
    frame_border,
    frame_strip,
    slot_box_mm,
    slot_room,
    slot_widths,
)
from electrical_symbols.sheet_svg import bold_layer, sheet_svg
from electrical_symbols.sheet_title import (
    TITLE_BLOCK_MIN_BAND_MM,
    TITLE_BLOCK_MIN_WIDTH_MM,
    TitleBlock,
    notice_table,
    title_block,
    title_logo,
)

__all__ = [
    "GENERIC_BOX_KEY",
    "G_PER_MODULE",
    "LIBRARY",
    "LIBRARY_VERSION",
    "NORTH",
    "PORT_PITCH",
    "PORT_PITCH_G",
    "SOUTH",
    "TITLE_BLOCK_MIN_BAND_MM",
    "TITLE_BLOCK_MIN_WIDTH_MM",
    "WIRING_GRID",
    "BridgePiece",
    "Natural",
    "TitleBlock",
    "bold_layer",
    "box_pitch",
    "box_port_marking",
    "box_port_name",
    "bridge_mark",
    "bridge_mark_room",
    "default_order",
    "default_sides",
    "draw_order",
    "frame_border",
    "frame_strip",
    "generic_box",
    "is_generic_box",
    "library_version",
    "natural",
    "notice_table",
    "sheet_svg",
    "slot_box_mm",
    "slot_room",
    "slot_widths",
    "title_block",
    "title_logo",
]


def library_version() -> str:
    """Both packages' versions, one string: `"electrical-symbols <v> / symdef <v>"`.

    The one home for this string (decision D40); layout and render re-use it.
    """
    return f"electrical-symbols {LIBRARY_VERSION} / symdef {_SYMDEF_LIBRARY_VERSION}"
