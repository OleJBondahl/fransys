"""A layout hint error reaches the consumer as `fr.AuthorError` naming file:line (decision 0184).

One case per kind of `HintError` the facade translates: an order cycle and a chain that names a
box-drawn function in its middle. The cause stays the layout `HintError`.
"""

from typing import TYPE_CHECKING, Any

import fransys as fr
import pytest
from _model_build_cover import cabinet_document
from fransys.colours import BU

from fransys_layout import HintError

if TYPE_CHECKING:
    from collections.abc import Callable


def _build(hint: Callable[[Any, Any, Any], None]) -> None:
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
    fr.build(d, cabinet_document(cab))


def _cycle(d: Any, groups: Any, _devices: Any) -> None:
    one, two = groups
    d.layout.order(one, two)
    d.layout.order(two, one)


def _middle(d: Any, _groups: Any, devices: Any) -> None:
    k1, h1, di = devices
    d.layout.chain(k1.co_1, di.di_1, h1.lamp)


@pytest.mark.parametrize(("hint", "word"), [(_cycle, "cycle"), (_middle, "head or its tail")])
def test_a_hint_error_is_an_author_error_naming_file_and_line(
    hint: Callable[[Any, Any, Any], None], word: str
) -> None:
    with pytest.raises(fr.AuthorError, match=word) as raised:
        _build(hint)
    assert f"{__file__.rsplit('/', 1)[-1]}:" in str(raised.value)
    assert isinstance(raised.value.__cause__, HintError)
