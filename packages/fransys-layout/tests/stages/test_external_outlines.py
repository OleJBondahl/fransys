"""`external_outlines`: a dashed outline per run of an external item, one note per item and page.

Fakes stand for the placed functions; `page_taken` is replaced by an empty keep-out list, since
these tests read the runs and the note count, not the note's place.

Can-fail (one mutation of `stages/external_outlines.py`):
- one run for all members: `for run in member_runs(members, placed)` -> `for run in [members]`
  (the replica test: a replica in another column is its own run).
- a note per run: move the note block inside the run loop (the note count test).
"""

from types import SimpleNamespace
from typing import Any, cast

import pytest

from fransys_layout.geometry import Box
from fransys_layout.stages import external_outlines as module
from fransys_layout.stages.external_outlines import ExternalInputs, external_outlines

_BODY = Box(x=0, y=0, width=4, height=8)


def _one(function: str, column: str, x: int, y: int = 20) -> Any:
    return SimpleNamespace(
        function=function,
        column=column,
        at=SimpleNamespace(x=x, y=y),
        geometry=SimpleNamespace(body=_BODY),
    )


def _run(placed: list[Any], external: set[str]) -> tuple[list[Any], tuple[Any, ...]]:
    spec_of = {one.function: SimpleNamespace(item=one.function[0], ports=()) for one in placed}
    inputs = ExternalInputs(
        spec_of=cast("Any", spec_of),
        root_of=cast("Any", {name: name for name in external}),
        text_height=6,
        note="by others",
    )
    plan = SimpleNamespace(drawing_set=0, number=1)
    return external_outlines((plan,), [(tuple(placed), ())], (), inputs)


@pytest.fixture(autouse=True)
def _no_keepouts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "page_taken", lambda *_: [])


def test_a_column_of_an_external_item_is_one_outline_with_one_note() -> None:
    placed = [_one("e1", "c", 20, 20), _one("e2", "c", 20, 40), _one("k", "d", 60)]
    pages, outlines = _run(placed, {"e"})
    assert len(outlines) == 1
    assert [label.slot for label in pages[0][1]] == ["external_note"]


def test_a_replica_in_another_column_behind_a_foreign_column_is_its_own_run() -> None:
    placed = [_one("e1", "a", 20), _one("k", "x", 60), _one("e2", "b", 100)]
    pages, outlines = _run(placed, {"e"})
    assert len(outlines) == 2
    assert outlines[0].box.x < outlines[1].box.x
    assert len(pages[0][1]) == 1  # one note for the item, not one per run


def test_a_symbol_of_no_external_item_gets_no_outline() -> None:
    pages, outlines = _run([_one("k", "x", 60)], {"e"})
    assert outlines == ()
    assert pages[0][1] == ()
