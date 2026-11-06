"""Fact 5: a rail pin stands a power symbol with no wire; a wire or a signal pin never does."""
# NET_POTENTIAL_CONFLICT 1 per default-salt build set: refusal or induced finding, asserted through expect_codes.
# NET_SHORTED 1 per default-salt build set: refusal or induced finding, asserted through expect_codes.

from typing import TYPE_CHECKING, NamedTuple

import fransys as fr
import pytest
from _expected_codes import expect_codes
from fransys.colours import BU, GNYE

from fransys_model.checks.rails import check_rails
from fransys_model.derive import (
    conductor_ends,
    connected_ports,
    drawn_stands,
    function_scopes,
    is_bridge,
    is_pe_conductor,
    is_rail_terminal,
    terminal_items,
    terminal_rows,
    terminal_strips,
    wire_rows,
)
from fransys_model.derive.facts.conductor_facts import drawn_conductors
from fransys_model.derive.lookups import item_of_port
from fransys_model.derive.power import port_power_kind
from fransys_model.derive.stands import stands
from fransys_model.layout import PowerSymbol, layout_of
from fransys_model.vocab import PowerKind
from fransys_model.vocab.tables import conductors, functions, items, ports

if TYPE_CHECKING:
    from pathlib import Path

    from fransys_model.kernel import Id, Model
    from fransys_model.vocab import Port

_WIRE = (BU, 0.5)


class _Nothing(NamedTuple):
    pass


def _build() -> fr.BuildResult:
    """A 24 V PSU feeds three lamps; PE on lamps P4-P6 (three ports) and P12-P13 (two); a wire P10-P11; a second PSU wired to P8."""
    d = fr.design("demo_parts")
    with d.function("G", "Group"):
        psu = d.device("T1", "DEMO-PSU-24")
        lamps = [d.device(f"P{i}", "DEMO-LAMP-24") for i in range(1, 4)]
        earthed = [d.device(f"P{i}", "DEMO-LAMP-24") for i in (4, 5, 6)]
        pair = [d.device(f"P{i}", "DEMO-LAMP-24") for i in (12, 13)]
        signal = [d.device(f"P{i}", "DEMO-LAMP-24") for i in (10, 11)]
        psu2 = d.device("T2", "DEMO-PSU-24")
        lone = d.device("P8", "DEMO-LAMP-24")
    d.dc_supply("24VDC", psu, names=("P24", "P0"))
    for lamp in lamps:
        d.series(psu.output["+"], lamp[1], wire=_WIRE)
    for lamp in (*lamps, *earthed, *pair, *signal):
        d.series(psu.output["-"], lamp[2], wire=_WIRE)
    d.series(earthed[0][1], earthed[1][1], wire=(GNYE, 0.75))
    d.series(earthed[1][1], earthed[2][1], wire=(GNYE, 0.75))
    d.earth(earthed[0][1], earthed[1][1], earthed[2][1])
    d.series(pair[0][1], pair[1][1], wire=(GNYE, 0.75))
    d.earth(pair[0][1], pair[1][1])
    d.series(signal[0][1], signal[1][1], wire=_WIRE)
    d.dc_supply("SOLO", psu2, names=("SOLO_24", "SOLO_0"))
    d.series(psu2.output["+"], lone[1], wire=_WIRE)
    d.series(psu2.output["-"], lone[2], wire=_WIRE)
    return fr.build(d)


@pytest.fixture(scope="module")
def model() -> Model:
    return _build().model


def _port(model: Model, tag: str, name: str) -> Id[Port]:
    """The port `name` of the device tagged `tag`."""
    (item,) = (i for i in items(model).values() if i.tag == tag)
    fns = {f.id for f in functions(model).values() if f.item == item.id}
    return next(p.id for p in ports(model).values() if p.function in fns and p.name == name)


def test_rail_pins_stand_their_power_kind(model: Model) -> None:
    result = stands(model)
    assert result[_port(model, "P1", "1")] is PowerKind.SUPPLY
    assert result[_port(model, "P3", "1")] is PowerKind.SUPPLY
    assert result[_port(model, "P1", "2")] is PowerKind.GROUND
    assert result[_port(model, "P5", "1")] is PowerKind.PE


