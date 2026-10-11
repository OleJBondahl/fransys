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
    put = {record.id: record for record in _derived(base) if record.id not in gone}
    fresh: dict[Id[Any], Record] = {}
    for units, laid in runs:
        fresh.update(owned_records(laid, units))
    put.update(fresh)
    put.update(_repaged(put, fresh))
    sets = sorted(
        (record for record in put.values() if isinstance(record, DrawingSet)),
        key=lambda one: (rank.get(one.unit, 0), one.number),
    )
    first = min((one.number for one in sets), default=0)
    put.update((one.id, replace(one, number=first + i)) for i, one in enumerate(sets))
    origin = Origin(file=produced_by(), line=1, note="derived layout record")
    return evolve(base, remove=derived_layout_ids(base), put=list(put.values()), origin=origin)


def _homes(fresh: Mapping[Id[Any], Record]) -> dict[Id[Any], tuple[Id[Page], int]]:
    """Each port a run's labels partner, with the page and `x` the run draws it at (first wins)."""
    homes: dict[Id[Any], tuple[Id[Page], int]] = {}
    for one in fresh.values():
        if isinstance(one, Label):
            for end in one.partners:
                homes.setdefault(end.port, (end.page, end.x))
    return homes


def _repaged(
    put: Mapping[Id[Any], Record], fresh: Mapping[Id[Any], Record]
) -> dict[Id[Any], Record]:
    """A kept label's partner on a replaced page, moved to where the run draws that port.

    A page's id follows its first drawn group, so another profile can rename the page and shift
    the columns. A port with no label in the run raises; one on two pages takes the first's.
    """
    pages = {one.id for one in put.values() if isinstance(one, Page)}
    homes = _homes(fresh)
    found: dict[Id[Any], Record] = {}
    for one in put.values():
        if not isinstance(one, Label):
            continue
        moved = tuple(_homed(end, homes) if end.page not in pages else end for end in one.partners)
        if moved != one.partners:
            found[one.id] = replace(one, partners=moved)
    return found


def _homed(
    end: CrossReferencePartner, homes: Mapping[Id[Any], tuple[Id[Page], int]]
) -> CrossReferencePartner:
    """`end` on the page and `x` its unit's run draws its port at."""
    if end.port not in homes:
        msg = f"cross-reference partner {end.port} is on a replaced page its unit's run lacks"
        raise LayoutError(msg)
    page, x = homes[end.port]
    return replace(end, page=page, x=x)
