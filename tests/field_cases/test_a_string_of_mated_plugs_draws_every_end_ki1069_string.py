"""Field case: one string of a cabinet unit whose board and precharge plugs mate through connectors (KI-1069, R2593, R2598).
The bug: CONNECTION_NOT_DRAWN on six plug pins (S1 plugs 1, 2, 3, 6 and 3, and a sensor plug 2); dropping any one plug gives none.
Fixed: KI1069-B (layout-0628, R2596); KI-1069 stays open until the real cabinet shows none. Anchors KI-1090: INK_WITHOUT_CONDUCTOR (R2822)."""

import fransys as fr
import pytest
from _expected_codes import expect_codes
from _model_build_cover import unit_document
from ki1069_string_shape import build


@pytest.mark.timeout(600)
def test_a_string_of_mated_plugs_draws_every_end() -> None:
    d = fr.design("ki1069_string_parts")
    d.add(build, "U1")
    d.layout.profile(hide_unused_pins=True)
    result = fr.build(d, unit_document("dev-top"))
    expect_codes(result, "CONNECTION_NOT_DRAWN")  # KI-1405 (ARM-SCOPE): 14 bare grounds on the connector pins of two drawing sets
    assert sum(f.code == "CONNECTION_NOT_DRAWN" for f in result.findings) == 14


# TEXT_HIDES_TEXT: a falling stock of this file's builds, KI-1133 (R2647, TEXT-WIRE P0).


# CARD_OVERFULL: a looks finding of this file's builds, on KI-1378 (R3557).
