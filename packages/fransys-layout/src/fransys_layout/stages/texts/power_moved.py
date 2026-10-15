"""Layout-0245: a power symbol's lead and text are set again on a page whose markers moved.

A pin view moves under its cell after the leads are set (HL19), so two symbols that stood
clear of each other can touch. The page's leads and power texts are set again on the moved pins.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from fransys_layout.stages.content import content_box
from fransys_layout.stages.labels import SlotFrame
from fransys_layout.stages.slices import by_plan, page_of
from fransys_layout.stages.types import LabelKind

from .place_texts import LABEL_UNPLACED
from .power import with_power_labels
from .power_lead import POWER_SYMBOL_UNPLACED, with_power_leads

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_layout.stages.types import (
        LinkMarker,
        PagePlan,
        PlacedFunction,
        PlacedLabel,
        Profile,
        SheetFormat,
    )
    from fransys_model.kernel import Finding, Id

    type Page = tuple[tuple[PlacedFunction, ...], tuple[PlacedLabel, ...]]


@dataclass(frozen=True, slots=True)
class PowerFrame:
    """What setting a page's power symbols needs: the sheet, the profile, the text slot."""

    sheet: SheetFormat
    profile: Profile
    slot: str


@dataclass(frozen=True, slots=True)
class PowerRedo:
    """What the second pass redid: the ports of its symbols, and its findings for them."""

    ports: frozenset[Id[Any]] = frozenset()
    findings: tuple[Finding, ...] = ()

    def over(self, findings: Sequence[Finding]) -> list[Finding]:
        """`findings` less the first pass's power findings of the redone ports, plus the new."""
        power = {POWER_SYMBOL_UNPLACED, LABEL_UNPLACED}  # a power text's handle is its port
        kept = [
            one for one in findings if one.code not in power or one.subjects[0] not in self.ports
        ]
        return [*kept, *self.findings]


def reset_power(
    plans: tuple[PagePlan, ...],
    pages: Sequence[Page],
    markers: tuple[LinkMarker, ...],
    was: tuple[LinkMarker, ...],
    frame: PowerFrame,
) -> tuple[list[Page], tuple[LinkMarker, ...], PowerRedo]:
    """`pages` and `markers` with the power leads and texts set again where a marker moved."""
    found: list[Page] = []
    redo = PowerRedo()
    led: dict[int, LinkMarker] = {}
    slots = SlotFrame(content=content_box(frame.sheet), profile=frame.profile)
    mine, before = by_plan(markers, page_of, plans), by_plan(was, page_of, plans)
    for (placed, labels), now, then in zip(pages, mine, before, strict=True):
        if now == then or not any(one.symbol for one in now):
            found.append((placed, labels))
            continue
        page, again, one = _again(placed, labels, now, (slots, frame.slot))
        found.append(page)
        redo = PowerRedo(redo.ports | one.ports, (*redo.findings, *one.findings))
        # by_plan hands back the same marker objects, so identity finds them in `markers`
        led.update((id(old), new) for old, new in zip(now, again, strict=True))
    return found, tuple(led.get(id(one), one) for one in markers), redo


def _again(
    placed: tuple[PlacedFunction, ...],
    labels: tuple[PlacedLabel, ...],
    now: tuple[LinkMarker, ...],
    on: tuple[SlotFrame, str],
) -> tuple[Page, tuple[LinkMarker, ...], PowerRedo]:
    """One page with its power leads and texts set again, and what that redid."""
    slots, slot = on
    plain = tuple(one for one in labels if not _power_text(one, slot))
    again, lead_findings = with_power_leads(now, placed, plain)
    made, text_findings = with_power_labels(plain, placed, again, slots, slot)
    ports = frozenset(one.port for one in now if one.symbol)
    return (placed, made), again, PowerRedo(ports, (*lead_findings, *text_findings))


def _power_text(label: PlacedLabel, slot: str) -> bool:
    """Whether `label` is a power symbol's text, placed in the power slot."""
    return label.kind is LabelKind.MARKING and label.slot == slot
