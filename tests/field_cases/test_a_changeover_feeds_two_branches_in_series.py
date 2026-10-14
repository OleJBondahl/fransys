"""Field case: one relay changeover feeds two coil branches, each a series from one throw.

The common of the changeover is on the 24 V rail. Its make throw feeds one coil and its break
throw feeds another, each coil returning to 0 V.

The bug: a changeover could not be a series element ("1 poles into 2: name the pins"), so each
branch needed a `d.wire` with pin names, and the common's wire was written by hand.

Fixing decision: author-0039 (SERIES-GAPS S7).
"""

import fransys as fr


def changeover_design():
    """The built-from design, for the page render of Part 4."""
    d = fr.design("demo_parts")
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"))
    k1 = d.device("K1", "DEMO-RLY-2CO-24")
    k2 = d.device("K2", "DEMO-CTR-3P-24")
    k3 = d.device("K3", "DEMO-RLY-2CO-24")
    d.series(dc.plus, k1.co_1.no, k2.coil, dc.minus, wire=0.75)
    d.series(k1.co_1.nc, k3.coil, dc.minus, wire=0.75)
    return d


def _ends(d) -> set[frozenset]:
    return {frozenset((r.from_, r.to)) for r in fr.derive.wire_rows(fr.build(d).model)}


def test_each_throw_feeds_its_own_coil_and_both_return_to_zero_volts() -> None:
    ends = _ends(changeover_design())
    for a, b in (
        ("-G1:+", "-K1:11"),
        ("-K1:14", "-K2:A1"),
        ("-K1:12", "-K3:A1"),
        ("-K2:A2", "-G1:-"),
        ("-K3:A2", "-G1:-"),
    ):
        assert frozenset((a, b)) in ends, f"{a} to {b}"


def test_the_common_is_wired_once() -> None:
    rows = fr.derive.wire_rows(fr.build(changeover_design()).model)
    assert sum("-K1:11" in (r.from_, r.to) for r in rows) == 1
