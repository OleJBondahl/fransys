"""The layout's text room for a profile's capital height, and the floor it is held to."""

import math
lazy from decimal import Decimal

from fransys_model.derive.library_grid import mm_per_division
from fransys_model.derive.print_sizes import font_size_mm
from fransys_model.layout import profile_of, sheet_format_of
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.layout import Profile, SheetFormat
lazy from fransys_model.vocab.core import Unit

__all__ = ["text_room", "text_room_g", "text_under_floor"]


def text_room_g(model: Model, text_height_mm: Decimal, sheet: SheetFormat) -> int:
    """The grid units a text of capital height `text_height_mm` gets: font size over one G, up."""
    return math.ceil(font_size_mm(model, text_height_mm) / mm_per_division(model, sheet))


def text_room(model: Model, unit: Id[Unit] | None = None) -> int:
    """The grid units a text line gets under `unit`'s profile (`None`: the top) and its sheet.

    The one reader of the profile and sheet for the text room; sizes come from `text_room_g`.
    """
    profile = profile_of(model, unit)
    return text_room_g(model, profile.text_height_mm, sheet_format_of(model, profile.sheet_format))


def text_under_floor(profile: Profile) -> Decimal | None:
    """The capital height of `profile`'s text when it is under `min_text_height_mm`."""
    return profile.text_height_mm if profile.text_height_mm < profile.min_text_height_mm else None
