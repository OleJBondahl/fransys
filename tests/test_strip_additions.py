"""STRIP-ADDITIONS (decision author-0022): `Terminal.limits` (TL), a partly bridged run (PB), a run
with no size (RS) and a strip or run as a wire or core end (RE).

TL: a unit rates a terminal boundary as it rates a device function; a circuit above the rating
gives RATING_VOLTAGE_BELOW_CIRCUIT. PB: `run(label, n, bridged=(first, last))` jumpers terminals
`first` to `last` only, and the listing's jumper group follows. RS: `run(label, bridged=True)`
grows with each connection. RE: `d.wire` and `W1.core` take the next free terminal. Demo parts only.

Can-fail probes (`just probe`): a `Terminal.limits` that writes nothing fails the TL test;
bridging the whole run for any pair fails the PB test; bridging only terminals 1-2 of a growing
run fails the RS test; a wire end that always takes terminal 1 fails the RE test.
"""

from decimal import Decimal
from typing import NamedTuple

import fransys as fr
import pytest
from fransys.colours import BU
from fransys_author import AuthorError

from fransys_model.vocab import ConductorKind, tables

_RATED = fr.derive.Rating(voltage_dc_v=Decimal(12))


class _Io(NamedTuple):
    X1: fr.TerminalStrip


@fr.unit("demo-feed", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _feed(d: fr.Design) -> _Io:
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 2, interface=True)
    x1[1].limits(rating=_RATED)
    return _Io(x1)


def test_a_terminal_boundary_rating_below_the_circuit_is_found() -> None:
    d = fr.design("demo_parts", place="HALL")
    d.location("HALL", "Pump hall")
    psu = d.device("T1", "DEMO-PSU-24")
    d.dc_supply("S", psu)
    io = d.add(_feed, "U1")
    d.wire(psu.output["+"], io.X1[1].outer, wire=(BU, 0.5))
    d.wire(psu.output["-"], io.X1[2].outer, wire=(BU, 0.5))
    found = [f for f in fr.build(d).findings if f.code == "RATING_VOLTAGE_BELOW_CIRCUIT"]
    assert len(found) == 1
    assert "boundary rating of unit" in found[0].message


def _io_run(bridged: object):
    d = fr.design("demo_parts", place="HALL")
    d.location("HALL", "Pump hall")
    strip = d.terminal_strip("X1", "DEMO-TB-2.5")
    run = strip.run("IO", 10, bridged=bridged)  # ty: ignore[invalid-argument-type] -- the refusals pass bad pairs
    return d, strip, run


def test_a_pair_bridges_its_terminals_only_and_fills_the_jumper_group() -> None:
    d, _strip, _run = _io_run((7, 10))
    model = fr.build(d).model
    jumpers = [c for c in tables.conductors(model).values() if c.kind is ConductorKind.JUMPER]
    pairs = sorted(
        tuple(sorted(tables.ports(model)[end].key[3] for end in (c.a, c.b))) for c in jumpers
    )
    assert pairs == [("10", "9"), ("7", "8"), ("8", "9")]
    (strip_id,) = fr.derive.terminal_strips(model)
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
    found = [
        tuple(sorted(ports[end].key[3] for end in (c.a, c.b)))
        for c in tables.conductors(model).values()
        if c.kind is ConductorKind.JUMPER
    ]
    return sorted(found)


def _groups(model) -> dict[int, int | None]:
    (strip_id,) = fr.derive.terminal_strips(model)
    return {row.index: row.jumper_group for row in fr.derive.terminal_rows(model, strip_id)}


def _sizeless():
    d = fr.design("demo_parts", place="HALL")
    d.location("HALL", "Pump hall")
    feed = d.terminal_strip("X1", "DEMO-TB-2.5").run("24V", bridged=True)
    return d, feed


def test_a_sizeless_run_grows_with_each_series_and_bridges_the_last_two() -> None:
    d, feed = _sizeless()
    for tag in ("S1", "S2", "S3"):
        d.series(feed, d.device(tag, "DEMO-MCB-C6").element, wire=(BU, 0.5))
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
    ends = [
        ports[end]
        for c in tables.conductors(model).values()
        if c.kind is kind
        for end in (c.a, c.b)
    ]
    return sorted((p.key[3], p.role.value) for p in ends if p.key[:2] == ("X1", "terminal"))


def test_a_run_as_a_wire_end_takes_the_next_terminal_each_time_and_a_core_the_outer_side() -> None:
    d, feed = _sizeless()
    lamp = d.device("H1", "DEMO-LAMP-24")
    d.wire(feed, lamp["1"], wire=(BU, 0.5))
    d.wire(feed, lamp["2"], wire=(BU, 0.5))
    d.cable("W1", "DEMO-CBL-4G1.5", length_m=2).core(1, feed, lamp["1"])
    model = fr.build(d).model
    assert _landed(model, ConductorKind.WIRE) == [("1", "internal"), ("2", "internal")]
    assert _landed(model, ConductorKind.CORE) == [("3", "external")]
    assert _jumpers(model) == [("1", "2"), ("2", "3")]
