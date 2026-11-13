"""Field case: two units each hold a connector, mated to each other, so the halves stand in no common drawing (KI-441).
The bug: 0.22 refused every mate, so a plug between two drawings could not be drawn.
Fixed by model-0445 (R2223): each mated pin owes an OFF stub that names its partner pin; a mate inside one drawing stays refused."""

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

_CLEAN = ("CONNECTION_NOT_DRAWN", "DANGLING_WIRE_END", "MARKER_UNPAIRED", "MATES_DISABLED")


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
