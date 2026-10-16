"""Field case: two GNYE spellings that failed before 0.19.9 name the guide's order as the fix.

Engineering shape: a 4-core cable (3 non-earth cores and one GNYE core) joins a terminal strip to
an external load with L1, L2, L3 and PE. The guide's series page ("Earth pins") wires the GNYE core
first with `core(GNYE, a, b)` and then writes the 3-pole series.

Not regressions (both failed on 0.19.8 as well): the series first and the GNYE core after it, and
the PE pin passed as a fourth pole of the series. Each must refuse and say how to write it.

Fixing work order: GNYE-SERIES (patch 0.19.10).
"""

import fransys as fr
import pytest
from fransys.colours import GNYE
from fransys_author import AuthorError

_GUIDE = "core(GNYE, a, b) before the series"


def _parts() -> tuple:
    d = fr.design("demo_parts")
    x = d.terminal_strip("X", "DEMO-TB-2.5", 4)
    ext = d.device("EXT", None, external=True, pins=("L1", "L2", "L3", "PE"))
    w = d.cable("W1", "DEMO-CBL-4G1.5", external=True)
    return d, x, ext, w


def test_a_gnye_core_after_the_series_names_the_guides_order() -> None:
    d, x, ext, w = _parts()
    d.series(x[1:4], w, (ext["L1"], ext["L2"], ext["L3"]))
    with pytest.raises(AuthorError, match=r"already wired or marked spare") as raised:
        w.core(GNYE, x[4], ext["PE"])
    assert _GUIDE in str(raised.value)


def test_the_pe_pin_as_a_fourth_pole_names_the_guides_order() -> None:
    d, x, ext, w = _parts()
    with pytest.raises(AuthorError, match=r"4 poles") as raised:
        d.series(x[1:5], w, (ext["L1"], ext["L2"], ext["L3"], ext["PE"]))
    assert _GUIDE in str(raised.value)
