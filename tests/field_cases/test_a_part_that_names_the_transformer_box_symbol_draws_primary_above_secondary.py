"""Field case: a transformer part that names `symbol = "transformer-box"` draws the box with the winding sign, primary pins above, secondary below.
The ask (legacy, R2067): a transformer symbol that is a box with a transformer sign inside, as a psu is; chosen by the part's own `symbol`."""

import fransys as fr
from _drawn_pages import drawn_pages
from _model_build_cover import unit_document

from electrical_symbols import LIBRARY
from fransys_layout.drawing import port_points

KEY = "transformer-box"


def _drawn() -> list[dict[str, float]]:
    """The y of each port of every transformer-box symbol the build drew, by symbol port id."""
    d = fr.design("demo_parts", "tbox_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        t = d.device("T1", "TBOX-TRAFO")
        x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 2)
        x2 = d.terminal_strip("X2", "DEMO-TB-2.5", 2)
        d.series(x1[1].inner, t.primary["1U"], wire=("BK", 0.75))
        d.series(x1[2].inner, t.primary["1V"], wire=("BK", 0.75))
        d.series(t.secondary["2U"], x2[1].inner, wire=("BK", 0.75))
        d.series(t.secondary["2V"], x2[2].inner, wire=("BK", 0.75))
    result = fr.build(d, unit_document(cab))
    found = [s for page in drawn_pages(result.model).values() for s in page.symbols if s.key == KEY]
    return [{port: at[1] for at, port in port_points(s, LIBRARY)} for s in found]


def test_the_primary_pins_stand_above_the_secondary_pins() -> None:
    drawn = _drawn()
    assert len(drawn) == 1
    (ys,) = drawn
    assert set(ys) == {"p1", "p2", "s1", "s2"}
    assert max(ys["p1"], ys["p2"]) < min(ys["s1"], ys["s2"])
