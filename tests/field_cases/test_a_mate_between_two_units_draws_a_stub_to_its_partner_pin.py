"""Field case: two units each hold a connector, mated to each other, so the halves stand in no common drawing (KI-441).
The bug: 0.22 refused every mate, so a plug between two drawings could not be drawn.
Fixed by model-0445 (R2223): each mated pin owes an OFF stub naming its partner, also on a rail (KI-1405); a mate inside one drawing stays refused."""

from functools import cache
from typing import NamedTuple

import fransys as fr
import pytest
from _expected_codes import expect_codes
from _model_build_cover import unit_document
from fransys.colours import BU

from fransys_model.derive import mate_pairs
from fransys_model.layout import LinkMarker, StarKind, layout_of
from fransys_model.vocab.tables import ports

_CLEAN = (
    "CONNECTION_NOT_DRAWN",
    "DANGLING_WIRE_END",
    "MARKER_UNPAIRED",
    "MATES_DISABLED",
    "WIRE_OVER_MARKER",
)  # the stub stands at the pin's mating port, never on its wire


class _Io(NamedTuple):
    X1: fr.Device


def _unit(name: str, mpn: str, *, wired: bool) -> fr.UnitDef[_Io]:
    @fr.unit(name, revision=1, interface_version=1, date="2026-02-02", text="First", by="XX")
    def board(u: fr.Design) -> _Io:
        x1 = u.device("X1", mpn, interface=True)
        if wired:
            lamp = u.device("H1", "DEMO-LAMP-24")
            u.series(x1["1"], lamp["1"], wire=(BU, 0.5))
            u.series(lamp["2"], x1["2"], wire=(BU, 0.5))
        return _Io(x1)

    return board


@cache
def _built(*, second_wired: bool, third: bool = False) -> fr.BuildResult:
    d = fr.design("demo_parts")
    first = d.add(_unit("demo-mate-a", "DEMO-HSG-4M", wired=True), "A")
    second = d.add(_unit("demo-mate-b", "DEMO-HSG-4F", wired=second_wired), "B")
    d.mate(first.X1, second.X1)
    documents = [unit_document(first), unit_document(second)]
    if third:
        other = d.add(_unit("demo-mate-c", "DEMO-HSG-4F", wired=True), "C")
        d.mate(first.X1, other.X1)
        documents.append(unit_document(other))
    return fr.build(d, *documents)


class _Plug(NamedTuple):
    X1: fr.Device


def _rail(u: fr.Design, tag: str) -> tuple[fr.SupplyRail, fr.SupplyRail]:
    """A 24 V supply with a lamp across it, so both rails hold three pins; the pair's supply ends are returned."""
    dc = u.dc_supply("24VDC", u.device(f"G{tag}", "DEMO-PSU-24").output, names=("P24", "P0"))
    lamp = u.device(f"H{tag}", "DEMO-LAMP-24")
    u.series(dc.plus, lamp["1"], wire=(BU, 0.5))
    u.series(lamp["2"], dc.minus, wire=(BU, 0.5))
    return dc.plus, dc.minus


@fr.unit("demo-mate-rail-board", revision=1, interface_version=1, date="2026-02-02", text="First", by="XX")
def _rail_board(u: fr.Design) -> _Plug:
    x1 = u.device("X1", "DEMO-HSG-4F", interface=True)
    plus, minus = _rail(u, "1")
    u.series(plus, x1["1"], wire=(BU, 0.5))
    u.series(x1["2"], minus, wire=(BU, 0.5))
    return _Plug(x1)


@fr.unit("demo-mate-rail-top", revision=1, interface_version=1, date="2026-02-02", text="First", by="XX")
def _rail_top(u: fr.Design) -> _Plug:
    plug = u.device(None, "DEMO-HSG-4M", name="kx1")
    u.mate(plug, u.add(_rail_board, "A2").X1)
    plus, minus = _rail(u, "2")
    u.series(plus, plug["1"], wire=(BU, 0.5))
    u.series(plug["2"], minus, wire=(BU, 0.5))
    return _Plug(plug)


@cache
def _rail_built() -> fr.BuildResult:
    d = fr.design("demo_parts")
    top = d.add(_rail_top, "U1")
    d.layout.profile(hide_unused_pins=True)
    return fr.build(d, unit_document(top))


