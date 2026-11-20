"""Shared by the TEXT-KEEPS ship tests: a build's Drawings with each tag beside the annex that holds it."""

from typing import TYPE_CHECKING, Any

import pytest
from fransys_el import draw_layout
from fransys_el.placement_tables import is_table_spot

if TYPE_CHECKING:
    from collections.abc import Callable


def tags_with_annexes(run: Callable[[], Any]) -> tuple[Any, list[tuple[Any, Any, Any]]]:
    """`run()` returns Drawings; give them and each tag as (page, TAG text, annex), taken while it builds."""
    seen: list[tuple[Any, Any, Any]] = []
    labels = draw_layout._labels

    def spy(w: Any, keys: Any) -> Any:
        got = labels(w, keys)
        annexes = (a for a in w.layout.annotations.annexes if not is_table_spot(a.spot))
        seen.extend((page, text, a) for a, (page, text) in zip(annexes, got, strict=True))
        return got

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(draw_layout, "_labels", spy)
        return run(), seen


def ink_boxes(drawings: Any, seen: list[tuple[Any, Any, Any]]) -> list[tuple[Any, Any]]:
    """Each tag's and its WHERE lines' ink box beside the box of the annex that holds them."""
    return [(w.box, a.box) for p, t, a in seen for w in (t, *(w for w in drawings[p].texts if w.kind == "WHERE" and w.owner == t.owner))]
