"""Where the vendored fonts live (spec P2)."""

from importlib.resources import files
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from pathlib import Path


def font_dir() -> Path:
    """The directory holding the vendored Liberation Serif faces and their licence text.

    A path through `importlib.resources`, not a read: the directory need not exist for
    this call to succeed. The package adds no third-party dependency and reads no file
    (root CLAUDE.md invariant 4); the facade's compiler call is the one that reads it.
    """
    return cast("Path", files("fransys_pdf") / "fonts")
