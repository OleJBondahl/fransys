"""The layout's text room for a profile's capital height, and the floor it is held to."""

import math
lazy from decimal import Decimal

from fransys_model.derive.print_sizes import font_size_mm
from fransys_model.derive.text_width import G_PER_MODULE
lazy from fransys_model.layout import Profile

__all__ = ["text_room_g", "text_under_floor"]


def text_room_g(text_height_mm: Decimal, module_mm: Decimal) -> int:
    """The grid units a text of capital height `text_height_mm` gets: font size over one G, up."""
    return math.ceil(font_size_mm(text_height_mm) * G_PER_MODULE / module_mm)


def text_under_floor(profile: Profile) -> Decimal | None:
    """The capital height of `profile`'s text when it is under `min_text_height_mm`."""
    return profile.text_height_mm if profile.text_height_mm < profile.min_text_height_mm else None
