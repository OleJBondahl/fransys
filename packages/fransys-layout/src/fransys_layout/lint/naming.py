"""The last pass over the findings: each about a drawn thing names its page and its designation.

The page is derive's `position_text`, as a reference from another drawing set prints it; the
designations and location labels are read once by `engines/schematic/read/finding_names.py` (V6b).
"""

from collections import defaultdict
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

from fransys_layout.stages.partition import UNIT_GROUP_SPLIT
from fransys_layout.stages.slices import page_of
from fransys_model.derive.drawing_text import position_text

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping

    from fransys_layout.stages.types import FunctionSpec, Layout
    from fransys_model.kernel import Finding, Id

    from ._harness import HarnessInk

_SHOWN = 4  # designations a message lists before "and N more"
type Page = tuple[int, int]


@dataclass(frozen=True, slots=True)
class Where:
    """Where each handle is drawn, where each group is planned, and each set's location labels."""

    pages: Mapping[Id[Any], set[Page]]
    groups: Mapping[Id[Any], set[Page]]
    labels: Mapping[int, tuple[str, ...]]


def _ink_pages(ink: HarnessInk) -> Iterator[tuple[Id[Any], Page]]:
    for piece in (*ink.lines, *ink.fan_outs, *ink.stubs):
        yield piece.harness, (piece.drawing_set, piece.page)
    for box in ink.boxes:
        yield box.function, (box.drawing_set, box.page)


def _layout_pages(layout: Layout) -> Iterator[tuple[Id[Any], Page]]:
    for one in layout.placed:
        yield one.function, page_of(one)
    for route in layout.routes:
        for handle in (route.connection, route.a, route.b):
            yield handle, page_of(route)
    for marker in layout.markers:
        yield marker.connection, page_of(marker)
        yield marker.port, page_of(marker)
    for label in layout.labels:
        yield label.subject, page_of(label)


def _pages_of(
    layout: Layout, specs: Iterable[FunctionSpec], ink: HarnessInk
) -> dict[Id[Any], set[Page]]:
    """Every handle the layout and the harness ink draw, with the pages it is drawn on."""
    found: defaultdict[Id[Any], set[Page]] = defaultdict(set)
    for handle, page in (*_ink_pages(ink), *_layout_pages(layout)):
        found[handle].add(page)
    for spec in specs:
        for port in spec.ports:
            found[port.port] |= found.get(spec.function, set())
    return found


def _suffix(positions: tuple[str, ...], names: tuple[str, ...]) -> str:
    """` (p3, p4: -K1:13, -K2:14)`: the positions, then the designations; empty when neither."""
    shown = list(names[:_SHOWN])
    if len(names) > _SHOWN:
        shown.append(f"and {len(names) - _SHOWN} more")
    parts = [text for text in (", ".join(positions), ", ".join(shown)) if text]
    return f" ({': '.join(parts)})" if parts else ""


def _groups_on(layout: Layout) -> dict[Id[Any], set[Page]]:
    """Each group, with the pages it is planned on."""
    found: defaultdict[Id[Any], set[Page]] = defaultdict(set)
    for plan in layout.pages:
        for planned in plan.groups:
            if planned.group is not None:
                found[planned.group].add((plan.drawing_set, plan.number))
    return found


def append_pages_and_designations(
    names: Mapping[Id[Any], str], where: Where, findings: Iterable[Finding]
) -> tuple[Finding, ...]:
    """`findings` with each message ending in the pages and designations of its subjects.

    The designations list in the order `names` holds its subjects (reader order, never `Id`).
    """
    named = []
    rank = {subject: place for place, subject in enumerate(names)}
    for finding in findings:
        # A unit group's split is about the pages it runs over (group subjects locate only here)
        table = where.groups if finding.code == UNIT_GROUP_SPLIT else where.pages
        on = sorted({page for subject in finding.subjects for page in table.get(subject, ())})
        positions = tuple(position_text(p, None, None, where.labels.get(s, ()), s) for s, p in on)
        members = sorted((s for s in finding.subjects if names.get(s)), key=rank.__getitem__)
        who = tuple(dict.fromkeys(names[s] for s in members))
        named.append(replace(finding, message=finding.message + _suffix(positions, who)))
    return tuple(named)


def where_drawn(
    layout: Layout,
    specs: Iterable[FunctionSpec],
    ink: HarnessInk,
    labels: Mapping[int, tuple[str, ...]],
) -> Where:
    """`Where` read from the layout and the harness ink."""
    return Where(pages=_pages_of(layout, specs, ink), groups=_groups_on(layout), labels=labels)
