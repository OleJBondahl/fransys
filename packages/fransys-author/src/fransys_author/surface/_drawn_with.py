"""The `drawn_with=` keyword of the by-others item calls: one checker, one refusal text each (BY-OTHERS-DRAWN-WITH)."""

from typing import TYPE_CHECKING, Any, cast

from fransys_author._draft_view import draft_view
from fransys_author.errors import AuthorError
from fransys_author.surface._added import added_unit
from fransys_model.derive import drawn_with
lazy from fransys_author.design import Scope
lazy from fransys_model.vocab import Item as ModelItem
lazy from fransys_model.vocab import Unit as ModelUnit
lazy from fransys_model.vocab import UnitRelease

if TYPE_CHECKING:
    from fransys_model.kernel import Draft, Id


type UnitHandle = Scope | tuple[Any, ...]  # what `d.add(...)` returned for a unit: its result tuple, or a unit scope


def _unit_name(draft: Draft, unit: Id[ModelUnit]) -> str:
    """The name of the unit's release, as `d.unit(name, ...)` was given it."""
    release = cast("ModelUnit", draft.record_of(unit)).release
    return cast("UnitRelease", draft.record_of(release)).name


def _refuse_under_root(draft: Draft, parent: Id[ModelItem] | None, unit: Id[ModelUnit], call: str, label: str) -> None:
    """Raise `AuthorError` when the by-others root above `parent` already sets `drawn_with`: one root, one choice."""
    if parent is None:
        return
    chosen = drawn_with(draft_view(draft), parent)
    if chosen is not None:
        holder = cast("ModelItem", draft.record_of(parent)).tag
        fix = (
            f"remove drawn_with from -{label}; -{holder} already sets it"
            if chosen == unit
            else f"remove drawn_with from -{label} or set it on -{holder}"
        )
        msg = f"{call}: -{label} is under -{holder}, which is drawn with {_unit_name(draft, chosen)}; {fix}"
        raise AuthorError(msg)


def drawn_with_unit(
    engine: Scope,
    drawn_with: UnitHandle | None,
    *,
    external: bool,
    who: tuple[str, str],
    parent: Id[ModelItem] | None = None,
) -> Id[ModelUnit] | None:
    """The unit id `drawn_with` names, or an `AuthorError` with the fix: it needs external=True, a unit from d.unit, and no root that sets it."""
    if drawn_with is None:
        return None
    call, label = who
    unit = added_unit(drawn_with) or (drawn_with._unit if isinstance(drawn_with, Scope) else None)
    if unit is None:
        msg = f"{call}: drawn_with takes what d.add(...) returned for the unit, got {type(drawn_with).__name__}; pass that unit or remove drawn_with"
        raise AuthorError(msg)
    if not external:
        msg = f"{call}: drawn_with is for items supplied by others; remove it or add external=True"
        raise AuthorError(msg)
    _refuse_under_root(engine._design._draft, parent, unit, call, label)
    return unit
