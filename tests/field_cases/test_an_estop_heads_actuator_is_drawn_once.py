"""Field case: one e-stop head with NC contact blocks clipped on, each opening its own circuit.
Once the actuator drew at the lead contact only; API-022 removed that mode, every block draws its own mushroom."""

from collections import Counter
from typing import TYPE_CHECKING

import fransys as fr
from _drawn_pages import drawn_pages
from _model_build_cover import cabinet_document
from fransys.colours import BU


def _head_example() -> Model:
    """The e-stop head with two NC blocks, both wired to the terminal strip."""
    d = fr.design("demo_parts", place="CAB")
    d.project(title="E-stop", number="P-1", customer="Example Co", revision=1, author="OJB")
    d.revision(1, date="2026-10-14", text="First issue", created="XX")
    cabinet = d.location("CAB", "Cabinet")
    strip = d.terminal_strip("X1", "DEMO-TB-2.5")
    s1 = d.device("S1", "DEMO-HEAD-ESTOP")
    first = d.device(None, "DEMO-BLOCK-1NC", name="nc-1", parent=s1)
    second = d.device(None, "DEMO-BLOCK-1NC-21", name="nc-2", parent=s1)
    wire = (BU, 0.5)
    d.series(strip[1], first["11"], wire=wire)
    d.series(first["12"], strip[2], wire=wire)
    d.series(strip[3], second["21"], wire=wire)
    d.series(second["22"], strip[4], wire=wire)
    return fr.build(d, cabinet_document(cabinet)).model


def test_nothing_set_draws_the_head_example_as_it_was_before_one_actuator_per_device() -> None:
    """With nothing set, each contact block draws its own mushroom actuator, as before Part 1."""
    drawn = Counter(one.key for d in drawn_pages(_head_example()).values() for one in d.symbols)
    assert drawn == {"terminal": 4, "emergency-stop": 2}


if TYPE_CHECKING:
    from fransys_model.kernel import Model
