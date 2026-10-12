"""The unit rows of the readability report: each unit's page rows added up (readability R10)."""

lazy from collections.abc import Iterable

from .rows import ReadabilityPage, ReadabilityUnit

__all__ = ["readability_units"]


def readability_units(pages: Iterable[ReadabilityPage]) -> tuple[ReadabilityUnit, ...]:
    """One row per unit of `pages`, in the order its first page comes; `None` is the design."""
    by_unit: dict[object, list[ReadabilityPage]] = {}
    for page in pages:
        by_unit.setdefault(page.unit, []).append(page)
    return tuple(
        ReadabilityUnit(
            unit=group[0].unit,
            pages=len(group),
            text_mm=min(one.text_mm for one in group),
            min_text_mm=max(one.min_text_mm for one in group),
            fill_percent=min(one.fill_percent for one in group),
            wire_crossings=sum(one.wire_crossings for one in group),
            struck_labels=sum(one.struck_labels for one in group),
            text_overlaps=sum(one.text_overlaps for one in group),
            lone_cells=sum(one.lone_cells for one in group),
            contact_images=sum(one.contact_images for one in group),
            contact_image_targets=sum(one.contact_image_targets for one in group),
            single_contact_images=sum(one.single_contact_images for one in group),
            stars=sum(one.stars for one in group),
            star_branches=sum(one.star_branches for one in group),
            single_branch_stars=sum(one.single_branch_stars for one in group),
            page_cuts=sum(one.page_cuts for one in group),
        )
        for group in by_unit.values()
    )
