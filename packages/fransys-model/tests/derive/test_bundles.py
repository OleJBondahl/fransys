"""A bundle is the nets that connect the poles of one multi-pole device: one trunk, one lane a pole.

Three-phase feeds from a 3-pole breaker are the shape. A crossed feed is a bundle whose
crossed end carries the permutation; a ragged feed is in none.
"""

from itertools import pairwise

import fransys as fr
import pytest
from fransys.colours import BU

from fransys_model.derive.bundles import Bundle, bundle_of, bundles
from fransys_model.vocab.tables import functions, items, ports
lazy from fransys_model.kernel import Id
lazy from fransys_model.vocab import Port

_MCB = "DEMO-MCB-3P"
_MOTOR = "DEMO-MOTOR-4KW"
_WIRE = (BU, 2.5)
_PHASES = (("2", "U"), ("4", "V"), ("6", "W"))


def _port(model: fr.Model, tag: str, name: str) -> Id[Port]:
    """The port `name` of the item whose last key part is `tag`."""
    (found,) = [
        p.id
        for p in ports(model).values()
        if p.name == name and items(model)[functions(model)[p.function].item].key[-1] == tag
    ]
    return found


def _feed() -> fr.Design:
    """Q1's load side to three motors by direct wires, M1 to M2 to M3 on every phase."""
    d = fr.design("demo_parts")
    q = d.device("Q1", _MCB)
    motors = [d.device(f"M{n}", _MOTOR) for n in (1, 2, 3)]
    for load, pin in _PHASES:
        d.detail.wire(q.element[load], motors[0][pin], wire=_WIRE)
        for near, far in pairwise(motors):
            d.detail.wire(near[pin], far[pin], wire=_WIRE)
    return d


@pytest.fixture(scope="module")
def feed() -> fr.Model:
    """The three-phase feed model."""
    return fr.build(_feed()).model


def _lane(model: fr.Model, tag: str, name: str) -> tuple[Id[Port], int]:
    found = bundle_of(model, _port(model, tag, name))
    assert found is not None, f"{tag}:{name} is in no bundle"
    return found


def test_a_three_phase_feed_is_one_bundle_in_phase_order(feed: fr.Model) -> None:
    """Catches a bundle split by motor or by phase, or poles out of L1 L2 L3 order."""
    load = _lane(feed, "Q1", "2")[0]
    (bundle,) = [b for b in bundles(feed) if b.id == load]
    assert isinstance(bundle, Bundle)
    assert [n.pole for n in bundle.nets] == [0, 1, 2]
    for tag in ("Q1", "M1", "M2", "M3"):
        for (load_pin, motor_pin), pole in zip(_PHASES, range(3), strict=True):
            pin = load_pin if tag == "Q1" else motor_pin
            assert _lane(feed, tag, pin) == (load, pole)


def test_a_net_that_is_no_phase_is_in_no_bundle(feed: fr.Model) -> None:
    """Catches a PE net, or a port of no net, handed a lane (the phases above are in one)."""
    assert bundle_of(feed, _port(feed, "M1", "PE")) is None
    assert _lane(feed, "M1", "U")[1] == 0


def test_the_line_side_of_the_breaker_is_its_own_bundle(feed: fr.Model) -> None:
    """The breaker alone makes its line side a bundle (poles 0 to 2), apart from its load side."""
    line = {_lane(feed, "Q1", pin) for pin in ("1", "3", "5")}
    assert {pole for _, pole in line} == {0, 1, 2}
    assert len({bundle for bundle, _ in line}) == 1
    assert line.isdisjoint({_lane(feed, "Q1", pin) for pin in ("2", "4", "6")})


def test_a_feed_through_in_line_terminals_stays_one_trunk() -> None:
    """The closure joins a terminal's two sides, so Q1 -> X2 -> M1 is one bundle, not three."""
    d = fr.design("demo_parts")
    q, m = d.device("Q1", _MCB), d.device("M1", _MOTOR)
    x = d.terminal_strip("X2", "DEMO-TB-2.5")
    for number, (load, pin) in enumerate(_PHASES, 1):
        d.detail.wire(q.element[load], x[number], wire=_WIRE)
        d.detail.wire(x[number], m[pin], wire=_WIRE)
    model = fr.build(d).model
    (trunk,) = {_lane(model, "Q1", load)[0] for load, _ in _PHASES}
    assert [_lane(model, "M1", pin) for _, pin in _PHASES] == [(trunk, n) for n in range(3)]


def _two_breakers(order: tuple[tuple[str, str], ...]) -> fr.Model:
    """Q1's load pins wired to Q2's line pins as `order` says."""
    d = fr.design("demo_parts")
    q1, q2 = d.device("Q1", _MCB), d.device("Q2", _MCB)
    for load, line in order:
        d.detail.wire(q1.element[load], q2.element[line], wire=_WIRE)
    return fr.build(d).model


