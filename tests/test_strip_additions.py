"""Decision author-0022: a partly bridged run, a run with no size and a strip or run as a wire or core end."""

from typing import Any, NamedTuple

import fransys as fr
import pytest
from fransys.colours import BU
from fransys_author import AuthorError

from fransys_model.derive import stub_far, terminal_strips
from fransys_model.vocab import ConductorKind, tables


class _Io(NamedTuple):
    X1: fr.TerminalStrip


@fr.unit("demo-feed", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _feed(d: fr.Design) -> _Io:
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 2, interface=True)
    return _Io(x1)


def _io_run(bridged: Any):
    d = fr.design("demo_parts", place="HALL")
    d.location("HALL", "Pump hall")
    strip = d.terminal_strip("X1", "DEMO-TB-2.5")
    run = strip.run("IO", 10, bridged=bridged)
    return d, strip, run


def test_a_pair_bridges_its_terminals_only_and_fills_the_jumper_group() -> None:
    d, _strip, _run = _io_run((7, 10))
    model = fr.build(d).model
    jumpers = [c for c in tables.conductors(model).values() if c.kind is ConductorKind.JUMPER]
    pairs = sorted(tuple(sorted(tables.ports(model)[end].key[3] for end in (c.a, c.b))) for c in jumpers)
    assert pairs == [("10", "9"), ("7", "8"), ("8", "9")]
    (strip_id,) = terminal_strips(model)
    rows = fr.derive.terminal_rows(model, strip_id)
    groups = {row.index: row.jumper_group for row in rows}
    assert {n for n, g in groups.items() if g is not None} == {7, 8, 9, 10}
    assert {groups[n] for n in range(7, 11)} == {1}


@pytest.mark.parametrize("pair", [(0, 3), (7, 11), (8, 7), (3, 3)])
def test_a_pair_outside_the_run_or_out_of_order_raises(pair: tuple[int, int]) -> None:
    with pytest.raises(AuthorError, match=r"needs 1 <= first < last <= 10"):
        _io_run(pair)


def _jumpers(model) -> list[tuple[str, ...]]:
    ports = tables.ports(model)
    found = [tuple(sorted(ports[end].key[3] for end in (c.a, c.b))) for c in tables.conductors(model).values() if c.kind is ConductorKind.JUMPER]
    return sorted(found)


def _groups(model) -> dict[int, int | None]:
    (strip_id,) = terminal_strips(model)
    return {row.index: row.jumper_group for row in fr.derive.terminal_rows(model, strip_id)}


def _sizeless():
    d = fr.design("demo_parts", place="HALL")
    d.location("HALL", "Pump hall")
    feed = d.terminal_strip("X1", "DEMO-TB-2.5").run("24V", bridged=True)
    return d, feed


def test_a_sizeless_run_grows_with_each_series_and_bridges_the_last_two() -> None:
    d, feed = _sizeless()
    psu = d.device("T1", "DEMO-PSU-24")
    for tag in ("S1", "S2", "S3"):
        breaker = d.device(tag, "DEMO-MCB-C6")
        d.series(feed, breaker.element, wire=(BU, 0.5))
        d.series(breaker["2"], psu.output["-"], wire=(BU, 0.5))
    model = fr.build(d).model
    assert _jumpers(model) == [("1", "2"), ("2", "3")]
    assert _groups(model) == {1: 1, 2: 1, 3: 1}


def test_a_sizeless_run_names_only_a_terminal_already_taken() -> None:
    d, feed = _sizeless()
    for tag in ("S1", "S2"):
        d.series(feed, d.device(tag, "DEMO-MCB-C6").element, wire=(BU, 0.5))
    assert feed[2] is not None
    with pytest.raises(AuthorError, match="give the run a size"):
        feed[3]


def test_a_sizeless_run_that_is_not_bridged_or_has_a_pair_raises() -> None:
    strip = fr.design("demo_parts", place="HALL").terminal_strip("X1", "DEMO-TB-2.5")
    with pytest.raises(AuthorError, match="a run with no size is bridged=True"):
        strip.run("A")
    with pytest.raises(AuthorError, match="a run with no size is bridged=True"):
        strip.run("B", bridged=(1, 2))


def _landed(model, kind) -> list[tuple[str, str]]:
    """(terminal number, port role) of every strip-terminal port a `kind` conductor lands on."""
    ports = tables.ports(model)
    ends = [ports[end] for c in tables.conductors(model).values() if c.kind is kind for end in (c.a, c.b)]
    return sorted((p.key[3], p.boundary.value) for p in ends if p.key[:2] == ("X1", "terminal"))


def test_a_run_as_a_wire_end_takes_the_next_terminal_each_time_and_a_core_the_outer_side() -> None:
    d, feed = _sizeless()
    lamp = d.device("H1", "DEMO-LAMP-24")
    d.series(feed, lamp["1"], wire=(BU, 0.5))
    d.series(feed, lamp["2"], wire=(BU, 0.5))
    d.cable("W1", "DEMO-CBL-4G1.5", length_m=2).core(1, feed, lamp["1"])
    model = fr.build(d).model
    assert _landed(model, ConductorKind.WIRE) == [("1", "internal"), ("2", "internal")]
    assert _landed(model, ConductorKind.CORE) == [("3", "external")]
    assert _jumpers(model) == [("1", "2"), ("2", "3")]


def test_every_bridged_terminal_of_a_rail_group_shows_its_bridge_in_the_terminal_table() -> None:
    """RAIL-FLAG (R885): a bridge is no drawn wire; its terminals share one `jumper_group` in the table."""
    d = fr.design("demo_parts", place="HALL")
    d.location("HALL", "Pump hall")
    rail = d.terminal_strip("X1", "DEMO-TB-2.5").run("24V", 4, bridged=True, rail=True)
    psu = d.device("T1", "DEMO-PSU-24")
    d.dc_supply("S", psu)
    d.series(psu.output["+"], rail[1].outer, wire=(BU, 0.5))
    model = fr.build(d).model
    bridged = {tables.ports(model)[end].key[3] for c in tables.conductors(model).values() if c.kind is ConductorKind.JUMPER for end in (c.a, c.b)}
    assert bridged == {"1", "2", "3", "4"}
    groups = _groups(model)
    assert {groups[int(n)] for n in bridged} == {1}


def test_a_terminal_side_only_a_bridge_reaches_names_no_stub_far_end() -> None:
    """RAIL-FLAG (R885): a bridge is no wire, so its side takes no stub of the wire on the terminal's other side."""
    d, _strip, run = _io_run(bridged=True)
    psu = d.device("T1", "DEMO-PSU-24")
    d.series(psu.output["+"], run[1].outer, wire=(BU, 0.5))
    model = fr.build(d).model
    sides = [
        end
        for c in tables.conductors(model).values()
        if c.kind is ConductorKind.JUMPER
        for end in (c.a, c.b)
        if tables.ports(model)[end].key[3] == "1"
    ]
    assert sides
    assert all(stub_far(model, [end]) == () for end in sides)