def test_a_two_port_earth_net_is_a_wire_as_a_two_port_24v_net_is(model: Model) -> None:
    """Can-fail (R1289): a PE branch with no port-count test makes P12 stand the earth symbol."""
    result = stands(model)
    assert _port(model, "P12", "1") not in result
    assert _port(model, "P13", "1") not in result


def test_a_pin_that_stands_a_symbol_is_connected_by_its_stand() -> None:
    """Can-fail (R1289): without the stand clause in `connected_ports` the lone pin, whose peers are all rail terminals, is unconnected."""
    d = fr.design("demo_parts")
    with d.function("F", "Group"):
        pe = d.terminal_strip("PE", "DEMO-TB-2.5", 2).run("L", 2, bridged=True, rail=True)
        lamp = d.device("P1", "DEMO-LAMP-24")
        d.earth(lamp.lamp["1"], pe[1].outer, pe[2].outer)
        zero = d.terminal_strip("Z1", "DEMO-TB-2.5", 1).run("L", 1)
        d.series(lamp.lamp["2"], zero[1].outer, wire=_WIRE)
    model = fr.build(d).model
    assert stands(model)
    assert set(stands(model)) <= connected_ports(model)


def _rail_design(*, flag_second: bool = False, potentials: bool = True, two_units: bool = False) -> fr.Design:
    """A bridged 24 V strip X1 (flagged) and a 0 V strip Z1; X2 is a second 24 V strip, flagged when asked."""
    d = fr.design("demo_parts")

    def build(owner: fr.Design, *, second: bool) -> None:
        with owner.function("F", "Group"):
            live = owner.terminal_strip("X1", "DEMO-TB-2.5", 3).run("L", 3, bridged=True, rail=True)
            zero = owner.terminal_strip("Z1", "DEMO-TB-2.5", 3).run("L", 3, bridged=True)
            lamp = owner.device("P1", "DEMO-LAMP-24")
            owner.series(lamp.lamp["1"], live[2].outer, wire=_WIRE)
            owner.series(lamp.lamp["2"], zero[2].outer, wire=_WIRE)
            if potentials:
                owner.dc_supply("S", plus=live[1], minus=zero[1], voltage=24)
            if second:
                other = owner.terminal_strip("X2", "DEMO-TB-2.5", 3).run("L", 3, bridged=True, rail=flag_second)
                owner.series(live[3].outer, other[1].outer, wire=_WIRE)

    if two_units:

        @fr.unit("demo-cab", revision=1, interface_version=1, date="2026-10-14", text="first", by="AB")
        def cab(u: fr.Design) -> _Nothing:
            build(u, second=False)
            return _Nothing()

        d.add(cab, "U1", place=None)
        d.add(cab, "U2", place=None)
        return d
    build(d, second=True)
    return d


def test_a_declared_group_is_a_rail_terminal_and_an_unflagged_bridged_group_is_not() -> None:
    """Can-fail: an `is_rail_terminal` that is always False fails the first assert."""
    model = fr.build(_rail_design()).model
    by_terminal = {t: is_rail_terminal(model, t) for t in terminal_items(model)}
    assert sum(by_terminal.values()) == 3
    assert not all(by_terminal.values())


def test_two_groups_of_one_potential_in_one_unit_are_an_error_naming_both() -> None:
    """Can-fail: dropping the unit-and-potential keying removes the finding."""
    result = fr.build(_rail_design(flag_second=True))
    expect_codes(result, "RAIL_DUPLICATE_POTENTIAL")
    (found,) = [f for f in check_rails(result.model) if f.code == "RAIL_DUPLICATE_POTENTIAL"]
    assert found.message.count("rail group") == 2


def test_the_same_potential_in_two_units_is_two_rails() -> None:
    """Can-fail: a key without the unit reports the two cabinets as one potential twice."""
    model = fr.build(_rail_design(two_units=True)).model
    assert [f.code for f in check_rails(model)] == []


def test_a_group_with_no_potential_is_an_error() -> None:
    """Can-fail: removing the `None` branch leaves the finding out."""
    expect_codes(fr.build(_rail_design(potentials=False)), "RAIL_WITHOUT_POTENTIAL")


