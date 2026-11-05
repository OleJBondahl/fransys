"""Field case: a second `d.earth` in one unit joins that unit's one PE net.
The bug (0.18.3): the second d.earth raised AuthorError "'U1/net/PE' already names a different net record", though d.earth takes no name.
Fixed by model-0236 (model-0236), a unit has one PE net and each further d.earth adds its pins to it."""

from typing import Any, NamedTuple

import fransys as fr
from _model_build_cover import unit_document

from fransys_model.vocab.tables import nets, ports


class _Top(NamedTuple):
    """A unit with no interface to hand back."""


@fr.unit("earth-top", revision=1, interface_version=1, date="2026-10-14", text="first", by="AB")
def _top(u: Any) -> _Top:
    m1 = u.device("M1", "DEMO-MOTOR-4KW")
    m2 = u.device("M2", "DEMO-MOTOR-4KW")
    m3 = u.device("M3", "DEMO-MOTOR-4KW")
    u.earth(m1.motor["PE"])
    u.earth(m2.motor["PE"], m3.motor["PE"])
    u.earth(u.device("M4", "DEMO-MOTOR-4KW").motor["PE"])
    return _Top()


def test_every_d_earth_call_in_a_unit_joins_one_pe_net() -> None:
    """The build succeeds, and the unit's one `PE` net holds all four pins."""
    d = fr.design("demo_parts")
    placed = d.add(_top, "U1")
    result = fr.build(d, unit_document(placed))
    top = [n for n in nets(result.model).values() if n.key[:3] == ("U1", "net", "PE")]
    assert not [f for f in result.findings if f.severity.value == "error"]
    assert len(top) == 1
    assert len(top[0].ports) == 4
    assert {ports(result.model)[p].name for p in top[0].ports} == {"PE"}
