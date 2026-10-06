"""S20 M9: room for a vertical box between two ports stacked along a stub.

Function `n` is the through symbol (`samples.drawn`): port `10n + 1` at `in` on top of its
keep-out, facing N; port `10n + 2` at `out` at its bottom, facing S. One column holds
function 1 over function 2, so port 12 (S) stands straight above port 21 (N) on one x. The
texts are built through `page_texts`, as the engine builds them.
"""

from dataclasses import replace

from samples import PROFILE, SHEET, column, drawn, hid, page_plan

from fransys_layout.stages.page_stacking import PageStacking
from fransys_layout.stages.place import _reference_band, page_stack
from fransys_layout.stages.references.marker_boxes import reference_size
from fransys_layout.stages.references.types import MarkerDecision
from fransys_layout.stages.texts.stand import page_texts
from fransys_layout.stages.types import MarkerSide

_TIGHT = replace(PROFILE, row_gap=8, row_spacing=8)  # the stacking leaves 16 G between ports
_PLAN = page_plan(("a",))
_COLUMNS = (column("a", (1, 2)),)
_FUNCTIONS = (drawn(1), drawn(2))
_KEY = _PLAN.columns[0].column


def _reference(port: int) -> MarkerDecision:
    """A one-line star reference at port `port` (of function `port // 10`)."""
    return MarkerDecision(
        connection=hid("conductor", port),
        function=hid("function", port // 10),
        port=hid("port", port),
        side=MarkerSide.OWNER,
        drawing_set=1,
        page=1,
        star="ref",
        lines=1,
        size=reference_size(SHEET, PROFILE, lines=1),
        partner=hid("port", 91),
        partner_set=1,
        partner_page=2,
        out=0,
    )


def _apart(*texts: MarkerDecision) -> int:
    """How far port 21 stands below port 12 as `place` stacks the column with `texts`."""
    reserved = page_texts(texts, frozenset(), sheet=SHEET, profile=PROFILE)[1, 1] if texts else None
    stacking = PageStacking(profile=_TIGHT, sheet=SHEET, texts=reserved)
    stack = page_stack(_PLAN, _COLUMNS, _FUNCTIONS, stacking)
    return stack.ports[_KEY, hid("port", 21)].offset - stack.ports[_KEY, hid("port", 12)].offset


def test_two_stacked_ends_hold_a_vertical_box_between_them() -> None:
    """A reference at the upper port: the two ports stand at least the reference band apart.
    With no text, or a text at neither port, the stacking is as it was."""
    # UNDO: stages/place.py `_stacked`: drop the `make_room(...)` call (no spacing rule)
    band = _reference_band(SHEET, _TIGHT)
    bare = _apart()
    assert bare < band  # premise: the house gap alone leaves no room for the box
    assert _apart(_reference(12)) >= band
    assert _apart(_reference(21)) >= band  # a text at the lower port asks the same room
    assert _apart(_reference(12), _reference(21)) >= 2 * band  # a text at each: a band each
    assert _apart(_reference(11)) == bare  # a text at neither of the two ports asks none
