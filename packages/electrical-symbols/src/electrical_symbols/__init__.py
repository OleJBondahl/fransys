"""Electrical graphical symbols as data, drawn after the conventions of IEC 60617."""

from pathlib import Path

from symdef import LIBRARY_VERSION as _SYMDEF_LIBRARY_VERSION
from symdef import Library, load_bundle

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
from electrical_symbols.generic_box import box_pitch, generic_box
from electrical_symbols.text import text_width

__all__ = [
    "GENERIC_BOX_KEY",
    "G_PER_MODULE",
    "LIBRARY",
    "LIBRARY_VERSION",
    "NORTH",
    "PORT_PITCH",
    "PORT_PITCH_G",
    "SOUTH",
    "WIRING_GRID",
    "box_pitch",
    "box_port_marking",
    "box_port_name",
    "default_order",
    "default_sides",
    "draw_order",
    "generic_box",
    "is_generic_box",
    "library_version",
    "text_width",
]

LIBRARY: Library = load_bundle(Path(__file__).parent / "bundle.json")


def library_version() -> str:
    """Both packages' versions, one string: `"electrical-symbols <v> / symdef <v>"`.

    The one home for this string (decision D40); layout and render re-use it.
    """
    return f"electrical-symbols {LIBRARY_VERSION} / symdef {_SYMDEF_LIBRARY_VERSION}"
