"""The two readability counts no finding states: wire crossings and the references of a page.

`fr.readability` (readability R8 to R11) counts the other four from the findings themselves
(`geometry_by_page`, `lone_cells`, `fill_shares`). These two have no finding: a crossing is not
a defect, and a reference is the page doing its job. Both read the stage `Layout`.
"""

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fransys_layout.stages import LabelKind

from ._segments import runs_of

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fransys_layout.stages import LinkMarker, PlacedLabel, Route

__all__ = ("ReferenceCounts", "reference_counts", "wire_crossings")


def wire_crossings(routes: Iterable[Route]) -> int:
    """How often a wire runs across a wire of another physical net, inside both runs."""
    flat = [(route.physical_net, run) for route in routes for run in runs_of(route)]
    across = sorted(
        (
            (run.y, run.x, run.to_x, net)
            for net, run in flat
            if run.y == run.to_y and run.x < run.to_x
        ),
        key=lambda one: one[:3],
    )
    rows = [one[0] for one in across]
    found = 0
    for net, run in flat:
        if run.x != run.to_x or run.y == run.to_y:
            continue
        low, high = bisect_right(rows, run.y), bisect_left(rows, run.to_y)
        found += sum(
            1 for _, left, right, other in across[low:high] if other != net and left < run.x < right
        )
    return found


@dataclass(frozen=True, slots=True)
class ReferenceCounts:
    """The references one page draws: contact images, stars and page cuts (readability R9)."""

    contact_images: int = 0
    contact_image_targets: int = 0
    single_contact_images: int = 0
    stars: int = 0
    star_branches: int = 0
    single_branch_stars: int = 0
    page_cuts: int = 0


def _branches(markers: tuple[LinkMarker, ...]) -> dict[tuple[object, ...], int]:
    """How many "branch" markers name each star reference, by its port, set, page and net."""
    found: dict[tuple[object, ...], int] = {}
    for one in markers:
        if one.star == "branch":
            key = (one.connection, one.star_partner, one.star_partner_set, one.partner_page)
            found[key] = found.get(key, 0) + 1
    return found


def _is_image(label: PlacedLabel) -> bool:
    """Whether `label` is a coil's contact image: the cross-reference in the "contacts" slot."""
    return label.kind is LabelKind.CROSS_REFERENCE and label.slot == "contacts"


def reference_counts(
    labels: tuple[PlacedLabel, ...], markers: tuple[LinkMarker, ...]
) -> ReferenceCounts:
    """The references of one page: its `labels` and `markers`, both of that page only.

    A contact image is a coil's cross-reference label in the "contacts" slot. A star is a "ref"
    marker with its "branch" markers. A page cut is a connection cut in two across pages.
    """
    images = [len(one.partners) for one in labels if _is_image(one)]
    branches = _branches(markers)
    stars = [
        branches.get((one.connection, one.port, one.drawing_set, one.page), 0)
        for one in markers
        if one.star == "ref"
    ]
    return ReferenceCounts(
        contact_images=len(images),
        contact_image_targets=sum(images),
        single_contact_images=images.count(1),
        stars=len(stars),
        star_branches=sum(stars),
        single_branch_stars=stars.count(1),
        page_cuts=sum(1 for one in markers if not one.star and not one.symbol),
    )
