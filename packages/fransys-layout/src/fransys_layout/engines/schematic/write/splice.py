"""Joining the runs of several profiles into one layout, by drawing set (model-0192)."""

from dataclasses import replace
from typing import TYPE_CHECKING, Any, cast

from fransys_layout.engines.schematic.write import produced_by
from fransys_layout.geometry import LayoutError
from fransys_model.kernel import Origin, evolve
from fransys_model.layout import (
    DERIVED_KINDS,
    CrossReferencePartner,
    DrawingSet,
    Label,
    LinkMarker,
    Page,
    StubEnd,
    derived_layout_ids,
    layout_of,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from fransys_model.kernel import Id, Model, Record


def _derived(laid: Model) -> list[Record]:
    """Every derived `layout.*` record of `laid`."""
    return [
        record
        for kind in DERIVED_KINDS
        for record in cast("Iterable[Record]", layout_of(laid, kind).values())
    ]


def drawn_units(laid: Model) -> frozenset[Id[Any]]:
    """The units that have a drawing set in `laid`."""
    return frozenset(one.unit for one in layout_of(laid, DrawingSet).values() if one.unit)


def _owner(
    record: Record, page_set: Mapping[Id[Any], Id[Any]], marker_page: Mapping[Id[Any], Id[Any]]
) -> Id[Any]:
    """The drawing set a derived record belongs to."""
    if isinstance(record, DrawingSet):
        return record.id
    if isinstance(record, Page):
        return record.drawing_set
    if isinstance(record, StubEnd):
        return page_set[marker_page[record.marker]]
    return page_set[cast("Any", record).page]


def owned_records(laid: Model, units: frozenset[Id[Any]]) -> dict[Id[Any], Record]:
    """Every derived record in a drawing set of one of `units`, by id."""
    page_set = {one.id: one.drawing_set for one in layout_of(laid, Page).values()}
    marker_page = {one.id: one.page for one in layout_of(laid, LinkMarker).values()}
    mine = {one.id for one in layout_of(laid, DrawingSet).values() if one.unit in units}
    return {
        record.id: record
        for record in _derived(laid)
        if _owner(record, page_set, marker_page) in mine
    }


def spliced(
    base: Model, runs: tuple[tuple[frozenset[Id[Any]], Model], ...], rank: Mapping[Id[Any], int]
) -> Model:
    """`base` with the drawing sets of each run's units taken from that run, set numbers redone.

    The sets are numbered as one run numbers them: the top design's, then each unit's in unit
    `rank` order, each unit's by its run's own number.
    """
    every = frozenset().union(*(units for units, _ in runs))
    gone = owned_records(base, every)
    parts = [owned_records(laid, units) for units, laid in runs]
    put = {record.id: record for record in _derived(base) if record.id not in gone}
    for part in parts:
        put.update(part)
    put.update(_repaged(put, *_drawn_by(base, gone, parts)))
    sets = sorted(
        (record for record in put.values() if isinstance(record, DrawingSet)),
        key=lambda one: (rank.get(one.unit, 0), one.number),
    )
    first = min((one.number for one in sets), default=0)
    put.update((one.id, replace(one, number=first + i)) for i, one in enumerate(sets))
    origin = Origin(file=produced_by(), line=1, note="derived layout record")
    return evolve(base, remove=derived_layout_ids(base), put=list(put.values()), origin=origin)


def _drawn_by(
    base: Model, gone: Mapping[Id[Any], Record], parts: Iterable[Mapping[Id[Any], Record]]
) -> tuple[dict[Id[Any], frozenset[Id[Page]]], dict[Id[Any], tuple[Id[Page], int]]]:
    """Per label, the pages its own run owns; per port, the page and `x` the owning run draws it at.

    A run names the pages and columns of its own drawing sets only; the base run owns the rest.
    A port takes the first end that its own run puts on a page that run owns.
    """
    kept = frozenset(one.id for one in layout_of(base, Page).values() if one.id not in gone)
    sources: list[tuple[Mapping[Id[Any], Record], frozenset[Id[Any]]]] = [
        (layout_of(base, Label), kept)
    ]
    sources += [
        (part, frozenset(i for i, one in part.items() if isinstance(one, Page))) for part in parts
    ]
    owner: dict[Id[Any], frozenset[Id[Page]]] = {}
    homes: dict[Id[Any], tuple[Id[Page], int]] = {}
    for records, own in sources:
        for one in records.values():
            if isinstance(one, Label):
                owner[one.id] = own
                for end in one.partners:
                    if end.page in own:
                        homes.setdefault(end.port, (end.page, end.x))
    return owner, homes


def _repaged(
    put: Mapping[Id[Any], Record],
    owner: Mapping[Id[Any], frozenset[Id[Page]]],
    homes: Mapping[Id[Any], tuple[Id[Page], int]],
) -> dict[Id[Any], Record]:
    """A label's partner on a page its own run does not own, moved to where the owning run draws it.

    A page's id follows its first drawn group, so another profile can rename the page and shift
    the columns. A port no owning run puts a label end on raises.
    """
    found: dict[Id[Any], Record] = {}
    for one in put.values():
        if not isinstance(one, Label):
            continue
        moved = tuple(
            end if end.page in owner[one.id] else _homed(end, homes) for end in one.partners
        )
        if moved != one.partners:
            found[one.id] = replace(one, partners=moved)
    return found


def _homed(
    end: CrossReferencePartner, homes: Mapping[Id[Any], tuple[Id[Page], int]]
) -> CrossReferencePartner:
    """`end` on the page and `x` the run that owns its port's page draws it at."""
    if end.port not in homes:
        msg = f"cross-reference partner {end.port} is on a replaced page its unit's run lacks"
        raise LayoutError(msg)
    page, x = homes[end.port]
    return replace(end, page=page, x=x)
