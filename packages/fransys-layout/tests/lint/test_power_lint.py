"""D5 step 6: the lint counts a power symbol as a draw, and a power end takes no `#n` digit.

On the invented plant of `power_fixture` (eleven power ends on four pages) every net member is
covered by nothing but its power end. Dropping the end must name the port; keeping it must not.
"""

import importlib
from dataclasses import replace
from typing import TYPE_CHECKING

from power_fixture import power_model, power_run

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.lint import check_members, check_nowhere
from fransys_layout.lint.codes import CONNECTION_DRAWN_TWICE, CONNECTION_NOT_DRAWN
from fransys_layout.stages.types import NetGroup, Role

if TYPE_CHECKING:
    import pytest

_LINT = (CONNECTION_NOT_DRAWN, CONNECTION_DRAWN_TWICE)


def _without_symbols(layout):
    return replace(layout, markers=tuple(one for one in layout.markers if not one.symbol))


def _rail_group() -> NetGroup:
    """V3: the rail nets leave `inputs.net_groups`; one group of the rail-end ports stands in."""
    _, inputs, _, _ = power_run()
    ends = inputs.rail_ends
    return NetGroup(
        net=ends[0].connection,
        physical_net=ends[0].connection,
        role=Role.POWER,
        ports=tuple(one.ref for one in ends),
    )


def _coverage(layout) -> list:
    _, inputs, results, _ = power_run()
    groups = (*inputs.net_groups, _rail_group())
    return [
        *check_members(layout, inputs.connections, groups, results.drawn),
        *check_nowhere(layout, inputs.connections, groups, results.drawn),
    ]


def test_a_power_end_covers_its_port_for_the_member_check() -> None:
    """UNDO: in `check_members` read only `layout.routes` (drop the markers): every port fires."""
    _, _, results, _ = power_run()
    assert [one for one in results.layout.markers if one.symbol]
    assert _coverage(results.layout) == []


def test_dropping_the_power_ends_names_each_port_not_drawn() -> None:
    """The member check and the nowhere guard both fire once the symbols are gone.

    V3: the ports come from `rail_ends` (no conductor is drawn), grouped by `_rail_group`.

    UNDO: in `check_members` skip a marker with `symbol` set: this test passes, the one above fails.
    """
    _, _, results, _ = power_run()
    ports = {one.port for one in results.layout.markers if one.symbol}
    found = _coverage(_without_symbols(results.layout))
    assert {one.code for one in found} == {CONNECTION_NOT_DRAWN}
    assert ports <= {handle for one in found for handle in one.subjects}


def test_the_whole_run_has_no_connection_finding_with_the_symbols() -> None:
    """UNDO: in `link_markers` (stages) drop the power markers: the next test's finding appears."""
    _, _, _, findings = power_run()
    assert [one for one in findings if one.code in _LINT] == []


def test_a_run_draws_a_power_symbol_at_each_rail_end() -> None:
    """V3: the rail wires are not drawn, so each rail-end pin is covered by its symbol alone.

    The engine's lint sees no net group for a rail net, so this is the check that a pin keeps
    its symbol.
    """
    _, inputs, results, _ = power_run()
    drawn = {one.port for one in results.layout.markers if one.symbol}
    assert inputs.rail_ends
    assert {one.ref.port for one in inputs.rail_ends} <= drawn


def test_a_power_end_consumes_no_reference_digit(monkeypatch: pytest.MonkeyPatch) -> None:
    """S4: the digit count sees no flagged end, so a power-only set keeps the floor digits.

    UNDO: in `references/__init__.py` drop `if not one.symbol` from the `set_digits` call.
    """
    module = importlib.import_module("fransys_layout.stages.references")
    seen: list = []
    real = module.set_digits

    def spy(markers, plans, location_paths):
        markers = tuple(markers)
        seen.extend(markers)
        return real(markers, plans, location_paths)

    monkeypatch.setattr(module, "set_digits", spy)
    model = power_model(60)
    results, _ = stage_results(model, read_inputs(model))
    assert [one for one in results.layout.markers if one.symbol]
    assert seen == []
