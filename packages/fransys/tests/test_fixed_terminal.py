"""API-CLARITY C6.11: a fixed terminal in a series (author-0046, amendment 5)."""

import fransys as fr
import pytest
from fransys.colours import BK, BU

from fransys_model.vocab import Conductor, WireFacet

PATH = (BU, 0.75)
POWER = (BK, 2.5)


def _wires(d) -> list:
    """Every wire record of the design, in the order it was written."""
    return [r for r in d.draft().records() if isinstance(r, Conductor | WireFacet)]


def _ends(d) -> set[frozenset[str]]:
    return {frozenset((r.from_, r.to)) for r in fr.derive.wire_rows(fr.build(d).model)}


def _lamp(d):
    g1 = d.device("G1", "DEMO-PSU-24")
    return g1, d.dc_supply("24VDC", g1), d.terminal_strip("X1", "DEMO-TB-2.5", 6)


def test_a_fixed_terminal_builds_the_detail_wire_script_byte_for_byte() -> None:
    """P21: the next free terminal instead of the fixed one makes the records differ."""
    d = fr.design("demo_parts")
    _, dc, x1 = _lamp(d)
    h1 = d.device("H1", "DEMO-LAMP-24")
    d.series(dc.plus, x1[3], h1.lamp, x1[4], dc.minus, wire=PATH)

    twin = fr.design("demo_parts")
    g1, _, y1 = _lamp(twin)
    h2 = twin.device("H1", "DEMO-LAMP-24")
    wire = twin.detail.wire
    wire(g1.output["+"], y1[3], wire=PATH)
    wire(y1[3].outer, h2.lamp["1"], wire=PATH)
    wire(h2.lamp["2"], y1[4], wire=PATH)
    wire(y1[4].outer, g1.output["-"], wire=PATH)
    assert _wires(d) == _wires(twin)
    assert len(_wires(d)) == 8
    assert {frozenset(("-G1:+", "-X1:3")), frozenset(("-H1:2", "-X1:4"))} <= _ends(d)


def test_a_fixed_terminal_counts_as_taken_for_a_strip_passed_whole() -> None:
    """P22: without the taken mark the whole strip takes terminal 1 again."""
    d = fr.design("demo_parts")
    _, dc, x1 = _lamp(d)
    h1, h2 = d.device("H1", "DEMO-LAMP-24"), d.device("H2", "DEMO-LAMP-24")
    d.series(dc.plus, x1[1], h1.lamp, dc.minus, wire=PATH)
    d.series(dc.plus, x1, h2.lamp, dc.minus, wire=PATH)
    ends = _ends(d)
    assert frozenset(("-G1:+", "-X1:2")) in ends
    assert frozenset(("-H2:1", "-X1:2")) in ends
    assert frozenset(("-H2:1", "-X1:1")) not in ends


def test_a_slice_is_a_multi_pole_element_in_order() -> None:
    """P23: the three terminals 1, 2, 3 of x1[1:4] carry the three phases like the script."""
    d = fr.design("demo_parts")
    xa = d.terminal_strip("XA", "DEMO-TB-2.5")
    a = d.ac_supply("A", "230", xa[1], xa[2], xa[3])
    x1, m1 = d.terminal_strip("X1", "DEMO-TB-2.5", 6), d.device("M1", "DEMO-MOTOR-4KW")
    d.series(a, x1[1:4], m1, wire=POWER)

    twin = fr.design("demo_parts")
    xb = twin.terminal_strip("XA", "DEMO-TB-2.5")
    twin.ac_supply("A", "230", xb[1], xb[2], xb[3])
    y1, m2 = twin.terminal_strip("X1", "DEMO-TB-2.5", 6), twin.device("M1", "DEMO-MOTOR-4KW")
    for number, motor in zip((1, 2, 3), "UVW", strict=True):
        twin.detail.wire(xb[number].outer, y1[number], wire=POWER)
        twin.detail.wire(y1[number].outer, m2.motor[motor], wire=POWER)
    assert _ends(d) == _ends(twin)
    assert len(_ends(d)) == 6


