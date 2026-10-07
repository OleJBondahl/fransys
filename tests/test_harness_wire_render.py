"""A single wire of a harness renders from layout's records: two runs and its key (HA-D6 P2).

Render computes no position: the key stands where `CoreWire.text_x/text_y` say.
"""

import re
from dataclasses import replace
from typing import Any

import fransys as fr
import pytest
from fransys.colours import BU
from fransys_render import cable_blocks

from fransys_layout import lay_out_cables
from fransys_model.derive.cable_drawing import block_wires
from fransys_model.kernel import Origin, evolve
from fransys_model.layout import CableBlock, CoreWire, layout_of

_PLUG = "DEMO-CONN-4P"
_ORIGIN = Origin(file="tests/test_harness_wire_render.py", line=1, note="invented")


@pytest.fixture(scope="module")
def laid() -> Any:
    """Wire-only harness `ONLY` with one BU 0.5 mm² wire, after the cable pass."""
    d = fr.design("demo_parts")
    d.location("L0", "Workshop")
    with d.function("ONLY", "Wire-only loom"):
        loom = d.harness("ONLY", place="L0")
        near = d.device("J1", _PLUG, parent=loom, place="L0")
        far = d.device("J2", _PLUG, parent=loom, place="L0")
        d.wire(near[1], far[1], wire=(BU, 0.5))
    return lay_out_cables(fr.build(d).model)[0]


def _svg(model: Any) -> str:
    (svg,) = cable_blocks(model).values()
    return svg


def _key_text(svg: str) -> tuple[str, str]:
    """The wire key's (x, text) from the one `label core` text."""
    ((x, text),) = re.findall(r'<text class="label core"[^>]* x="([^"]+)"[^>]*>([^<]*)</text>', svg)
    return x, text


def test_the_wire_draws_two_runs_and_its_derived_key(laid: Any) -> None:
    """Two polylines and the key `DrawnWire.text`. A render that drops a wire without a cable
    (the old KeyError path) or invents its own text fails here."""
    (block,) = layout_of(laid, CableBlock).values()
    (drawn,) = block_wires(laid, block.subject, block.unit)
    svg = _svg(laid)
    assert svg.count('<polyline class="wire core"') == 2
    assert _key_text(svg)[1] == drawn.text
    assert "BU" in drawn.text
    assert "0.5 mm²" in drawn.text


def _shifted(model: Any, dx: int) -> float:
    """The key's x after `text_x` moves by `dx` grid units in the record."""
    (wire,) = layout_of(model, CoreWire).values()
    return float(
        _key_text(
            _svg(
                evolve(
                    model,
                    put=[replace(wire, text_x=wire.text_x + dx)],
                    remove=[wire.id],
                    origin=_ORIGIN,
                )
            )
        )[0]
    )


def test_the_key_stands_where_the_record_puts_it(laid: Any) -> None:
    """Moving `text_x` in the record moves the key in proportion: render adds no position of
    its own. A render-computed key position would stay put."""
    base = _shifted(laid, 0)
    step = _shifted(laid, 4) - base
    assert step > 0
    assert _shifted(laid, 8) - base == pytest.approx(2 * step)
