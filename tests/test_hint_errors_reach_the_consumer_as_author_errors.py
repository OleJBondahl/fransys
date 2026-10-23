"""A layout hint error reaches the consumer as `fr.AuthorError` naming file:line (decision 0184).

A chain that names a box-drawn function in its middle is an AuthorError; the cause stays the layout
`HintError`. An order cycle is an ERROR finding naming the hints' Origins (R468, FLIP-NOW F2).
"""

from typing import TYPE_CHECKING, Any

import fransys as fr
import pytest
from _model_build_cover import cabinet_document
from fransys.colours import BU

from fransys_layout import HintError

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
    d.detail.wire(di.di_1["1"], k1.co_1["14"], wire=(BU, 0.5))
    d.detail.wire(k1.co_1["11"], h1.lamp[1], wire=(BU, 0.5))
    d.detail.wire(h1.lamp[2], psu.output["-"], wire=(BU, 0.5))
    hint(d, (one, two), (k1, h1, di))
    return fr.build(d, cabinet_document(cab))


def _cycle(d: Any, groups: Any, _devices: Any) -> None:
    one, two = groups
    d.layout.order(one, two)
    d.layout.order(two, one)


def _middle(d: Any, _groups: Any, devices: Any) -> None:
    k1, h1, di = devices
    d.layout.chain(k1.co_1, di.di_1, h1.lamp)


def test_a_chain_through_a_box_is_an_author_error_naming_file_and_line() -> None:
    with pytest.raises(fr.AuthorError, match="head or its tail") as raised:
        _build(_middle)
    assert f"{__file__.rsplit('/', 1)[-1]}:" in str(raised.value)
    assert isinstance(raised.value.__cause__, HintError)


def test_an_order_cycle_is_an_error_finding_naming_the_hints_origins() -> None:
    (finding,) = [f for f in _build(_cycle).findings if f.code == "ORDER_HINT_CYCLE"]
    assert finding.severity is fr.Severity.ERROR
    here = __file__.rsplit("/", 1)[-1]
    assert finding.message.count(here) == 2
