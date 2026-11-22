"""Field case: one string of a cabinet unit whose board and precharge plugs mate through connectors (KI-1069, R2593, R2598).
The bug: CONNECTION_NOT_DRAWN on six plug pins (S1 plugs 1, 2, 3, 6 and 3, and a sensor plug 2); dropping any one plug gives none.
Fixed: KI1069-B (layout-0628, R2596); KI-1069 stays open until the real cabinet shows none."""

import fransys as fr
import pytest
from _model_build_cover import unit_document
from ki1069_string_shape import build


@pytest.mark.timeout(600)
def test_a_string_of_mated_plugs_draws_every_end() -> None:
    d = fr.design("ki1069_string_parts")
    d.add(build, "U1")
    d.layout.profile(hide_unused_pins=True)
    result = fr.build(d, unit_document("dev-top"))
    undrawn = [f for f in result.findings if f.code == "CONNECTION_NOT_DRAWN"]
    assert not undrawn, f"{len(undrawn)} CONNECTION_NOT_DRAWN"


# TEXT_HIDES_TEXT: a falling stock of this file's builds, KI-1133 (R2647, TEXT-WIRE P0).
