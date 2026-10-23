"""`Facts.series` (SP3): each region's `derive.series_parallel` tree, as core values."""

from typing import TYPE_CHECKING

from fransys_layout.core import Parallel, Series
from fransys_model.derive import SeriesRow, series_parallel
from fransys_model.kernel import render_id
from fransys_model.layout import Side

from .kit_keys import function_of
from .placement_skips import NOT_SERIES_PARALLEL, Skipped

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

    from fransys_layout.core import SeriesPart, Sym
    from fransys_model.derive import SeriesParallel, SeriesRowPart
    from fransys_model.kernel import Id
    from fransys_model.vocab import Port

    from .placement_env import Env

__all__ = ["bridges_of", "leaves", "series_of", "trees", "within"]

_MIN_LEAVES = 2  # a series of one symbol orders nothing


def _ends(env: Env, syms: Sequence[Sym]) -> dict[Id[Port], tuple[str, Side]]:
    """Each drawn port of `syms`: its symbol id and the side its pin leaves by at R0."""
    side = {(s.id, p.id): p.side for s in syms for p in s.pins}
    drawn = {s.id for s in syms}
    return {
        port: (ref.sym, Side(side[ref.sym, ref.pin].lower()))
        for port, ref in env.pins.items()
        if port not in env.undrawn and ref.sym in drawn
    }


def trees(env: Env, syms: Sequence[Sym]) -> SeriesParallel:
    """`derive.series_parallel` over the drawn ports of `syms`."""
    return series_parallel(env.model, _ends(env, syms))


def _part(part: SeriesRowPart) -> SeriesPart:
    if isinstance(part, str):
        return part
    parts = tuple(_part(p) for p in part.parts)
    return Series(parts) if isinstance(part, SeriesRow) else Parallel(parts)


def series_of(found: SeriesParallel) -> tuple[Series, ...]:
    """The regions of `found` as core `Series`, in its order."""
    return tuple(Series(tuple(_part(p) for p in row.parts)) for row in found.regions)


def leaves(part: SeriesPart) -> tuple[str, ...]:
    """The symbol ids of `part`, in its order."""
    if isinstance(part, str):
        return (part,)
    return tuple(leaf for p in part.parts for leaf in leaves(p))


def bridges_of(env: Env, found: SeriesParallel) -> tuple[Skipped, ...]:
    """One `Skipped` per bridge of `found`: its symbols' lead functions, as id texts."""
    lead_of = {sym: lead for lead, sym in env.ids.items()}
    out = []
    for leaves_ in found.bridges:
        ids = [render_id(function_of(env.model, lead_of[leaf])) for leaf in leaves_]
        out.append(Skipped("region", ids[0], NOT_SERIES_PARALLEL, tuple(ids[1:])))
    return tuple(out)


def within(series: Series, keep: Collection[str]) -> Series | None:
    """`series` with only the leaves in `keep`, or None when fewer than two are left."""
    part = _kept(series, keep)
    if part is None or len(leaves(part)) < _MIN_LEAVES:
        return None
    return part if isinstance(part, Series) else Series((part,))


def _kept(part: SeriesPart, keep: Collection[str]) -> SeriesPart | None:
    """`part` with the leaves out of `keep` dropped; a group of one is that one part."""
    if isinstance(part, str):
        return part if part in keep else None
    kind = type(part)
    found: list[SeriesPart] = []
    for p in part.parts:
        k = _kept(p, keep)
        found.extend(k.parts if isinstance(k, kind) else () if k is None else (k,))
    if not found:
        return None
    return found[0] if len(found) == 1 else kind(tuple(found))
