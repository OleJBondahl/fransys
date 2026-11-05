"""Field case: a green-yellow wire joins two lamp pins on a net that no declared net lists, with and without d.earth.
The bug: the build was silent, as GNYE_NOT_PE read only declared nets, so a signal on a green-yellow core raised nothing.
Fixed by model-0246, a green-yellow conductor on a non-PE net that no declared net lists is a WARNING GNYE_NOT_PE naming the fix."""

import fransys as fr
from fransys.colours import BU, GNYE


def _codes(*, earthed: bool) -> list[fr.Finding]:
    d = fr.design("demo_parts")
    a, b = (d.device(tag, "DEMO-LAMP-24") for tag in ("P1", "P2"))
    d.series(a[1], b[1], wire=(GNYE, 0.75))
    d.series(a[2], b[2], wire=(BU, 0.75))
    if earthed:
        d.earth(a[1], b[1])
    return [f for f in fr.build(d).findings if f.code == "GNYE_NOT_PE_UNDECLARED"]


def test_green_yellow_on_an_undeclared_net_warns_with_its_fix() -> None:
    (finding,) = _codes(earthed=False)
    assert finding.severity.name == "WARNING"
    assert "recolour" in finding.message
    assert "d.earth" in finding.message


def test_green_yellow_on_a_declared_pe_net_stays_silent() -> None:
    assert _codes(earthed=True) == []
