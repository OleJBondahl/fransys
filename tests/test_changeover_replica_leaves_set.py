"""Layout-0076 for a terminal beside a changeover's throw (S20, 4b6c): a terminal never stands as a
host cell in another top-level drawing set.

The fixture is `field_cases/test_changeover_throws_to_two_strips.py`: poles 3 and 4 of changeover
-K1 at CAB, each throw wired to its own terminal of the strips -X01 and -X02 at FIELD. Built with no
`Unit`, the terminals belong to +FIELD's drawing set, so -K1's throws 32, 34, 42 and 44 end in C21
off stubs and the terminals stand in +FIELD's drawing with their stubs back. Built inside a `Unit`
the whole circuit is one drawing set (layout-0081), so the terminals stay host cells under -K1's
throws and no throw ends in a stub.

Before the guard `chains._attach` placed the terminals under -K1's throws in either case, so the
no-unit page drew them in +CAB's drawing, a drawing set that is not theirs.
"""

import importlib.util
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

from fransys_layout.engines.schematic import engine
from fransys_layout.engines.schematic.engine import stage_results
from fransys_model.vocab.tables import functions, ports

_FIELD_CASE = (
    Path(__file__).resolve().parent / "field_cases" / "test_changeover_throws_to_two_strips.py"
)
_spec = importlib.util.spec_from_file_location("_changeover_field_case_replica", _FIELD_CASE)
assert _spec is not None
assert _spec.loader is not None
_field_case = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_field_case)

_THROWS = {"32", "34", "42", "44"}


def _laid_out(tmp: Path, *, in_unit: bool) -> tuple[Any, Any]:
    """The field case built, its model and the engine's layout."""
    captured: list[Any] = []

    def recording_results(model: Any, inputs: Any) -> Any:
        results, findings = stage_results(model, inputs)
        captured.append(results.layout)
        return results, findings

    with mock.patch.object(engine, "stage_results", recording_results):
        model = _field_case._build(tmp, in_unit=in_unit).model
    return model, captured[-1]


class _Page:
    """What the tests read of one build: the sets of K1 and of the strip terminals."""

    def __init__(self, model: Any, layout: Any) -> None:
        keys = {fid: fn.key for fid, fn in functions(model).items()}
        self.layout = layout
        self.k1 = {fid for fid, key in keys.items() if "K1" in key}
        self.terminals = {fid for fid, key in keys.items() if {"X01", "X02"} & set(key)}
        names = {pid: (port.function, port.name) for pid, port in ports(model).items()}
        self.throw_stubs = {
            names[m.port][1]
            for m in layout.markers
            if names[m.port][0] in self.k1 and names[m.port][1] in _THROWS
        }

    def sets_of(self, group: set[Any]) -> set[int]:
        return {one.drawing_set for one in self.layout.placed if one.function in group}


@pytest.fixture(scope="module")
def nounit(tmp_path_factory) -> _Page:
    return _Page(*_laid_out(tmp_path_factory.mktemp("nounit"), in_unit=False))


@pytest.fixture(scope="module")
def inunit(tmp_path_factory) -> _Page:
    return _Page(*_laid_out(tmp_path_factory.mktemp("inunit"), in_unit=True))


def test_without_a_unit_the_terminals_stand_in_their_own_drawing_and_k1s_throws_end_in_stubs(
    nounit: _Page,
) -> None:
    """The terminals are placed, none in K1's drawing set, and all four throws end in a stub."""
    # UNDO: stages/chains.py `_attach`: drop the `_leaves_its_set` guard; the terminals stand
    #     as host cells in K1's drawing set and no throw ends in a stub
    assert nounit.terminals
    assert nounit.k1
    assert nounit.sets_of(nounit.terminals)
    assert not nounit.sets_of(nounit.terminals) & nounit.sets_of(nounit.k1)
    assert nounit.throw_stubs == _THROWS


def test_in_a_unit_the_terminals_stay_in_k1s_drawing_with_no_stub_on_a_throw(
    inunit: _Page,
) -> None:
    """A unit is one drawing set: the terminals share K1's, and no throw port carries a marker."""
    assert inunit.terminals
    assert inunit.k1
    assert inunit.sets_of(inunit.terminals) == inunit.sets_of(inunit.k1)
    assert len(inunit.sets_of(inunit.k1)) == 1
    assert inunit.throw_stubs == set()
