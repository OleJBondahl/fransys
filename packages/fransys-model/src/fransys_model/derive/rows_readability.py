"""Readability report row shapes (`fr.readability`, `derive.readability`).

Row shapes beside `rows.py` (model-0199); they import nothing from it.
"""

from decimal import Decimal

from fransys_model.kernel import Id, value
from fransys_model.layout import Page
from fransys_model.vocab.core import Unit


@value
class ReadabilityPage:
    """What `fr.readability` measures of one schematic page.

    `drawing_set` and `number` are as printed.
    `text_height_mm` is the profile's capital height of text
    and `min_text_height_mm` its floor for it. `fill_percent` is the share of the content box the
    drawn content covers, in whole percent. The four counts are the lint findings' own:
    `wire_crossings` (two wires of different conductors crossing), `struck_labels`
    (`WIRE_OVER_LABEL`), `text_overlaps` (`TEXT_OVERLAP`) and `lone_cells` (`LONE_CELL`).
    The references drawn on the page: contact images with the contacts they list, stars with the
    branches they name, and page cuts, which name one other page each. `single_*` counts the
    images with one contact and the stars with one branch; `single_contact_images_other_page` counts
    the single images whose contact is on another page.
    `wire_bends` and `wire_length_mm` read the page's routes. A loose symbol has no page, so the
    page row does not count it.
    """

    page: Id[Page]
    unit: Id[Unit] | None
    drawing_set: int
    number: int
    text_height_mm: Decimal
    min_text_height_mm: Decimal
    fill_percent: int
    wire_crossings: int
    wire_bends: int
    wire_length_mm: Decimal
    struck_labels: int
    text_overlaps: int
    lone_cells: int
    contact_images: int
    contact_image_targets: int
    single_contact_images: int
    single_contact_images_other_page: int
    stars: int
    star_branches: int
    single_branch_stars: int
    page_cuts: int


@value
class PageWires:
    """The routes of one page: their `bends` and their total `length_mm`."""

    bends: int
    length_mm: Decimal


@value
class ReadabilityUnit:
    """One unit's pages together: counts add up, `text_height_mm` and `fill_percent` are the lowest.

    `unit` is `None` for the design's own pages. `min_text_height_mm` is the highest floor of them.
    `loose_symbols` is the count of the unit's own loose symbols.
    """

    unit: Id[Unit] | None
    pages: int
    text_height_mm: Decimal
    min_text_height_mm: Decimal
    fill_percent: int
    wire_crossings: int
    wire_bends: int
    wire_length_mm: Decimal
    loose_symbols: int
    struck_labels: int
    text_overlaps: int
    lone_cells: int
    contact_images: int
    contact_image_targets: int
    single_contact_images: int
    single_contact_images_other_page: int
    stars: int
    star_branches: int
    single_branch_stars: int
    page_cuts: int


@value
class ReadabilityReport:
    """What `fr.readability` returns: a row for each schematic page, and for each unit.

    `loose_symbols` counts the symbols of the whole build that no page draws.
    """

    pages: tuple[ReadabilityPage, ...]
    units: tuple[ReadabilityUnit, ...]
    loose_symbols: int
