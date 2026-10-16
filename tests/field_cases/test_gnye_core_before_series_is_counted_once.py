"""Field case: a GNYE core wired before a series is not counted again as a pole core.

The engineering shape: a four-core cable with three non-earth cores and one GNYE core. The earth
core is wired first, from a strip's PE terminal to the load's PE, with `cable.core`. A three-pole
series then uses the three other cores, as the guide's series page "Earth pins" shows.

The bug (0.19.9): the already-wired GNYE core was counted twice, so the series was refused with
"W1 has 2 non-earth cores for 3 poles and no PE end...". Fixing work order GNYE-SERIES (patch
0.19.10). Demo parts: DEMO-TB-2.5, DEMO-CBL-4G1.5.
"""

import fransys as fr
from fransys.colours import GNYE


def test_gnye_core_wired_before_a_series_is_counted_once() -> None:
    d = fr.design("demo_parts")
    x = d.terminal_strip("X", "DEMO-TB-2.5", 4)
    ext = d.device("EXT", None, external=True, pins=("L1", "L2", "L3", "PE"))
    w = d.cable("W1", "DEMO-CBL-4G1.5", external=True)
    w.core(GNYE, x[4], ext["PE"])
    d.series(x[1:4], w, (ext["L1"], ext["L2"], ext["L3"]))

    b = fr.build(d)

    assert not [f for f in b.findings if f.severity is fr.Severity.ERROR]
    assert [(r.core, r.colour, r.end_a, r.end_b) for r in fr.derive.core_list_rows(b.model)] == [
        (1, "BN", "-EXT:L1", "-X:1"),
        (2, "BK", "-EXT:L2", "-X:2"),
        (3, "GY", "-EXT:L3", "-X:3"),
        (4, "GNYE", "-EXT:PE", "-X:4"),
    ]
