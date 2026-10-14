"""Field case: a unit's boundary box lists an interface terminal once, however often it is reached.

The engineering shape: an I/O unit with one terminal strip whose terminal 4 is its interface,
bridged or not, and one outside device whose three conductors of one cable all land on that
terminal.

The bug: the box printed the terminal's designation (`-IO-XF:4`) on its title line and again on
a row for every port the conductors landed on, so it read `-IO-XF:4` three times (two times on a
strip with no bridge).

The rule (decision layout-0255): a box prints each distinct line once; the count of its lines
does not follow how often its terminal is reached.
"""

from typing import Any, NamedTuple

import fransys as fr
import pytest
from _model_build_cover import layout_trigger_document

from fransys_model.derive import connector_box_lines
from fransys_model.vocab.tables import boundaries


class _Io(NamedTuple):
    XF: Any


def _built(*, bridged: bool) -> fr.BuildResult:
    @fr.unit("demo-io", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
    def io(d: fr.Design) -> _Io:
        return _Io(d.terminal_strip("XF", "DEMO-TB-2.5", 6, interface=(4,), bridged=bridged))

    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    unit = d.add(io, "IO")
    relay = d.device("P1", "DEMO-RLY-4CO-24")
    cable = d.cable("W1", "DEMO-CBL-4G1.5")
    cable.core(1, relay.coil["A1"], unit.XF[4])
    cable.core(2, relay.co_1["11"], unit.XF[4])
    cable.core(3, relay.co_1["14"], unit.XF[4])
    return fr.build(d, layout_trigger_document())


@pytest.mark.parametrize("bridged", [True, False])
def test_an_interface_terminal_is_listed_once(*, bridged: bool) -> None:
    model = _built(bridged=bridged).model
    (function,) = {b.function for b in boundaries(model).values()}
    assert connector_box_lines(model, function) == ("-IO-XF:4",)
