"""S20: each page's first slot call, run once its link markers stand, and its power symbols (D5)."""

from typing import TYPE_CHECKING
lazy from collections.abc import Sequence

lazy from fransys_layout.geometry import Box

from .content import content_box
from .labels import SlotFrame, place_slot_labels
from .slices import by_plan, page_of
from .texts.power import drawn_shapes, power_reserved, with_power_labels
from .texts.power_lead import with_power_leads

if TYPE_CHECKING:
    from fransys_model.kernel import Finding

    from .pagerun import FirstCall
    from .types import LinkMarker, PagePlan, PlacedFunction, PlacedLabel, SheetFormat


def _first_labels(
    call: FirstCall, markers: tuple[Box, ...]
) -> tuple[tuple[PlacedLabel, ...], tuple[Finding, ...]]:
    """S20: the page's first slot call, every marker's box and stub standing; no content box."""
    return place_slot_labels(
        call.requests,
        call.placed,
        call.drawn,
        occupied=(*call.occupied, *markers),
        frame=SlotFrame(content=None, profile=call.profile),
    )


def _held(markers: tuple[LinkMarker, ...]) -> tuple[Box, ...]:
    """The first call's keep-out: each ordinary end as drawn, each power end as reserved (D5)."""
    ordinary = tuple(one for one in markers if not one.symbol)
    return (*(one.box for one in drawn_shapes(ordinary)), *power_reserved(markers))


def labelled_pages(
    plans: tuple[PagePlan, ...],
    pages: Sequence[tuple[tuple[PlacedFunction, ...], FirstCall]],
    markers: tuple[LinkMarker, ...],
    power_slot: str,
    sheet: SheetFormat,
) -> tuple[
    list[tuple[tuple[PlacedFunction, ...], tuple[PlacedLabel, ...]]],
    tuple[LinkMarker, ...],
    tuple[Finding, ...],
]:
    """S20: each page's `(placed, labels)`, the markers with power leads set (D5), the findings."""
    found: list[tuple[tuple[PlacedFunction, ...], tuple[PlacedLabel, ...]]] = []
    findings: list[Finding] = []
    led: dict[int, LinkMarker] = {}
    for (placed, call), mine in zip(pages, by_plan(markers, page_of, plans), strict=True):
        labels, label_findings = _first_labels(call, _held(tuple(mine)))
        now, lead_findings = with_power_leads(tuple(mine), call.placed, labels)
        led.update((id(was), one) for was, one in zip(mine, now, strict=True))
        frame = SlotFrame(content=content_box(sheet), profile=call.profile)
        labels, power_findings = with_power_labels(labels, call.placed, now, frame, power_slot)
        found.append((placed, labels))
        findings.extend((*label_findings, *lead_findings, *power_findings))
    return found, tuple(led.get(id(one), one) for one in markers), tuple(findings)