def test_a_rail_group_on_a_fused_terminal_is_an_error() -> None:
    """Can-fail: removing the fused branch leaves the finding out; its text names the strip tag, not a file line (N7)."""
    d = fr.design("demo_parts")
    with d.function("F", "Group"):
        live = d.terminal_strip("X1", "DEMO-TB-FUSE-2.5", 2).run("L", 2, bridged=True, rail=True)
        zero = d.terminal_strip("Z1", "DEMO-TB-2.5", 2).run("L", 2, bridged=True, rail=True)
        d.dc_supply("S", plus=live[1], minus=zero[1], voltage=24)
    result = fr.build(d)
    expect_codes(result, "RAIL_ON_FUSED")
    (text,) = [f.message for f in result.findings if f.code == "RAIL_ON_FUSED"]
    assert "strip -X1" in text
    assert ".py:" not in text


def test_a_group_on_two_potentials_has_none_and_is_an_error() -> None:
    """Can-fail (R911 Q7): a `min()` over the potentials picks one of two and the finding goes."""
    d = fr.design("demo_parts")
    with d.function("F", "Group"):
        live = d.terminal_strip("X1", "DEMO-TB-2.5", 3).run("L", 3, bridged=True, rail=True)
        d.dc_supply("S", plus=live[1], minus=live[2], voltage=24)
    expect_codes(fr.build(d), "RAIL_WITHOUT_POTENTIAL", "NET_SHORTED", "NET_POTENTIAL_CONFLICT")


def _flagged_strip_case(potential: str, lamps: int) -> Model:
    """`lamps` lamp pins wired to the one flagged terminal of a strip, on 24 V or on PE."""
    d = fr.design("demo_parts")
    with d.function("F", "Group"):
        flag = d.terminal_strip("X1", "DEMO-TB-2.5-TWIN", 1).run("L", 1, rail=True)
        zero = d.terminal_strip("Z1", "DEMO-TB-2.5", lamps).run("L", lamps)
        devices = [d.device(f"P{i}", "DEMO-LAMP-24") for i in range(1, lamps + 1)]
        for k, lamp in enumerate(devices, 1):
            d.series(lamp[1], flag[1].outer, wire=(GNYE, 0.5) if potential == "PE" else _WIRE)
            d.series(lamp[2], zero[k].outer, wire=_WIRE)
        if potential == "PE":
            d.earth(flag[1].outer, *(lamp[1] for lamp in devices))
        else:
            d.dc_supply("S", plus=flag[1], minus=zero[1], voltage=24)
    return fr.build(d).model


@pytest.mark.parametrize("lamps", [1, 2])
def test_pe_follows_the_24v_path_through_a_flagged_terminal(lamps: int) -> None:
    """Can-fail (R1289): a PE-only branch in `_kinds`, `stands` or `connected_ports` makes the two shapes differ."""

    def shape(potential: str) -> tuple[frozenset[tuple[str, str]], frozenset[tuple[str, str]], int]:
        model = _flagged_strip_case(potential, lamps)
        tag_of = {
            p.id: (next(i.tag or "" for i in items(model).values() if i.id == functions(model)[p.function].item), p.name)
            for p in ports(model).values()
        }
        standing = frozenset(tag_of[p] for p, kind in stands(model).items() if kind is not PowerKind.GROUND)
        joined = frozenset(tag_of[p] for p in connected_ports(model) if tag_of[p][0].startswith("P"))
        rails = sum(is_rail_terminal(model, t) for t in terminal_items(model))
        return standing, joined, rails

    assert shape("PE") == shape("24V")


