"""The one printed size of a profile's text: `text_height` grid units on a sheet, in millimetres."""

from decimal import Decimal

from fransys_model.derive.text_width import G_PER_MODULE
lazy from fransys_model.layout import Profile

__all__ = ["text_size_mm", "text_under_floor"]


def text_size_mm(text_height: int, module_mm: Decimal) -> Decimal:
    """The font size in mm that `text_height` G prints at on a sheet of `module_mm`."""
    return Decimal(text_height) * module_mm / G_PER_MODULE


def text_under_floor(profile: Profile, module_mm: Decimal) -> Decimal | None:
    """The size in mm `profile` prints text at on `module_mm` when it is under `min_text_mm`."""
    printed = text_size_mm(profile.text_height, module_mm)
    return printed if printed < profile.min_text_mm else None
