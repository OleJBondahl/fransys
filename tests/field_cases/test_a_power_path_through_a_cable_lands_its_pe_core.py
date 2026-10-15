"""Field case: a power path through a cable lands the cable's protective core on the load's PE pin.

The engineering shape: a three-phase motor M1 is fed from a 400 V supply through a breaker, a
contactor, an overload relay and a cable W1 whose fourth core is green-yellow:
`d.series(ac, q0.element, q1.main, f1.main, x1, w1, m1)`.

The bug: the core landed only when the strip before the cable had a PE terminal part. With no
strip, or a strip with no `pe=`, the build raised "has no PE terminal part" or "has no PE port",
and a later wire to the load's PE pin built an ERROR (GNYE_NOT_PE) in place of refusing.

Rule (author-0044): the core's far end lands on the load's PE port. Its near end lands on the next
free PE terminal of the strip before the cable, and otherwise is earthed as `d.earth` earths a pin
(PE-BAR B0). A cable with no protective core, or no PE port at either end, changes nothing. A later
wire to that core or port raises, naming the series that carried it.
"""

from typing import Any

import fransys as fr
import pytest
from fransys.colours import BK, GNYE


def _build(*, strip: str | None = "pe"):
    """The motor starter's power path; `strip` is `"pe"`, `"plain"` or `None` (no strip)."""
    d = fr.design("demo_parts")
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5")
    ac = d.ac_supply("400V", "230", x0[1], x0[2], x0[3], n=x0[4])
    q0, q1 = d.device("Q0", "DEMO-MCB-3P"), d.device("Q1", "DEMO-CTR-3P-24")
    f1 = d.device("F1", "DEMO-OVERLOAD-3P")
    w1 = d.cable("W1", "DEMO-CBL-4G1.5")
    m1 = d.device("M1", "DEMO-MOTOR-4KW")
    path: list[object] = [ac, q0.element, q1.main, f1.main]
    if strip is not None:
        pe: dict[str, Any] = {"pe": "DEMO-TB-PE-2.5"} if strip == "pe" else {}
        path.append(d.terminal_strip("X1", "DEMO-TB-2.5", **pe))
    d.series(*path, w1, m1, wire=(BK, 2.5))
    return d, w1, m1, x0


def _pe_core(d) -> list[tuple[str, str, str]]:
    """The ends and the word of the GNYE core of W1, wired or open."""
    model = fr.build(d).model
    (cable,) = fr.derive.cable_items(model)
    wired = [
        (r.end_a_designation, r.end_b_designation, "")
        for r in fr.derive.cable_rows(model, cable)
        if r.colour == GNYE
    ]
    opened = [
        (r.at_designation, "", "spare" if r.spare else "")
        for r in fr.derive.open_core_rows(model, cable)
        if r.colour == GNYE
    ]
    return wired + opened


def test_the_core_runs_from_the_strips_pe_terminal_to_the_motors_pe_pin() -> None:
    assert _pe_core(_build()[0]) == [("-M1:PE", "-X1:4", "")]


def test_a_strip_without_a_pe_part_earths_the_cores_near_end() -> None:
    d, *_ = _build(strip="plain")
    assert _pe_core(d) == [("-M1:PE", "", "")]
    assert not [f for f in fr.check(fr.build(d)) if "PE" in f.code or f.severity.name == "ERROR"]


def test_a_path_with_no_strip_earths_the_cores_near_end() -> None:
    d, *_ = _build(strip=None)
    assert _pe_core(d) == [("-M1:PE", "", "")]
    assert not [f for f in fr.check(fr.build(d)) if "PE" in f.code or f.severity.name == "ERROR"]


def test_a_load_and_a_strip_with_no_pe_port_leave_the_core_spare() -> None:
    d = fr.design("demo_parts")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5")
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"))
    w1 = d.cable("W1", "DEMO-CBL-4G1.5")
    d.series(dc.plus, x1, w1, d.device("H1", "DEMO-LAMP-24").lamp, dc.minus, wire=(BK, 0.75))
    assert _pe_core(d) == [("", "", "spare")]


def test_a_later_wire_to_the_motors_pe_pin_names_the_series() -> None:
    d, _, m1, x0 = _build()
    with pytest.raises(fr.AuthorError, match=r"M1.*d\.series\(400V, Q0, Q1, F1, X1, W1, M1\)"):
        d.detail.wire(m1.motor["PE"], x0[1], wire=(GNYE, 2.5))


def test_a_later_core_call_for_the_pe_core_names_the_series() -> None:
    _, w1, m1, x0 = _build()
    with pytest.raises(fr.AuthorError, match=r"d\.series\(400V, Q0, Q1, F1, X1, W1, M1\)"):
        w1.core(GNYE, m1.motor["PE"], x0[1])


def test_an_earthed_pe_core_is_not_listed_as_a_spare() -> None:
    model = fr.build(_build(strip=None)[0]).model
    (row,) = [r for r in fr.derive.core_list_rows(model) if r.colour == GNYE]
    assert row.note == ""


def test_a_parked_pe_core_is_listed_as_a_spare() -> None:
    d = fr.design("demo_parts")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5")
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"))
    d.series(
        dc.plus,
        x1,
        d.cable("W1", "DEMO-CBL-4G1.5"),
        d.device("H1", "DEMO-LAMP-24").lamp,
        dc.minus,
        wire=(BK, 0.75),
    )
    (row,) = [r for r in fr.derive.core_list_rows(fr.build(d).model) if r.colour == GNYE]
    assert row.note == "spare"


def test_a_second_wire_onto_the_motors_pe_pin_through_a_cable_names_the_series() -> None:
    d, _, m1, x0 = _build()
    w2 = d.cable("W2", "DEMO-CBL-4G1.5")
    with pytest.raises(fr.AuthorError, match=r"M1:PE already has the protective core.*d\.series"):
        w2.core(GNYE, m1.motor["PE"], x0[2])
