"""The draft's records as a read-only view the model's facts accept (EL-7, spec M4)."""

import dataclasses
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fransys_model.kernel import Draft, Id, Record


@dataclasses.dataclass(frozen=True, slots=True)
class DraftView:
    """A snapshot of a `Draft` with the `tables` a fact reads; never a `Model`, hashed nowhere."""

    tables: frozendict[str, frozendict[Id[Any], Record]]


def draft_view(draft: Draft) -> DraftView:
    """The view of `draft` as it stands now; a later `add` is not in it."""
    return DraftView(draft.tables())
