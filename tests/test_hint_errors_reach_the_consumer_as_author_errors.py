"""Order hints: a cycle and a group that draws nothing are ERROR findings (R468, FLIP-NOW F2; R1841)."""

from typing import TYPE_CHECKING, Any

import fransys as fr
from _expected_codes import expect_codes
from _model_build_cover import cabinet_document
from fransys.colours import BU

if TYPE_CHECKING:
    from collections.abc import Callable


def _build(hint: Callable[[Any, Any, Any], None]) -> Any:
    d = fr.design("demo_parts", place="CAB")
    d.project(title="Hints", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-02", text="First issue", created="XX")
    cab = d.location("CAB", "Cabinet")
    with d.function("F1", "One") as one:
        k1 = d.device("K1", "DEMO-RLY-2CO-24")
        h1 = d.device("H1", "DEMO-LAMP-24")
        di = d.device("A1", "DEMO-PLC-DI-2")
        psu = d.device("G1", "DEMO-PSU-24")
    with d.function("F2", "Two") as two:
        d.device("K2", "DEMO-RLY-2CO-24")
    d.series(di.di_1["1"], k1.co_1["14"], wire=(BU, 0.5))
    d.series(k1.co_1["11"], h1.lamp[1], wire=(BU, 0.5))
    d.series(h1.lamp[2], psu.output["-"], wire=(BU, 0.5))
    hint(d, (one, two), (k1, h1, di))
    return fr.build(d, cabinet_document(cab))


def _cycle(d: Any, groups: Any, _devices: Any) -> None:
    one, two = groups
    d.layout.order(one, two)
    d.layout.order(two, one)


def test_an_order_cycle_is_an_error_finding_naming_the_hints_origins() -> None:
    result = _build(_cycle)
    expect_codes(result, "ORDER_HINT_CYCLE")
    (finding,) = [f for f in result.findings if f.code == "ORDER_HINT_CYCLE"]
    assert finding.severity is fr.Severity.ERROR
    here = __file__.rsplit("/", 1)[-1]
    assert finding.message.count(here) == 2


def _draws_nothing(result: Any) -> list[Any]:
    return [f for f in result.findings if f.code == "ORDER_GROUP_DRAWS_NOTHING"]


def _empty(d: Any, groups: Any, _devices: Any) -> None:
    with d.function("F3", "Three") as three:
        pass
    d.layout.order(groups[0], three)


def test_an_order_hint_naming_a_group_with_no_member_is_an_error_naming_it_and_the_fix() -> None:
    result = _build(_empty)
    expect_codes(result, "ORDER_GROUP_DRAWS_NOTHING")
    (found,) = _draws_nothing(result)
    assert found.severity is fr.Severity.ERROR
    assert "=F3" in found.message
    assert "no member to draw" in found.message
    assert "drop the hint" in found.message


def test_an_order_hint_naming_drawn_groups_gives_no_such_error() -> None:
    assert _draws_nothing(_build(lambda d, groups, _devices: d.layout.order(*groups))) == []


def test_a_group_that_draws_one_function_of_its_split_relay_is_ordered_where_it_draws() -> None:
    d = fr.design("demo_parts", place="CAB")
    with d.function("MOD", "Module") as mod:
        k1 = d.device("K1", "DEMO-RLY-2CO-24")
    with d.function("RUN", "Run") as run:
        g1 = d.device("G1", "DEMO-PSU-24")
        d.series(g1.output["+"], k1.coil, g1.output["-"], wire=(BU, 0.5))
    d.layout.order(mod, run)
    assert _draws_nothing(fr.build(d)) == []
