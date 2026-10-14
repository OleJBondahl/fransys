"""Dashed outlines of items by others, and their "by others" note (OUTLINES BO1, BO2, BO6)."""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

from fransys_layout.geometry import WIRING_GRID, push_clear, text_width

from .outlines import marker_reach, page_taken, title_box
from .runs import body_box, member_runs, run_box
from .slices import by_key, page_of
from .types import LabelKind, PlacedExternalOutline, PlacedLabel

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .types import FunctionSpec, Handle, LinkMarker, PlacedFunction


@dataclass(frozen=True)
class ExternalInputs:
    """What `external_outlines` reads: the specs, each external item's root and the note text."""

    spec_of: Mapping[Handle, FunctionSpec]
    root_of: Mapping[Handle, Handle]  # an external item to its outermost external ancestor
    text_height: int
    note: str


def _roots(
    placed: Sequence[PlacedFunction], inputs: ExternalInputs
) -> dict[Handle, list[PlacedFunction]]:
    """The page's placements of external items, by the external root each belongs to."""
    groups: dict[Handle, list[PlacedFunction]] = {}
    for one in placed:
        root = inputs.root_of.get(inputs.spec_of[one.function].item)
        if root is not None:
            groups.setdefault(root, []).append(one)
    return groups


def _run_texts(
    run: Sequence[PlacedFunction],
    labels: Sequence[PlacedLabel],
    markers: Sequence[LinkMarker],
    inputs: ExternalInputs,
) -> list[Any]:
    """The labels and link markers of a run's functions and ports: they stand inside its box."""
    names = {m.function for m in run}
    names |= {p.port for m in run for p in inputs.spec_of[m.function].ports}
    return [
        *(label.box for label in labels if label.subject in names),
        *(marker_reach(marker) for marker in markers if marker.port in names),
    ]


def _page_externals(
    placed: tuple[PlacedFunction, ...],
    labels: tuple[PlacedLabel, ...],
    markers: Sequence[LinkMarker],
    inputs: ExternalInputs,
    where: tuple[int, int],
) -> tuple[list[PlacedLabel], list[PlacedExternalOutline]]:
    """One page's notes and outlines: one outline per run, one note per external root."""
    taken = page_taken(placed, labels, markers)
    notes: list[PlacedLabel] = []
    outlines: list[PlacedExternalOutline] = []
    margin = WIRING_GRID // 2
    for root, members in sorted(
        _roots(placed, inputs).items(), key=lambda kv: min((m.at.x, m.at.y) for m in kv[1])
    ):
        names = {m.function for m in members}
        foreign = [body_box(f) for f in placed if f.function not in names]
        boxes = [
            (run, run_box(run, _run_texts(run, labels, markers, inputs), padding=margin))
            for run in member_runs(members, placed, obstacles=foreign)
        ]
        leads = [min(run, key=lambda m: (m.at.x, m.at.y)) for run, _ in boxes]
        outlines += [
            PlacedExternalOutline(
                item=root, lead=lead.function, drawing_set=where[0], page=where[1], box=box
            )
            for lead, (_, box) in zip(leads, boxes, strict=True)
        ]
        first = min(range(len(boxes)), key=lambda at: (leads[at].at.x, leads[at].at.y))
        size = (text_width(inputs.note, height=inputs.text_height), inputs.text_height)
        note = title_box(boxes[first][1], size, taken, drawn_top=False)
        taken.append(note)
        notes.append(
            PlacedLabel(
                kind=LabelKind.TAG,
                subject=leads[first].function,
                slot="external_note",
                drawing_set=where[0],
                page=where[1],
                box=note,
            )
        )
    return notes, outlines


def _is_table(label: PlacedLabel) -> bool:
    """Whether `label` is a contact table, headed or lone (`images` names the slots)."""
    return label.kind is LabelKind.CROSS_REFERENCE and label.slot.startswith("contacts")


def _bands(tables: Sequence[PlacedLabel]) -> list[list[PlacedLabel]]:
    """`tables` in reader order, grouped into bands: tables whose rows overlap in y share one."""
    bands: list[list[PlacedLabel]] = []
    reach = 0
    for table in sorted(tables, key=lambda t: (t.box.y, t.box.x)):
        if bands and table.box.y < reach:
            bands[-1].append(table)
            reach = max(reach, table.box.y + table.box.height)
        else:
            bands.append([table])
            reach = table.box.y + table.box.height
    return bands


def _band_drop(band: Sequence[PlacedLabel], held: Sequence[Any], gap: int) -> int:
    """The one distance `band` moves down: the largest any table needs to clear `held`."""
    drop = 0
    while True:
        need = max(
            push_clear(replace(t.box, y=t.box.y + drop), held, gap=gap, axis="y").y
            - (t.box.y + drop)
            for t in band
        )
        if need <= 0:
            return drop
        drop += need


def _tables_below(labels: Sequence[PlacedLabel], held: Sequence[Any]) -> list[PlacedLabel]:
    """layout-0238: `labels` with each band of contact tables moved down, whole, to clear `held`.

    A band keeps its stagger (owner 2026-10-06 G1, 2026-10-11): every table in it moves by the
    largest push any of them needs. Bands settle in reader order and clear the ones before them.
    """
    gap = WIRING_GRID // 2
    moved: dict[int, PlacedLabel] = {}
    settled: list[Any] = []
    for band in _bands([one for one in labels if _is_table(one)]):
        drop = _band_drop(band, [*held, *settled], gap)
        for table in band:
            box = replace(table.box, y=table.box.y + drop)
            settled.append(box)
            if drop:
                moved[id(table)] = replace(table, box=box)
    return [moved.get(id(one), one) for one in labels]


def external_outlines(
    plans: tuple[Any, ...],
    pages: Sequence[tuple[tuple[PlacedFunction, ...], tuple[PlacedLabel, ...]]],
    markers: tuple[LinkMarker, ...],
    inputs: ExternalInputs,
) -> tuple[
    list[tuple[tuple[PlacedFunction, ...], tuple[PlacedLabel, ...]]],
    tuple[PlacedExternalOutline, ...],
]:
    """Per page, a dashed outline per run of an external item and its note; the pages with notes."""
    on_page = by_key(markers, page_of)
    found: list[tuple[tuple[PlacedFunction, ...], tuple[PlacedLabel, ...]]] = []
    outlines: list[PlacedExternalOutline] = []
    for plan, (placed, labels) in zip(plans, pages, strict=True):
        where = (plan.drawing_set, plan.number)
        rest = tuple(one for one in labels if not _is_table(one))
        notes, boxes = _page_externals(placed, rest, on_page.get(where, ()), inputs, where)
        held = [*(one.box for one in boxes), *(note.box for note in notes)]
        found.append((placed, (*_tables_below(labels, held), *notes)))
        outlines.extend(boxes)
    return found, tuple(outlines)
