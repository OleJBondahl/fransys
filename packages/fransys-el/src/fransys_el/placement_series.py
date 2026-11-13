"""`Facts.series` (SP3): each region's `derive.series_parallel` tree, as core values."""

from typing import TYPE_CHECKING

from fransys_layout.core import Series, leaves_of
from fransys_model.kernel import render_id

from .kit_keys import function_of
from .placement_skips import NOT_SERIES_PARALLEL, Skipped

if TYPE_CHECKING:
    from collections.abc import Collection

    from fransys_layout.core import SeriesPart
    from fransys_model.derive import SeriesParallel

    from .placement_env import Env

__all__ = ["bridges_of", "within"]

_MIN_LEAVES = 2  # a series of one symbol orders nothing


def bridges_of(env: Env, found: SeriesParallel) -> tuple[Skipped, ...]:
    """One `Skipped` per bridge of `found`: its symbols' lead functions, as id texts."""
    lead_of = {sym: lead for lead, sym in env.ids.items()}
    out = []
    for leaves_ in found.bridges:
        ids = [render_id(function_of(env.model, lead_of[leaf])) for leaf in leaves_]
        out.append(Skipped("region", ids[0], NOT_SERIES_PARALLEL, tuple(ids[1:])))
    return tuple(out)


def within(series: Series, keep: Collection[str]) -> Series | None:
    """`series` with only the leaves in `keep`, or None when fewer than two are left.

    An anchored series keeps its anchor and a lone leaf, and goes when its anchored leaf is out.
    """
    part = _kept(series, keep)
    if part is None:
        return None
    parts = part.parts if isinstance(part, Series) else (part,)
    if series.anchor is None:
        return Series(parts) if len(leaves_of(part)) >= _MIN_LEAVES else None
    end = leaves_of(series)[0 if series.anchor == "head" else -1]
    return Series(parts, series.anchor) if end in keep else None


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
