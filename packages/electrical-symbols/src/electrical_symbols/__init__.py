"""Electrical graphical symbols as data, drawn after the conventions of IEC 60617."""

from pathlib import Path

from graphical_symbols import LIBRARY_VERSION as _GRAPHICAL_LIBRARY_VERSION
from graphical_symbols import Library, load_bundle

from electrical_symbols._version import LIBRARY_VERSION
from electrical_symbols.generic_box import GENERIC_BOX_KEY, generic_box

__all__ = [
    "GENERIC_BOX_KEY",
    "LIBRARY",
    "LIBRARY_VERSION",
    "generic_box",
    "library_version",
]

LIBRARY: Library = load_bundle(Path(__file__).parent / "bundle.json")


def library_version() -> str:
    """Both packages' versions, one string: `"electrical-symbols <v> / graphical-symbols <v>"`.

    The one home for this string (render spec D3, decision D40); layout and render re-use it.
    """
    return f"electrical-symbols {LIBRARY_VERSION} / graphical-symbols {_GRAPHICAL_LIBRARY_VERSION}"