@pytest.mark.rule("MATE-REFERENCE")
def test_a_mated_pair_on_a_power_rail_draws_an_off_stub_not_two_bare_power_symbols() -> None:
    result = _rail_built()
    assert [f.code for f in result.findings if f.code in (*_CLEAN, "PLACEMENT_PROBLEM")] == []
    pairs = {(a, b) for _, a, b in mate_pairs(result.model) if ports(result.model)[a].name in {"1", "2"}}
    assert len(pairs) == 2
    stubs = {(m.port, m.far) for m in layout_of(result.model, LinkMarker).values() if m.star is StarKind.OFF}
    assert stubs == {end for pair in pairs for end in (pair, pair[::-1])}


@pytest.mark.rule("MATE-REFERENCE")
@pytest.mark.parametrize("second_wired", [True, False], ids=["both halves wired", "one half unwired"])
def test_each_mated_pin_draws_an_off_stub_naming_its_partner_pin(*, second_wired: bool) -> None:
    result = _built(second_wired=second_wired)
    assert [f.code for f in result.findings if f.code in _CLEAN] == []
    pairs = {(a, b) for _, a, b in mate_pairs(result.model) if ports(result.model)[a].name in {"1", "2"}}
    assert len(pairs) == 2
    stubs = {(m.port, m.far) for m in layout_of(result.model, LinkMarker).values() if m.star is StarKind.OFF}
    assert stubs == {end for pair in pairs for end in (pair, pair[::-1])}


def test_a_function_on_two_mates_stays_refused() -> None:
    expect_codes(_built(second_wired=True, third=True), "MATES_DISABLED")


@fr.unit("demo-mate-rails-board", revision=1, interface_version=1, date="2026-02-02", text="First", by="XX")
def _rails_board(u: fr.Design) -> _Plug:
    x1 = u.device("X1", "DEMO-HSG-4F", interface=True)
    lamp = u.device("H1", "DEMO-LAMP-24")
    u.series(x1["1"], lamp["1"], wire=(BU, 0.5))
    u.series(lamp["2"], x1["2"], wire=(BU, 0.5))
    return _Plug(x1)


@fr.unit("demo-mate-rails-top", revision=1, interface_version=1, date="2026-02-02", text="First", by="XX")
def _rails_top(u: fr.Design) -> _Plug:
    """A free plug mated to a child board, its pins on the 24 V and 0 V rails; a lamp from each pin, joined at a node (the series_parallel case)."""
    plug = u.device(None, "DEMO-HSG-4M", name="kx1")
    u.mate(plug, u.add(_rails_board, "A2").X1)
    plus, minus = _rail(u, "2")
    from_plus, from_minus = u.device("H3", "DEMO-LAMP-24"), u.device("H4", "DEMO-LAMP-24")
    u.series(plus, plug["1"], wire=(BU, 0.5))
    u.series(plug["2"], minus, wire=(BU, 0.5))
    u.series(plug["1"], from_plus["1"], wire=(BU, 0.5))
    u.series(plug["2"], from_minus["1"], wire=(BU, 0.5))
    u.series(from_plus["2"], from_minus["2"], wire=(BU, 0.5))
    return _Plug(plug)


@cache
def _rails_built() -> fr.BuildResult:
    d = fr.design("demo_parts")
    top = d.add(_rails_top, "U1")
    d.layout.profile(hide_unused_pins=True)
    return fr.build(d, unit_document(top))


@pytest.mark.rule("MATE-REFERENCE")
def test_a_cabinet_with_a_mated_free_plug_on_two_rails_draws_clean_with_an_off_stub_to_its_partner() -> None:
    result = _rails_built()
    assert [f.code for f in result.findings if f.code in (*_CLEAN, "PLACEMENT_PROBLEM") or f.severity is fr.Severity.ERROR] == []
    pins = {(a, b) for _, a, b in mate_pairs(result.model) if ports(result.model)[a].name in {"1", "2"}}
    assert len(pins) == 2
    stubs = {(m.port, m.far) for m in layout_of(result.model, LinkMarker).values() if m.star is StarKind.OFF}
    assert stubs == {end for pair in pins for end in (pair, pair[::-1])}