@pytest.mark.parametrize(
    ("pick", "text"),
    [
        (lambda x1: x1[2:2], r"X1\[2:2\] holds no terminal"),
        (lambda x1: x1[4:2], r"X1\[4:2\] holds no terminal"),
        (lambda x1: x1[1:4:2], r"X1\[a:b\] takes no step"),
        (lambda x1: x1[1:], r"X1\[a:b\] names both ends"),
        (lambda x1: x1[0:2], r"X1\[0:2\] starts below terminal 1"),
        (lambda x1: x1[5:8], r"X1 has 6 terminals; X1\[5:8\] reaches past the last"),
    ],
)
def test_a_slice_that_names_no_terminals_raises_and_names_the_form(pick, text: str) -> None:
    """P23: an empty slice and a step each raise, and so do bounds past the strip."""
    x1 = fr.design("demo_parts").terminal_strip("X1", "DEMO-TB-2.5", 6)
    with pytest.raises(fr.AuthorError, match=text):
        pick(x1)


def test_a_device_pin_in_a_series_still_raises_a_pin_is_one_wire() -> None:
    d = fr.design("demo_parts")
    q1, k1 = d.device("Q1", "DEMO-MCB-3P"), d.device("K1", "DEMO-CTR-3P-24")
    with pytest.raises(fr.AuthorError, match="a pin is one wire"):
        d.series(q1.element, k1.main["1"], wire=POWER)


def _selector(d):
    k1 = d.device("K1", "DEMO-RLY-4CO-24")
    return k1, d.poles(k1.co_1, k1.co_2, k1.co_3, selector=True)


def test_a_tuple_of_fixed_terminals_on_three_strips_is_a_three_pole_element() -> None:
    """P24: a three-pole selector over (x1[3], x2[3], x3[3]) wires as its script does."""
    d = fr.design("demo_parts")
    strips = [d.terminal_strip(f"X{n}", "DEMO-TB-2.5", 4) for n in (1, 2, 3)]
    _, q = _selector(d)
    d.series(q.nc, tuple(x[3] for x in strips), wire=POWER)

    twin = fr.design("demo_parts")
    mirror = [twin.terminal_strip(f"X{n}", "DEMO-TB-2.5", 4) for n in (1, 2, 3)]
    k2, _ = _selector(twin)
    for pole, strip in enumerate(mirror, start=1):
        twin.detail.wire(getattr(k2, f"co_{pole}")[f"{pole}1"], strip[3], wire=POWER)
    assert _wires(d) == _wires(twin)
    assert len(_wires(d)) == 6


def test_a_tuple_in_order_on_one_strip_raises_and_names_the_slice() -> None:
    """P24: (x1[1], x1[2]) is x1[1:3]; accepting it would leave two ways to write one thing."""
    d = fr.design("demo_parts")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 4)
    _, q = _selector(d)
    with pytest.raises(fr.AuthorError, match=r"run in order on one strip: write x1\[1:3\]"):
        d.series(q.nc, (x1[1], x1[2]), wire=POWER)


def test_a_tuple_with_a_gap_or_two_strips_is_accepted_and_a_stranger_raises() -> None:
    d = fr.design("demo_parts")
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 6)
    _, q = _selector(d)
    d.series(q.nc, (x1[1], x1[3], x1[5]), wire=POWER)
    assert len(_wires(d)) == 6
    with pytest.raises(fr.AuthorError, match=r"holds fixed terminals .*, not str"):
        d.series(q.no, (x1[2], "X"), wire=POWER)


def test_the_same_terminal_twice_in_a_tuple_raises_and_names_it() -> None:
    """FIX P2: (x1[3], x2[3], x1[3]) would put one terminal on two poles."""
    d = fr.design("demo_parts")
    x1, x2 = (d.terminal_strip(f"X{n}", "DEMO-TB-2.5", 4) for n in (1, 2))
    _, q = _selector(d)
    with pytest.raises(fr.AuthorError, match=r"names terminal X1:3 twice"):
        d.series(q.nc, (x1[3], x2[3], x1[3]), wire=POWER)
