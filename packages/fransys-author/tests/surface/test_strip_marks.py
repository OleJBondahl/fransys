"""Strip boundary marks: a run's `interface=`, a strip's tuple, and their refusals (UNIT-MARKS)."""

from typing import TYPE_CHECKING, Any, NamedTuple

import pytest
from fransys_author import AuthorError
from fransys_author.surface import Design, design, unit

from fransys_model.checks.units import check_units
from fransys_model.derive.numbering_pins import name_findings
from fransys_model.kernel import freeze, merge

if TYPE_CHECKING:
    from collections.abc import Callable

from ..equivalence.series_parts import pair_library  # noqa: TID252 -- importlib mode puts tests/ on no path

_CONTAINER_BAD = {"BOUNDARY_UNCONNECTED", "UNIT_BOUNDARY_BYPASSED"}


class _Strip(NamedTuple):
    X2: Any


class _Nothing(NamedTuple):
    pass


def _unit_with(body: Callable[[Design], object]) -> Design:
    """A design with one unit `U1` whose body runs `body(unit_design)` when added."""

    @unit("demo-cab", revision=1, interface_version=1, date="d", text="t", by="XX")
    def cab(d: Design) -> _Nothing:
        body(d)
        return _Nothing()

    d = design(pair_library(), place="C1")
    d.add(cab, "U1")
    return d


def _codes(d: Design) -> set[str]:
    model = freeze(merge(pair_library(), d.draft()))
    return {f.code for f in name_findings(model, check_units(model))}


def test_a_run_marked_interface_makes_its_terminals_boundary() -> None:
    """A container's series to a run's terminals gives no boundary finding."""

    @unit("demo-cab", revision=1, interface_version=1, date="d", text="t", by="XX")
    def cab(d: Design) -> _Strip:
        x2 = d.terminal_strip("X2", "DEMO-TB-2.5")
        return _Strip(X2=x2.run("24V", 4, bridged=True, interface=True))

    d = design(pair_library(), place="C1")
    io = d.add(cab, "U1")
    lamp = d.device("H1", "DEMO-LAMP-24")
    d.detail.wire(io.X2[1], lamp.lamp["1"], wire=("BK", 1.5))
    d.detail.wire(io.X2[2], lamp.lamp["2"], wire=("BK", 1.5))
    assert not _codes(d) & {"UNIT_BOUNDARY_BYPASSED"}


def test_an_interface_index_past_the_count_names_the_range() -> None:
    with pytest.raises(AuthorError, match=r"1\.\.4"):
        _unit_with(lambda d: d.terminal_strip("X1", "DEMO-TB-2.5", 4, interface=(5,)))


def test_a_tuple_interface_without_a_count_names_the_fix() -> None:
    with pytest.raises(AuthorError, match="give the strip a count"):
        _unit_with(lambda d: d.terminal_strip("X1", "DEMO-TB-2.5", interface=(1,)))


def test_a_terminal_marked_by_both_the_strip_and_its_run_names_the_fix() -> None:
    def body(d: Design) -> None:
        x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4, interface=True)
        x1.run("24V", 4, interface=True)

    with pytest.raises(AuthorError, match="set it on the strip or on the run, not both"):
        _unit_with(body)


def test_a_bridged_range_past_the_count_names_the_range() -> None:
    with pytest.raises(AuthorError, match=r"needs 1 <= first < last <= 6"):
        design(pair_library()).terminal_strip("X4", "DEMO-TB-2.5", 6, bridged=(2, 7))


def test_a_bridged_range_whose_first_is_not_below_its_last_is_refused() -> None:
    with pytest.raises(AuthorError, match=r"needs 1 <= first < last <= 6"):
        design(pair_library()).terminal_strip("X4", "DEMO-TB-2.5", 6, bridged=(6, 2))


def test_overlapping_bridged_ranges_are_refused() -> None:
    with pytest.raises(AuthorError, match="give each terminal one range"):
        design(pair_library()).terminal_strip("X4", "DEMO-TB-2.5", 6, bridged=((2, 4), (3, 5)))


def test_bridged_on_a_strip_with_no_count_names_the_fix() -> None:
    with pytest.raises(AuthorError, match="give the strip a count"):
        design(pair_library()).terminal_strip("X4", "DEMO-TB-2.5", bridged=(1, 2))


def _jumper_count(d: Design) -> int:
    from fransys_model.vocab import Conductor, ConductorKind

    return sum(
        1
        for r in d.draft().records()
        if isinstance(r, Conductor) and r.kind is ConductorKind.JUMPER
    )


def test_bridged_true_on_a_strip_jumpers_every_adjacent_pair() -> None:
    d = design(pair_library())
    d.terminal_strip("X4", "DEMO-TB-2.5", 4, bridged=True)
    assert _jumper_count(d) == 3


def test_bridged_true_on_a_one_terminal_strip_is_refused_naming_the_range() -> None:
    with pytest.raises(AuthorError, match="needs a strip of at least 2 terminals"):
        design(pair_library()).terminal_strip("X4", "DEMO-TB-2.5", 1, bridged=True)


def test_two_bridged_ranges_make_two_separate_bridges() -> None:
    d = design(pair_library())
    d.terminal_strip("X4", "DEMO-TB-2.5", 6, bridged=((2, 3), (5, 6)))
    assert _jumper_count(d) == 2


def _codes_wiring_terminal(number: int) -> set[str]:
    """A unit whose strip says `unused=(1, 2)`, and a container wire to terminal `number`."""

    @unit("demo-cab", revision=1, interface_version=1, date="d", text="t", by="XX")
    def cab(d: Design) -> _Strip:
        return _Strip(X2=d.terminal_strip("X2", "DEMO-TB-2.5", 4, unused=(1, 2)))

    d = design(pair_library(), place="C1")
    io = d.add(cab, "U1")
    lamp = d.device("H1", "DEMO-LAMP-24")
    d.detail.wire(io.X2[number], lamp.lamp["1"], wire=("BK", 1.5))
    return _codes(d)


def test_unused_on_a_strip_names_only_its_named_terminals() -> None:
    assert "UNUSED_CONTRADICTED" in _codes_wiring_terminal(1)
    assert "UNUSED_CONTRADICTED" not in _codes_wiring_terminal(3)
