"""`readability_units`: a unit row adds its pages up and takes the extremes (readability R10)."""

from dataclasses import replace
from decimal import Decimal

from fransys_model.derive import ReadabilityPage, readability_units
from fransys_model.kernel import Id

_BASE = ReadabilityPage(
    page=Id(kind="layout.page", value="1"),
    unit=None,
    drawing_set=1,
    number=1,
    text_mm=Decimal("2.5"),
    min_text_mm=Decimal("2.5"),
    fill_percent=80,
    wire_crossings=1,
    struck_labels=2,
    text_overlaps=3,
    lone_cells=4,
    contact_images=5,
    contact_image_targets=6,
    single_contact_images=7,
    stars=8,
    star_branches=9,
    single_branch_stars=10,
    page_cuts=11,
)
_UNIT = Id(kind="unit", value="u")


def _page(number: int, **changes: object) -> ReadabilityPage:
    return replace(_BASE, number=number, **changes)


def test_the_counts_add_up_and_the_page_count_is_the_pages() -> None:
    (row,) = readability_units([_page(1), _page(2)])
    assert row.pages == 2
    assert (row.wire_crossings, row.struck_labels, row.text_overlaps, row.lone_cells) == (
        2,
        4,
        6,
        8,
    )
    assert (row.contact_images, row.contact_image_targets, row.single_contact_images) == (
        10,
        12,
        14,
    )
    assert (row.stars, row.star_branches, row.single_branch_stars, row.page_cuts) == (
        16,
        18,
        20,
        22,
    )


def test_the_smallest_text_and_the_emptiest_page_stand_for_the_unit() -> None:
    pages = [
        _page(1, text_mm=Decimal("2.5"), fill_percent=80),
        _page(2, text_mm=Decimal("1.8"), fill_percent=12),
    ]
    (row,) = readability_units(pages)
    assert (row.text_mm, row.fill_percent) == (Decimal("1.8"), 12)


def test_the_floor_of_the_unit_is_the_highest_floor_of_its_pages() -> None:
    pages = [_page(1, min_text_mm=Decimal("2.0")), _page(2, min_text_mm=Decimal("2.5"))]
    (row,) = readability_units(pages)
    assert row.min_text_mm == Decimal("2.5")


def test_each_unit_has_its_own_row_in_the_order_its_first_page_comes() -> None:
    rows = readability_units([_page(1, unit=_UNIT), _page(2), _page(3, unit=_UNIT)])
    assert [(row.unit, row.pages) for row in rows] == [(_UNIT, 2), (None, 1)]


def test_no_pages_give_no_rows() -> None:
    assert readability_units([]) == ()
