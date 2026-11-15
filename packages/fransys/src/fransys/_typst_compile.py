"""The one Typst compiler setup of the facade: the build's fonts, no system fonts (decision pdf-0001)."""

from typing import TYPE_CHECKING

import typst

import electrical_symbols

from ._settings_library import font_dirs

if TYPE_CHECKING:
    from .settings import Settings

__all__ = ["typst_compiler"]


def typst_compiler(settings: Settings) -> typst.Compiler:
    """A Typst compiler over the fonts of `settings` (ours when it names none); touches font files, so only the facade calls it."""
    fonts = font_dirs(settings.font)
    return typst.Compiler(font_paths=list(fonts) or [electrical_symbols.font_dir()], ignore_system_fonts=True)
