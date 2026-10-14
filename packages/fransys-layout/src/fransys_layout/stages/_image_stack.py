"""Contact tables that share one column foot stack in coil order, each headed by its coil."""

from dataclasses import replace
from typing import TYPE_CHECKING

from fransys_layout.geometry import Box, overlaps, push_clear, text_width
from fransys_model.derive.drawing_text import CONTACTS_HEADED

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .types import Handle, PlacedFunction, PlacedLabel, Profile


def foot_down(heights: Sequence[int], profile: Profile) -> int:
    """Room under a column for the tables of its foot: each padded, each headed when two or more."""
    head = profile.heading_room if len(heights) > 1 else 0
    return sum(h + head + profile.marker_padding for h in heights)


def headed_width(width: int, heading: str, profile: Profile) -> int:
    """`width`, or the measured `heading` plus padding when that is wider (layout-0170)."""
    return max(width, text_width(heading, height=profile.text_height) + 2 * profile.marker_padding)


def heads_by_set(
    heads: Mapping[tuple[Handle, Handle | None], str], units: Mapping[int, Handle | None]
) -> dict[tuple[Handle, int], str]:
    """Each coil's heading in each drawing set: the text of the set's own unit (model-0238)."""
    sets: dict[Handle | None, list[int]] = {}
    for one, unit in units.items():
        sets.setdefault(unit, []).append(one)
    return {(coil, one): text for (coil, unit), text in heads.items() for one in sets.get(unit, ())}


def _groups(labels: Sequence[PlacedLabel]) -> list[list[PlacedLabel]]:
    """`labels` (already in reader order) split into runs whose boxes overlap one another."""
    found: list[list[PlacedLabel]] = []
    for label in labels:
        group = next((g for g in found if any(overlaps(label.box, o.box) for o in g)), None)
        if group is None:
            found.append([label])
        else:
            group.append(label)
    return found


def _stack(
    group: Sequence[PlacedLabel],
    blockers: Sequence[Box],
    heads: Mapping[tuple[Handle, int], str],
    profile: Profile,
) -> list[PlacedLabel]:
    """One foot's tables, top coil first, each a heading line taller and pushed below the last."""
    placed: list[PlacedLabel] = []
    for label in group:
        grown = replace(
            label.box,
            width=headed_width(
                label.box.width, heads.get((label.subject, label.drawing_set), ""), profile
            ),
            height=label.box.height + profile.heading_room,
        )
        box = push_clear(
            grown,
            [*blockers, *(one.box for one in placed)],
            gap=profile.marker_padding,
            axis="y",
        )
        placed.append(replace(label, slot=CONTACTS_HEADED, box=box))
    return placed


def stack_tables(
    tables: Mapping[tuple[int, int], list[PlacedLabel]],
    home: Mapping[Handle, PlacedFunction],
    markers: Mapping[tuple[int, int], tuple[Box, ...]],
    profile: Profile,
    heads: Mapping[tuple[Handle, int], str],
) -> dict[tuple[int, int], list[PlacedLabel]]:
    """Tables whose boxes meet stack downwards in reader order (coil y, then x), headed (0170)."""
    found = {}
    for page, labels in tables.items():
        order = sorted(labels, key=lambda t: (home[t.subject].at.y, home[t.subject].at.x))
        stacked: dict[int, PlacedLabel] = {}
        for group in _groups(order):
            if len(group) > 1:
                blockers = markers.get(page, ())
                for old, new in zip(group, _stack(group, blockers, heads, profile), strict=True):
                    stacked[id(old)] = new
        found[page] = [stacked.get(id(label), label) for label in labels]
    return found


def _on_one_baseline(
    tables: Mapping[tuple[int, int], list[PlacedLabel]], home: Mapping[Handle, PlacedFunction]
) -> dict[tuple[int, int], list[PlacedLabel]]:
    """I4: the contact images of one page row share one baseline, the lowest needed."""
    found = {}
    for page, labels in tables.items():
        rows: dict[int, list[PlacedLabel]] = {}
        for label in labels:
            rows.setdefault(home[label.subject].at.y, []).append(label)
        found[page] = [
            replace(label, box=replace(label.box, y=max(one.box.y for one in row)))
            for row in rows.values()
            for label in row
        ]
    return found


def settled_tables(
    tables: Mapping[tuple[int, int], list[PlacedLabel]],
    home: Mapping[Handle, PlacedFunction],
    markers: Mapping[tuple[int, int], tuple[Box, ...]],
    profile: Profile,
    heads: Mapping[tuple[Handle, int], str],
) -> dict[tuple[int, int], list[PlacedLabel]]:
    """I4: each page row on one baseline, then the tables that share a foot stacked (0170)."""
    return stack_tables(_on_one_baseline(tables, home), home, markers, profile, heads)
