"""The conventions the builder needs and `Options` lacks, and the options it passes on (E4)."""

from dataclasses import dataclass, field

from fransys_layout.core import Options, Size
from fransys_model.layout import Side

__all__ = ["Conventions", "options"]

#: E4 written once: box pins spread to the attached columns' pitch, justified, rows aligned.
PLACEMENT_OPTIONS = Options(box_pins="spread", justify=True, band_align=True)


@dataclass(frozen=True, slots=True)
class Conventions:
    """Page area and text values for `derive.footprints`, the tag side, and the core options."""

    area: Size = field(default_factory=lambda: Size(1312, 854))
    text_height: int = 8
    step: int = 8
    pad: int = 2
    tiers: int = 2
    place_text: str = "/99.99"
    tag_side: Side = Side.W
    options: Options = PLACEMENT_OPTIONS


def options(conventions: Conventions) -> Options:
    """The core options of `conventions`."""
    return conventions.options
