"""The unit rows of the readability report: each unit's page rows added up (readability R10)."""

from decimal import Decimal
lazy from collections.abc import Iterable, Mapping

lazy from fransys_model.kernel import Id
lazy from fransys_model.vocab.core import Unit

from .rows_readability import ReadabilityPage, ReadabilityUnit

__all__ = ["readability_units"]


def readability_units(
    pages: Iterable[ReadabilityPage], loose: Mapping[Id[Unit] | None, int]
) -> tuple[ReadabilityUnit, ...]:
    """One row per unit of `pages`, in the order its first page comes; `None` is the design.

    `loose` is the count of loose symbols by unit; a unit with none has 0.
    """
    by_unit: dict[object, list[ReadabilityPage]] = {}
    for page in pages:
        by_unit.setdefault(page.unit, []).append(page)
    return tuple(
        ReadabilityUnit(
            unit=group[0].unit,
            pages=len(group),
            text_height_mm=min(one.text_height_mm for one in group),
            min_text_height_mm=max(one.min_text_height_mm for one in group),
            fill_percent=min(one.fill_percent for one in group),
            wire_crossings=sum(one.wire_crossings for one in group),
            wire_bends=sum(one.wire_bends for one in group),
            wire_length_mm=sum((one.wire_length_mm for one in group), Decimal(0)),
            loose_symbols=loose.get(group[0].unit, 0),
            struck_labels=sum(one.struck_labels for one in group),
            text_overlaps=sum(one.text_overlaps for one in group),
            lone_cells=sum(one.lone_cells for one in group),
            contact_images=sum(one.contact_images for one in group),
            contact_image_targets=sum(one.contact_image_targets for one in group),
            single_contact_images=sum(one.single_contact_images for one in group),
            single_contact_images_other_page=sum(
                one.single_contact_images_other_page for one in group
            ),
            stars=sum(one.stars for one in group),
            star_branches=sum(one.star_branches for one in group),
            single_branch_stars=sum(one.single_branch_stars for one in group),
            page_cuts=sum(one.page_cuts for one in group),
        )
        for group in by_unit.values()
    )
