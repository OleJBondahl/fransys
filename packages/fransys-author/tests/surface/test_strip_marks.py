"""Strip boundary marks: a run's `interface=`, a strip's tuple, and their refusals (UNIT-MARKS)."""

from typing import TYPE_CHECKING, Any, NamedTuple

import pytest
from fransys_author import AuthorError
from fransys_author.surface import Design, design, unit

from fransys_model.checks.units import check_units
from fransys_model.derive.numbering_pins import name_findings
from fransys_model.kernel import freeze, merge
from fransys_model.vocab import RailGroup

if TYPE_CHECKING:
    from collections.abc import Callable

from series_parts import pair_library

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
    d.series(io.X2[1], lamp.lamp["1"], wire=("BK", 1.5))
    d.series(io.X2[2], lamp.lamp["2"], wire=("BK", 1.5))
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

    return sum(1 for r in d.draft().records() if isinstance(r, Conductor) and r.kind is ConductorKind.JUMPER)


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
    d.series(io.X2[number], lamp.lamp["1"], wire=("BK", 1.5))
    return _codes(d)


def test_unused_on_a_strip_names_only_its_named_terminals() -> None:
    assert "UNUSED_CONTRADICTED" in _codes_wiring_terminal(1)
    assert "UNUSED_CONTRADICTED" not in _codes_wiring_terminal(3)


def _rails(d: Design) -> list[RailGroup]:
    return [r for r in d.draft().records() if isinstance(r, RailGroup)]


def test_rail_flags_one_group_per_flagged_run_and_none_for_an_unflagged_one() -> None:
    """Can-fail: dropping the `rail_numbers` call in `Run.__init__` leaves no group and fails the first assert."""
    d = design(pair_library())
    x = d.terminal_strip("X4", "DEMO-TB-2.5", 8)
    x.run("L1", 3, bridged=True, rail=True)
    x.run("L2", 3, bridged=True)
    x.run("L3", 1, rail=True)
    sizes = sorted(len(r.terminals) for r in _rails(d))
    assert sizes == [1, 3]


def test_rail_on_a_strip_flags_its_one_bridged_range() -> None:
    d = design(pair_library())
    d.terminal_strip("X4", "DEMO-TB-2.5", 6, bridged=(2, 4), rail=True)
    (group,) = _rails(d)
    assert len(group.terminals) == 3


def test_rail_on_several_bridged_ranges_is_refused_with_the_fix() -> None:
    with pytest.raises(AuthorError, match=r"flag each group with run\(\.\.\., rail=True\)"):
        design(pair_library()).terminal_strip("X4", "DEMO-TB-2.5", 6, bridged=((1, 2), (4, 5)), rail=True)


def test_rail_on_an_unbridged_group_of_more_than_one_terminal_is_refused() -> None:
    with pytest.raises(AuthorError, match="a rail is one bridged group"):
        design(pair_library()).terminal_strip("X4", "DEMO-TB-2.5", 3).run("L1", 2, rail=True)


def test_rail_on_a_run_with_no_count_is_refused() -> None:
    with pytest.raises(AuthorError, match="give it a count"):
        design(pair_library()).terminal_strip("X4", "DEMO-TB-2.5", 3).run("L1", bridged=True, rail=True)