def _pe_cabinet(tmp_path: Path, *, hide: bool = False) -> fr.BuildResult:
    """A flagged PE strip with its jumper, a motor wired to Z1 whose PE pin is wired to the strip, and Z1:4 wired to Z2."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    bar = d.terminal_strip("X1", "DEMO-TB-2.5", pe="DEMO-TB-PE-2.5").run("PE", 2, bridged=True, rail=True)
    motor = d.device("M1", "DEMO-MOTOR-4KW")
    zero = d.terminal_strip("Z1", "DEMO-TB-2.5", 4).run("L", 4)
    for k, pin in enumerate("UVW", 1):
        d.series(motor.motor[pin], zero[k].outer, wire=_WIRE)
    d.series(motor.motor["PE"], bar[1].inner, wire=(GNYE, 2.5))
    d.earth(motor.motor["PE"], bar[1])
    other = d.terminal_strip("Z2", "DEMO-TB-2.5", 1)
    d.series(zero[4].inner, other[1].inner, wire=_WIRE)
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "c.md").write_text("# C\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=tmp_path / "c.md")
    path = tmp_path / "fransys.toml"
    path.write_text(f"[export]\nhide_pe = {str(hide).lower()}\n", encoding="utf-8")
    return fr.build(d, doc, settings=fr.settings(path))


def test_the_pe_conductors_are_the_wire_and_the_jumper_on_the_pe_rail_terminals(tmp_path: Path) -> None:
    """Can-fail (model-0435): a predicate that names no PE-rail end leaves the set empty or takes the lamp's wire."""
    model = _pe_cabinet(tmp_path).model
    pe = {c for c in conductors(model) if is_pe_conductor(model, c)}
    assert len(pe) == 2
    assert all(
        any(is_rail_terminal(model, item_of_port(model, p)) and port_power_kind(model, p) is PowerKind.PE for p in conductor_ends(model, c))
        for c in pe
    )
    assert {c for c in conductors(model) if is_bridge(model, c)} <= pe


def test_hide_pe_leaves_out_exactly_the_pe_conductors_and_the_lists_keep_them(tmp_path: Path) -> None:
    """Can-fail (model-0435): a filter that takes one more or one fewer conductor, or one the lists read, breaks the sets or the rows."""
    shown, hidden = _pe_cabinet(tmp_path / "a").model, _pe_cabinet(tmp_path / "b", hide=True).model
    pe = {c for c in conductors(shown) if is_pe_conductor(shown, c)}
    assert pe
    assert set(conductors(hidden)) - drawn_conductors(hidden) == pe | {c for c in conductors(hidden) if is_bridge(hidden, c)}
    assert set(conductors(shown)) - drawn_conductors(shown) == {c for c in conductors(shown) if is_bridge(shown, c)}
    assert wire_rows(shown) == wire_rows(hidden)
    assert [terminal_rows(shown, x) for x in sorted(terminal_strips(shown), key=str)] == [
        terminal_rows(hidden, x) for x in sorted(terminal_strips(hidden), key=str)
    ]


def test_hide_pe_draws_no_protective_earth_and_every_other_connection_with_cnd_0(tmp_path: Path) -> None:
    """Can-fail (el-0119): an option that left the stand or the PE wire in, or took a Z1 wire out, shows a PE symbol or a CND finding."""
    shown, hidden = _pe_cabinet(tmp_path / "a"), _pe_cabinet(tmp_path / "b", hide=True)
    assert PowerKind.PE in stands(hidden.model).values()
    assert PowerKind.PE not in drawn_stands(hidden.model).values()
    assert PowerKind.PE in drawn_stands(shown.model).values()
    assert "CONNECTION_NOT_DRAWN" not in {f.code for f in fr.check(hidden)}
    assert {f: function_scopes(shown.model, f) for f in functions(shown.model)} == {
        f: function_scopes(hidden.model, f) for f in functions(hidden.model)
    }
    assert "protective-earth" in [s.symbol for s in layout_of(shown.model, PowerSymbol).values()]
    assert "protective-earth" not in [s.symbol for s in layout_of(hidden.model, PowerSymbol).values()]


def _page_svg(result: fr.BuildResult, folder: Path) -> str:
    """The compiled SVG of every page of `result`, joined."""
    fr.write(result, folder / "out", intermediates=folder / "inter")
    return "".join(p.read_text("utf-8") for p in sorted((folder / "inter").glob("layout.page-*.svg")))


def test_hide_pe_leaves_no_pe_pin_ink_on_the_motor_page(tmp_path: Path) -> None:
    """Can-fail (model-0435): without the PE stroke bound to its port, or without the marking drop, the PE polyline or its text stays."""
    shown = _page_svg(_pe_cabinet(tmp_path / "a"), tmp_path / "a")
    hidden = _page_svg(_pe_cabinet(tmp_path / "b", hide=True), tmp_path / "b")
    pe_lead = 'points="6.5625,-3.75 10,-8.125 10,-12.5"'
    assert pe_lead in shown
    assert ">PE</text>" in shown
    assert pe_lead not in hidden
    assert ">PE</text>" not in hidden
    assert all(f">{pin}</text>" in hidden for pin in "UVW")
