"""Field case: a control path from the 24 V rail to 0 V, colours by what each wire carries.

A rail feeds a bridged feed-rail run, two contacts in series, a coil and a return terminal
strip to 0 V. The house rule is red at the supply potential, black at 0 V, white otherwise.
A second path runs rail, fuse, contact, coil, 0 V: the fuse ends the supply potential.

The bug: one `wire=` colours every hop of a `d.series`, so the colour cannot change by hop and
the author wrote about 40 single `d.wire` calls instead.

Fixing decision: author-0039 (SERIES-GAPS S1, S2).
"""

import fransys as fr
from fransys.colours import BK, RD, WH


def _house_design():
    return fr.design(
        "demo_parts",
        wiring={
            fr.DC_SUPPLY: (RD, 0.75),
            fr.DC_CONTROL: (WH, 0.75),
            fr.DC_GROUND: (BK, 0.75),
        },
    )


def _rows(d) -> list:
    return list(fr.derive.wire_rows(fr.build(d).model))


def _check(rows: list, a: str, b: str, colour) -> None:
    found = [r for r in rows if {r.from_, r.to} == {a, b}]
    assert len(found) == 1, f"{a} to {b}: {[(r.from_, r.to) for r in rows]}"
    assert (found[0].colour, found[0].cross_section_mm2) == (colour, 0.75), f"{a} to {b}"


def test_a_path_through_a_run_two_contacts_and_a_coil_changes_colour_by_potential() -> None:
    d = _house_design()
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"))
    run = d.terminal_strip("X1", "DEMO-TB-2.5").run("24V", 2, bridged=True)
    x2 = d.terminal_strip("X2", "DEMO-TB-2.5")
    s1, s2 = d.device("S1", "DEMO-CTR-BLOCK-1NO1NC"), d.device("S2", "DEMO-CTR-BLOCK-1NO1NC")
    k1 = d.device("K1", "DEMO-RLY-2CO-24")
    d.series(dc.plus, run, s1.no, s2.nc, k1.coil, x2, dc.minus)
    rows = _rows(d)
    _check(rows, "-G1:+", "-X1:24V:1", RD)
    _check(rows, "-X1:24V:1", "-S1:53", RD)
    _check(rows, "-S1:54", "-S2:61", WH)
    _check(rows, "-S2:62", "-K1:A1", WH)
    _check(rows, "-K1:A2", "-X2:1", BK)
    _check(rows, "-X2:1", "-G1:-", BK)


def test_a_fuse_ends_the_supply_potential_so_the_wires_after_it_are_control_wires() -> None:
    d = _house_design()
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"))
    f1 = d.device("F1", "DEMO-MCB-C6")
    s3 = d.device("S3", "DEMO-CTR-BLOCK-1NO1NC")
    k2 = d.device("K2", "DEMO-RLY-2CO-24")
    d.series(dc.plus, f1.element, s3.no, k2.coil, dc.minus)
    rows = _rows(d)
    _check(rows, "-G1:+", "-F1:1", RD)
    _check(rows, "-F1:2", "-S3:53", WH)
    _check(rows, "-S3:54", "-K2:A1", WH)
    _check(rows, "-K2:A2", "-G1:-", BK)
