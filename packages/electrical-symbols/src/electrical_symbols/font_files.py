"""Where the vendored fonts live (G7)."""

from importlib.resources import files
from typing import cast
lazy from pathlib import Path

__all__ = ["font_dir"]


def font_dir() -> Path:
    """The directory holding the vendored DejaVu Sans Condensed faces and their licence text.

    A path through `importlib.resources`, not a read: the directory need not exist for this
    call to succeed. The facade's compiler call is the one that reads it (invariant 4).
    """
    return cast("Path", files("electrical_symbols") / "fonts")
