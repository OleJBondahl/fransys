"""EF-C2 part 3: a plug at `+EXT` wired to a relay coil and mated to a unit's boundary connector,
with the harness and the relay at a location other than the unit's, lays out without a
`LayoutError` ("two columns carry one authoring key") and with no ERROR finding.

Built through the `fransys` facade from `examples/demo-parts`.
"""

from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
import pytest
from _model_build_cover import layout_trigger_document

from fransys_model.kernel import Severity

_PROJECT: dict[str, Any] = {
    "title": "Two columns one key",
    "number": "P-1006",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


@pytest.mark.parametrize("coil_pin", ["A1", "A2"])
@pytest.mark.parametrize("relay_where", ["with the harness", "elsewhere"])
def test_a_plug_at_ext_wired_to_a_coil_and_mated_to_a_boundary_connector_lays_out(
    coil_pin, relay_where
) -> None:
    # Not failing-first: EF-A3's crash ("two columns carry one authoring key") does not reproduce
    # on this base; kept as a regression guard for the shape it described.
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-24", text="First issue", created="XX")
    cab = d.scope("cab").unit("demo-pump-cabinet", revision=1, interface="1")
    cab.revision(1, date="2026-01-01", text="First release", created="XX")
    c1, grp = cab.location("C1", "Cabinet"), d.group("PLC", "PLC")
    header = cab.item("DEMO-CONN-2P", tag="X1", at=c1, group=grp)
    cab.boundary(header)
    ext, field = d.location("EXT", "External"), d.group("EXT", "External")
    harness = d.harness(name="w1", tag="W1", at=ext, group=field)
    plug = d.item("DEMO-CONN-2P", tag="P1", parent=harness, at=ext, group=field)
    relay_at = ext if relay_where == "with the harness" else d.location("FLD", "Field")
    relay = d.item("DEMO-RLY-2CO-24", tag="K1", at=relay_at, group=field)
    d.wiring(colour="BU", gauge="0.5")(plug["1"], relay.fn("coil")[coil_pin])
    d.mate(plug, header)
    result = fr.build(parts, d.draft(), layout_trigger_document())
    assert not [f for f in result.findings if f.severity is Severity.ERROR]
