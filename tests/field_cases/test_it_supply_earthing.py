"""Field case: an IT (floating) supply is declared through the public API.

The engineering shape: a 24 V DC supply from a PSU that is not earthed on either rail, and an
AC supply that is earthed (the default).

The bug: `Earthing` was not on the surface, so a consumer script could not say `IT`, and the
supply was declared earthed. The rule (EA15, G25): `fr.IT` and `fr.EARTHED` are bare constants,
as `fr.DO` is: `earthing=fr.IT`. `Earthing` itself stays unpublished.
"""

import fransys as fr

from fransys_model.vocab import Earthing
from fransys_model.vocab.tables import supply_systems


def _earthing(system: Earthing) -> dict[str, Earthing]:
    """Each supply's name to its earthing, after a build."""
    d = fr.design("demo_parts", place="CAB")
    d.location("CAB", "Cabinet")
    psu = d.device("T1", "DEMO-PSU-24")
    d.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
    d.dc_supply("CONTROL", psu, earthing=system)
    return {s.name: s.earthing for s in supply_systems(fr.build(d).model).values()}


def test_it_reaches_the_model() -> None:
    """`earthing=fr.IT` is stored as IT; the default and `fr.EARTHED` stay earthed."""
    assert _earthing(fr.IT) == {"MAINS": Earthing.EARTHED, "CONTROL": Earthing.IT}
    assert _earthing(fr.EARTHED)["CONTROL"] is Earthing.EARTHED
