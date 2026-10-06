"""Field case: a PLC analog input channel with two pins, both wired to a two-pin header, built
with the profile switch `hide_unused_pins` on, in order and crossed.

The bug: the build gave SYMBOL_PORT_MISSING "model port '1' has no port on symbol 'plc-channel'"
with the switch on. Without the switch the same circuit built clean.

Cause: hiding left the module one drawn channel, and a module of one function was not an item
view, so the channel met the one-port `plc-channel` symbol (C6 binds one port on one port only).
Fix: a lone PLC channel with two or more ports is a view too (read/views.py). It states no new
rule (layout-0112's views), so no decision number.
"""

from typing import TYPE_CHECKING

import fransys as fr
import pytest

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs

if TYPE_CHECKING:
    from fransys_layout.geometry import Facing, Point


def _build(
    tmp_path_factory: pytest.TempPathFactory, *, hide: bool, crossed: bool
) -> fr.BuildResult:
    d = fr.design("demo_parts")
    cab = d.location("C1", "Cabinet")
    if hide:
        d.layout.profile(hide_unused_pins=True)
    module = d.device("K1", "DEMO-PLC-AI-4", place="C1")
    header = d.device("J1", "DEMO-CONN-2P", place="C1")
    first, second = ("2", "1") if crossed else ("1", "2")
    d.wire(header["1"], module.ai_1[first], wire=("WH", 0.5))
    d.wire(header["2"], module.ai_1[second], wire=("WH", 0.5))
    cover = tmp_path_factory.mktemp("hp") / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover))


def _channel_ports(result: fr.BuildResult) -> list[tuple[str, Point, Facing]]:
    """Channel 1's ports of the module's box: its name, place and facing."""
    model = result.model
    results, _ = stage_results(model, read_inputs(model))
    (box,) = (one.geometry for one in results.layout.placed if one.geometry.key == "generic-box")
    return [(p.name, p.at, p.facing) for p in box.ports if p.name.startswith("ai_1.")]


@pytest.mark.parametrize("crossed", [False, True])
def test_hiding_keeps_a_wired_channel_as_it_is(
    tmp_path_factory: pytest.TempPathFactory, *, crossed: bool
) -> None:
    """0 ERROR with the switch on, and channel 1's ports equal those of the build without it."""
    hidden = _build(tmp_path_factory, hide=True, crossed=crossed)
    assert [f for f in hidden.findings if f.severity.name == "ERROR"] == []
    plain = _build(tmp_path_factory, hide=False, crossed=crossed)
    assert len(_channel_ports(hidden)) == 2
    assert _channel_ports(hidden) == _channel_ports(plain)
