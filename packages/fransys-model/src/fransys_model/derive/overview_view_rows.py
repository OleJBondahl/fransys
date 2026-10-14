"""Every view of the overview, with the text of its boxes and lines (model-0202).

The system level, then each unit's plain level, its lanes view (O4), its strips opened and its
folds. It is the one reading of the views: the overview engine places what it returns and the page
prints it.
"""

from functools import partial
from typing import TYPE_CHECKING, Any
lazy from collections.abc import Iterator

from fransys_model.layout import OverviewMode, OverviewRef, OverviewRefKind
from fransys_model.vocab.tables import units
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab.core import Unit

from .instance_tag import instance_name, instance_tags
from .order import natural_key
from .overview_field import field_fold
from .overview_fold import fold_level
from .overview_levels import open_strips, overview_level, strip_view
from .overview_location import location_fold
from .overview_strip_stubs import strip_stubs
from .overview_view_fold import field_rows, fold_rows, location_rows
from .overview_view_plain import level_rows, strip_rows, tab_rows, with_tabs
from .rows_overview_view import Rows, ViewRows

if TYPE_CHECKING:
    from .overview_view_plain import Tabs
    from .rows_overview import FoldLevel

__all__ = ["overview_units", "overview_view_rows"]

_GROUPS = OverviewMode.GROUPS
_SEE_THROUGH = OverviewMode.SEE_THROUGH
_LEVELS = {OverviewRefKind.GROUP, OverviewRefKind.STRIPS}


def overview_units(model: Model) -> tuple[Id[Unit] | None, ...]:
    """`None` for the system, then every unit instance by the natural order of its designation."""
    named = [(natural_key(instance_name(instance_tags(model, u, None))), u) for u in units(model)]
    return (None, *(unit for _, unit in sorted(named)))


def _view(
    level: tuple[Id[Any] | None, OverviewRef | None, OverviewMode],
    open_: OverviewRef | None,
    rows: Rows,
) -> ViewRows:
    """A view; `open_` is its one open strip. A fold's members are rows of its box, not a view."""
    unit, opened, mode = level
    return ViewRows(unit=unit, level=opened, mode=mode, open=open_, boxes=rows[0], lines=rows[1])


def _system(model: Model, plain: Rows) -> Iterator[ViewRows]:
    """The system level's location fold, then its field-device fold and each box opened (O9)."""
    where = (None, None)
    places = location_fold(model)
    if places is not None:
        yield _view((*where, OverviewMode.LOCATION), None, location_rows(model, places))
    folds = field_fold(model)
    if not folds:
        return
    yield _view((*where, OverviewMode.FIELDS), None, field_rows(model, plain, folds))


def _plain(model: Model, unit: Id[Any] | None, tabs: Tabs) -> Iterator[ViewRows]:
    """The plain level of `unit`, then each of its strips opened; nothing when it is empty."""
    level = overview_level(model, unit)
    rows = with_tabs(level_rows(model, level), tabs)
    if not rows[0]:
        return
    yield _view((unit, None, OverviewMode.PLAIN), None, rows)
    if unit is None:
        yield from _system(model, rows)
        return
    yield _view((unit, None, OverviewMode.LANES), None, rows)
    for strip in open_strips(level):
        opened = strip_rows(
            model, unit, rows, strip_view(model, strip, unit), strip_stubs(model, strip, unit)
        )
        ref = OverviewRef(kind=OverviewRefKind.ITEM, item=strip)
        yield _view((unit, None, OverviewMode.PLAIN), ref, opened)
        yield _view((unit, None, OverviewMode.LANES), ref, opened)


def _fold_views(
    model: Model, level: FoldLevel, mode: OverviewMode, tabs: Tabs
) -> Iterator[ViewRows]:
    """A folded level, once per strip it opens.

    None when it is empty. The groups view opens no strip (O5).
    """
    where = (level.unit, level.opened, mode)
    if not level.boxes:
        return
    yield _view(where, None, with_tabs(fold_rows(model, level), tabs))
    if mode is _GROUPS:
        return
    for note in level.strips:
        shut = fold_level(model, level.unit, level.opened, fold=level.folded, strip=note.strip)
        ref = OverviewRef(kind=OverviewRefKind.ITEM, item=note.strip)
        yield _view(where, ref, with_tabs(fold_rows(model, shut), tabs))


def _folded(model: Model, unit: Id[Any], tabs: Tabs) -> Iterator[ViewRows]:
    """The groups view of `unit`, its all-devices view, each group and the strips box opened."""
    folded = fold_level(model, unit)
    views = partial(_fold_views, model, tabs=tabs)
    if not folded.folded:
        yield from views(folded, mode=_SEE_THROUGH)
        return
    yield from views(folded, mode=_GROUPS)
    yield from views(fold_level(model, unit, fold=False), mode=_SEE_THROUGH)
    for box in folded.boxes:
        if box.key.kind in _LEVELS:
            yield from views(fold_level(model, unit, box.key), mode=_SEE_THROUGH)


def overview_view_rows(model: Model, unit: Id[Unit] | None) -> tuple[ViewRows, ...]:
    """The views of `unit`'s level (`None`: the system), each with its boxes and lines.

    The plain level, each of its strips opened, and for a unit its folded levels: the groups, the
    all-devices level and each group. A fold is never a view of its own. A level with no box has
    no view.
    """
    tabs = tab_rows(model, unit)
    found = list(_plain(model, unit, tabs))
    if unit is not None:
        found.extend(_folded(model, unit, tabs))
    return tuple(found)