def test_crossed_phases_between_two_breakers_are_a_bundle_with_a_permutation() -> None:
    """Catches a crossed net left out, or the reversal lost; the straight feed carries no cross."""
    straight = _two_breakers((("2", "1"), ("4", "3"), ("6", "5")))
    assert [_lane(straight, "Q2", pin)[1] for pin in ("1", "3", "5")] == [0, 1, 2]
    (plain,) = [b for b in bundles(straight) if b.id == _lane(straight, "Q2", "1")[0]]
    assert plain.crosses == ()
    crossed = _two_breakers((("2", "5"), ("4", "3"), ("6", "1")))  # the reversing swap
    lanes = {_lane(crossed, t, p) for t, p in (("Q1", "2"), ("Q1", "4"), ("Q1", "6"))}
    assert {pole for _, pole in lanes} == {0, 1, 2}
    assert {_lane(crossed, "Q2", pin) for pin in ("1", "3", "5")} == lanes
    (bundle,) = [b for b in bundles(crossed) if b.id == next(iter(lanes))[0]]
    (cross,) = bundle.crosses
    assert [p.lane for p in cross.poles] == [2, 1, 0]
    assert [p.local for p in cross.poles] == [0, 1, 2]
    ends = {
        ports(crossed)[_port(crossed, tag, pin)].function for tag, pin in (("Q1", "2"), ("Q2", "1"))
    }
    assert cross.function in ends


def test_a_trunk_with_two_nets_on_one_pole_is_in_no_bundle() -> None:
    """Catches a bundle with a repeated pole index (a staircase of breakers: pole 0, 1, 0)."""
    d = fr.design("demo_parts")
    q = [d.device(f"Q{n}", _MCB) for n in (1, 2, 3, 4)]
    for a, pin_a, b, pin_b in ((0, "2", 1, "1"), (1, "3", 2, "4"), (2, "2", 3, "1")):
        d.detail.wire(q[a].element[pin_a], q[b].element[pin_b], wire=_WIRE)
    model = fr.build(d).model
    assert bundle_of(model, _port(model, "Q1", "2")) is None
    assert _lane(model, "Q1", "1")[1] == 0  # a breaker's untouched side is a bundle still


def test_the_wired_poles_of_a_half_wired_trunk_are_the_bundle() -> None:
    """Catches unwired poles that repeat a pole index and sink the trunk (poles 0 and 1 wired)."""
    model = _two_breakers((("2", "1"), ("4", "3")))
    wired = {_lane(model, "Q1", "2"), _lane(model, "Q1", "4")}
    assert wired == {_lane(model, "Q2", "1"), _lane(model, "Q2", "3")}
    assert {pole for _, pole in wired} == {0, 1}
    assert len({bundle for bundle, _ in wired}) == 1
    (bundle,) = [b for b in bundles(model) if b.id == _lane(model, "Q1", "2")[0]]
    assert len(bundle.nets) == 2  # the unwired pole 2 is not a member
    assert bundle_of(model, _port(model, "Q1", "6")) is None


def test_one_wired_pole_is_no_bundle() -> None:
    """Catches a lone wired pole bundled with the unwired poles beside it."""
    d = fr.design("demo_parts")
    q = d.device("Q1", _MCB)
    x = d.terminal_strip("X2", "DEMO-TB-2.5")
    d.detail.wire(q.element["4"], x[1], wire=_WIRE)
    model = fr.build(d).model
    assert bundle_of(model, _port(model, "Q1", "4")) is None
    assert bundle_of(model, _port(model, "Q1", "2")) is None


def test_nets_that_part_partway_are_one_bundle_over_the_span_they_share() -> None:
    """Q1 feeds M1 on two phases and M2 on the third: one bundle at Q1, poles 0, 1, 2."""
    d = fr.design("demo_parts")
    q = d.device("Q1", _MCB)
    m1, m2 = d.device("M1", _MOTOR), d.device("M2", _MOTOR)
    d.detail.wire(q.element["2"], m1["U"], wire=_WIRE)
    d.detail.wire(q.element["4"], m1["V"], wire=_WIRE)
    d.detail.wire(q.element["6"], m2["W"], wire=_WIRE)
    model = fr.build(d).model
    lanes = [_lane(model, "Q1", pin) for pin in ("2", "4", "6")]
    assert [pole for _, pole in lanes] == [0, 1, 2]
    assert len({bundle for bundle, _ in lanes}) == 1
    assert _lane(model, "M2", "W") == lanes[2]


def test_a_function_with_no_pole_link_bundles_by_its_fallback_poles() -> None:
    """A 4-pin connector pairs (1, 2) and (3, 4): nets from pins 1 and 3 are poles 0 and 1."""
    d = fr.design("demo_parts")
    a, b = d.device("J1", "DEMO-CONN-4P"), d.device("J2", "DEMO-CONN-4P")
    d.detail.wire(a[1], b[1], wire=_WIRE)
    d.detail.wire(a[3], b[3], wire=_WIRE)
    model = fr.build(d).model
    (trunk,) = {_lane(model, "J1", pin)[0] for pin in ("1", "3")}
    assert [_lane(model, "J1", pin) for pin in ("1", "3")] == [(trunk, 0), (trunk, 1)]
    assert [_lane(model, "J2", pin) for pin in ("1", "3")] == [(trunk, 0), (trunk, 1)]
