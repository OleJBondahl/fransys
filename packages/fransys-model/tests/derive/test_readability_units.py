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
    text_height_mm=Decimal("2.5"),
    min_text_height_mm=Decimal("2.5"),
    fill_percent=80,
    wire_crossings=1,
    wire_bends=13,
    wire_length_mm=Decimal("100.5"),
    struck_labels=2,
    text_overlaps=3,
    lone_cells=4,
    contact_images=5,
    contact_image_targets=6,
    single_contact_images=7,
    single_contact_images_other_page=12,
    stars=8,
    star_branches=9,
    single_branch_stars=10,
    page_cuts=11,
    contacts_not_drawn=13,
    references_off_document=14,
)
_UNIT = Id(kind="unit", value="u")


def _page(number: int, **changes: object) -> ReadabilityPage:
    return replace(_BASE, number=number, **changes)


def test_the_counts_add_up_and_the_page_count_is_the_pages() -> None:
    (row,) = readability_units([_page(1), _page(2)], {None: 3})
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
    assert row.single_contact_images_other_page == 24
    assert (row.wire_bends, row.wire_length_mm, row.loose_symbols) == (26, Decimal("201.0"), 3)
    assert (row.stars, row.star_branches, row.single_branch_stars, row.page_cuts) == (
        16,
        18,
        20,
        22,
    )


def test_the_smallest_text_and_the_emptiest_page_stand_for_the_unit() -> None:
    pages = [
        _page(1, text_height_mm=Decimal("2.5"), fill_percent=80),
        _page(2, text_height_mm=Decimal("1.8"), fill_percent=12),
    ]
    (row,) = readability_units(pages, {})
    assert (row.text_height_mm, row.fill_percent) == (Decimal("1.8"), 12)


def test_the_floor_of_the_unit_is_the_highest_floor_of_its_pages() -> None:
    pages = [
        _page(1, min_text_height_mm=Decimal("2.0")),
        _page(2, min_text_height_mm=Decimal("2.5")),
    ]
    (row,) = readability_units(pages, {})
    assert row.min_text_height_mm == Decimal("2.5")


def test_each_unit_has_its_own_row_in_the_order_its_first_page_comes() -> None:
    rows = readability_units([_page(1, unit=_UNIT), _page(2), _page(3, unit=_UNIT)], {_UNIT: 1})
    assert [(row.unit, row.pages, row.loose_symbols) for row in rows] == [
        (_UNIT, 2, 1),
        (None, 1, 0),
    ]


def test_no_pages_give_no_rows() -> None:
    assert readability_units([], {}) == ()


def test_the_spare_contacts_and_the_off_document_references_add_up() -> None:
    (row,) = readability_units([_page(1), _page(2)], {})
    assert (row.contacts_not_drawn, row.references_off_document) == (26, 28)
