"""S16: on real layouts, the texts change each page's room alone, and every run fits that room.

`references` decides a page's joined runs on the page as `place` stacks it before any text
exists (`place.page_stack`, S12). `place` then stacks the page with its reference and stub texts
(`texts`), whose room at a column's end is the page's margin (S16, Room's N or S call). Each
case's build records every `place` call of the engine (`pagerun.place`, every attempt), with the
page as `references` read it and as `place` stacks it with the texts. Two claims: the texts
change `room` alone, never a port's row or offset, a column's height or its last row; and every
joined run fits the final room (`join_y`), since `place` never refuses a run (S12) and a run
that stopped fitting would show only as a finding.

The cases: the goldens (the cabinet on the house sheet and on its 158 mm sheet), the S12
joining fixtures (a feed fanning to three breakers, the same breakers daisy-chained, a strip of
8 terminals wired in a chain) and the D9 coil hub (`tests/test_dd_gap_rules.py`: `K1:A1` and
`K2:A1` joined at row 0 facing N, and `K1:A1` a star reference listing K3). The goldens join
no run today (S12's test): they carry the first claim, and stay among the second's cases so a
run they come to join is checked too. The example and the field cases join no run either;
every engine run of the layout and root suites, and the example's, was measured on 2026-09-27
with this recorder instead (the hand-back of step 5's 2b-3). Each case builds once per module
(`_pages`).
"""

from dataclasses import dataclass, replace
from functools import cache
from typing import TYPE_CHECKING, Any
from unittest import mock

import pytest
from dd_chain_fixtures import build, design, terminal_chain, three_breakers
from layout_cabinet import build_cabinet
from narrow_cabinet import narrow_model

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.stages import pagerun
from fransys_layout.stages.place import page_stack, place
from fransys_layout.stages.stacking import JoinedRun, JoinEnd, PageStack, join_y
from fransys_model.kernel import Model, freeze

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True)
class _Page:
    """One `place` call: its joined runs, the page `references` read and the page `place` stacks."""

    joins: tuple[JoinedRun, ...]
    decided: PageStack
    final: PageStack


def _laid_out(model: Model) -> None:
    stage_results(model, read_inputs(model))


def _coil_hub() -> None:
    """Relays K1..K3, the coils' A1 wired K1-K2 and K1-K3: hub K1 lists K3, laid out."""
    parts, d = design()
    c, g = d.location("C1", "Cabinet"), d.group("G1", "Group")
    wire = d.wiring(colour="BU", gauge="0.5")
    coil = {
        tag: d.item("DEMO-RLY-2CO-24", tag=tag, name=tag.lower(), at=c, group=g).fn("coil")["A1"]
        for tag in ("K1", "K2", "K3")
    }
    wire(coil["K1"], coil["K2"])
    wire(coil["K1"], coil["K3"])
    build(parts, d)


_CASES: dict[str, Callable[[], Any]] = {
    "cabinet": lambda: _laid_out(freeze(build_cabinet())),
    "cabinet_narrow": lambda: _laid_out(narrow_model(158)),
    "feed_fanning": lambda: three_breakers(daisy=False),
    "daisy_chain": lambda: three_breakers(daisy=True),
    "terminal_chain": lambda: terminal_chain(8),
    "coil_hub": _coil_hub,
}
_JOINING = ("feed_fanning", "daisy_chain", "terminal_chain", "coil_hub")


@cache
def _pages(case: str) -> tuple[_Page, ...]:
    """Every `place` call of `case`'s build, recorded (`_Page`)."""
    pages = []

    def recording(plan: Any, columns: Any, drawn: Any, stacking: Any, joins: Any) -> Any:
        pages.append(
            _Page(
                joins=joins,
                decided=page_stack(plan, columns, drawn, replace(stacking, texts=None)),
                final=page_stack(plan, columns, drawn, stacking),
            )
        )
        return place(plan, columns, drawn, stacking, joins)

    with mock.patch.object(pagerun, "place", recording):
        _CASES[case]()
    return tuple(pages)


def _ends(run: JoinedRun, stack: PageStack) -> tuple[JoinEnd, ...]:
    """`run`'s ends as `references` reads them off `stack` (`joins.port_spots`)."""
    return tuple(
        JoinEnd(
            port=end.port,
            row=stack.ports[end.column, end.port].row,
            offset=stack.ports[end.column, end.port].offset,
            height=stack.heights[end.column],
        )
        for end in run.ends
    )


@pytest.mark.parametrize("case", sorted(_CASES))
def test_the_texts_change_each_pages_room_alone(case: str) -> None:
    """Every page stacks its ports and columns as `references` read them; its room can shrink."""
    # UNDO: stages/place.py `_text_room`, first rows: `boxes += _owned(...)` -> grow the cell by
    #     them instead (`cell.geometry = grow_keepout(cell.geometry, owned)` when it owns any):
    #     the cabinet's first rows that own a text then stand deeper below the top
    pages = _pages(case)
    assert pages
    for page in pages:
        assert page.final.ports == page.decided.ports
        assert page.final.heights == page.decided.heights
        assert page.final.last == page.decided.last
        assert page.final.room <= page.decided.room


def test_the_cabinets_texts_shrink_a_pages_room() -> None:
    """Premise of the claims above: a pushed first-row text shrinks a cabinet page's room."""
    assert any(page.final.room < page.decided.room for page in _pages("cabinet"))


@pytest.mark.parametrize("case", sorted(_CASES))
def test_every_joined_run_fits_the_final_room(case: str) -> None:
    """`join_y` puts every run on one y in the room `place` places it in; the fixtures join."""
    # UNDO: stages/place.py `_text_room`: `return snap_up(lift), snap_up(sink)` -> add 1000 G
    #     to the sink when `texts` is given (margin added after the decision): the runs on
    #     pages with texts (the feed fanning's, the coil hub's) no longer fit
    runs = [(run, page.final) for page in _pages(case) for run in page.joins]
    assert [run for run, final in runs if join_y(_ends(run, final), final.room) is None] == []
    if case in _JOINING:
        assert runs
