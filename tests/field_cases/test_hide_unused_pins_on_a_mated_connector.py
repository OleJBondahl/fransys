"""Field case: a field device with a connector, mated to a harness plug whose cable core lands on
one pin, the other pin unwired, built with the profile switch `hide_unused_pins` on.

The bug: the build raised `KeyError (LabelKind.MARKING, <port>)` in `label_requests`. With the
switch on, the set of drawn functions was taken after the connector became one view per pin, so
it held the pin views' ids and not the connector's own, and no marking text was made for the
pins. Without the switch the same circuit built.

Fix: the drawn set counts a pin view as its connector, switch on or off (read/__init__.py,
layout-0112's drawn set). It states no new rule, so no decision number.
"""

from typing import TYPE_CHECKING

import fransys as fr

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_model.vocab.tables import functions, items, ports

if TYPE_CHECKING:
    from pathlib import Path

_PLUG = "DEMO-CONN-2P"
_CABLE = "DEMO-CBL-4G1.5"


def _build(tmp_path: Path) -> fr.BuildResult:
    d = fr.design("demo_parts", place="EXT")
    d.location("EXT", "External")
    d.layout.profile(hide_unused_pins=True)
    switch = d.device("K1", "DEMO-SWITCH-2P", external=True)
    harness = d.harness("W3")
    near = d.device(None, _PLUG, name="p1", parent=harness)
    far = d.device(None, _PLUG, name="p2", parent=harness)
    cable = d.cable("W1", _CABLE, name="c", parent=harness, length_m=3)
    cable.core(1, near.x1["1"], far.x1["1"])
    d.mate(far, switch.x1)
    cover = tmp_path / "cover.md"
    cover.write_text("# System\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.SYSTEM, None, cover=cover))


def test_hide_unused_pins_builds_a_mated_connector(tmp_path: Path) -> None:
    """The build succeeds; the switch's pin with a conductor is drawn, its unwired pin is not."""
    result = _build(tmp_path)
    assert [f for f in result.findings if f.severity.name == "ERROR"] == []
    model = result.model
    results, _ = stage_results(model, read_inputs(model))
    (k1,) = (one.id for one in items(model).values() if one.tag == "K1")
    own = {f.id for f in functions(model).values() if f.item == k1}
    pin = {p.name: p.id for p in ports(model).values() if p.function in own}
    placed = {one.function for one in results.layout.placed}
    assert pin["1"] in placed
    assert pin["2"] not in placed
