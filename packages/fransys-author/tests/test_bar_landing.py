"""A bar function passed where a pin goes takes its next free screw (PE-BAR B2, A3)."""

import fransys_parts
import pytest
from fransys_author import AuthorError
from fransys_author.surface import design

from fransys_model.vocab import Conductor, Net, NetClass, Port, PortRole

WIRE = ("GNYE", 2.5)


@pytest.fixture(scope="module")
def demo():
    return fransys_parts.load("demo_parts")


def _lands(d, n):
    """The `n` landings of one design on `-PE1.pe`; the bar's ports are read from the draft."""
    pe1 = d.device("PE1", "DEMO-PEBAR-20")
    motors = [d.device(f"M{i}", "DEMO-MOTOR-4KW") for i in range(1, n + 1)]
    for m in motors:
        d.detail.wire(m.motor["PE"], pe1.pe, wire=WIRE)
    return pe1, motors


def _records(d, kind):
    return [r for r in d.draft().records() if isinstance(r, kind)]


def _bar_ends(d, bar_ports):
    return [
        (c.b if c.b in bar_ports else c.a)
        for c in _records(d, Conductor)
        if c.a in bar_ports or c.b in bar_ports
    ]


def test_twenty_landings_take_screws_one_to_twenty(demo):
    d = design(demo, place="C1")
    pe1, motors = _lands(d, 20)
    ports = {p.id: p.name for p in pe1.pe.pins}
    ends = _bar_ends(d, set(ports))
    assert sorted(ports[e] for e in ends) == sorted(str(i) for i in range(1, 21))
    assert len(set(ends)) == 20
    first = next(c for c in _records(d, Conductor) if pe1.pe.pins[0].id in (c.a, c.b))
    assert {first.a, first.b} == {pe1.pe.pins[0].id, motors[0].motor["PE"].id}


def test_the_twenty_first_landing_raises_and_names_the_count(demo):
    d = design(demo, place="C1")
    pe1, _ = _lands(d, 20)
    m21 = d.device("M21", "DEMO-MOTOR-4KW")
    with pytest.raises(AuthorError, match="20 screws"):
        d.detail.wire(m21.motor["PE"], pe1.pe, wire=WIRE)


def test_a_cut_to_length_bar_takes_twenty_five_landings(demo):
    d = design(demo, place="C1")
    pe1 = d.device("PE1", "DEMO-PEBAR-CUT")
    for i in range(1, 26):
        m = d.device(f"M{i}", "DEMO-MOTOR-4KW")
        d.detail.wire(m.motor["PE"], pe1.pe, wire=WIRE)
    bar_ports = [p for p in _records(d, Port) if p.function == pe1.pe.id]
    assert sorted(p.name for p in bar_ports) == sorted(str(i) for i in range(1, 26))
    assert len({p.id for p in bar_ports}) == 25
    assert len(_bar_ends(d, {p.id for p in bar_ports})) == 25


def test_a_one_ended_screen_lands_on_a_screw(demo):
    d = design(demo, place="C1")
    pe1 = d.device("PE1", "DEMO-PEBAR-20")
    w2 = d.cable("W2", "DEMO-CBL-2X2X0.75-SP")
    w2.core(5, pe1.pe)
    screws = {p.id for p in pe1.pe.pins}
    opened = [r for r in d.draft().records() if getattr(r, "at", None) in screws]
    assert len(opened) == 1


def test_each_taken_screw_is_in_a_pe_net(demo):
    d = design(demo, place="C1")
    pe1, _ = _lands(d, 3)
    nets = _records(d, Net)
    assert [n.net_class for n in nets] == [NetClass.PE] * 3
    assert {n.ports[0] for n in nets} == {p.id for p in pe1.pe.pins[:3]}


def test_a_cut_bar_screw_is_a_pe_port_with_no_template(demo):
    d = design(demo, place="C1")
    pe1 = d.device("PE1", "DEMO-PEBAR-CUT")
    d.detail.wire(d.device("M1", "DEMO-MOTOR-4KW").motor["PE"], pe1.pe, wire=WIRE)
    (screw,) = [p for p in _records(d, Port) if p.function == pe1.pe.id]
    assert (screw.name, screw.role, screw.template) == ("1", PortRole.PE, None)


def test_a_spare_parked_at_a_bar_takes_a_screw(demo):
    d = design(demo, place="C1")
    pe1 = d.device("PE1", "DEMO-PEBAR-20")
    d.cable("W1", "DEMO-CBL-4G1.5").spare(1, at=pe1.pe)
    first = pe1.pe.pins[0].id
    assert [r for r in d.draft().records() if getattr(r, "at", None) == first]


def test_a_non_bar_function_or_a_net_of_a_bar_raises(demo):
    d = design(demo, place="C1")
    m1, pe1 = d.device("M1", "DEMO-MOTOR-4KW"), d.device("PE1", "DEMO-PEBAR-20")
    with pytest.raises(AuthorError, match="is a function, not a pin"):
        d.detail.wire(m1.motor["PE"], m1.motor, wire=WIRE)
    with pytest.raises(AuthorError, match="name one pin"):
        d.detail.net("SIG", m1.motor["PE"], pe1.pe)
    d.detail.wire(m1.motor["PE"], pe1.pe, wire=WIRE)  # the same bar lands through d.wire
    assert len(_records(d, Net)) == 1


def _earthed(d):
    """Two motors' PE pins, for the `d.earth` tests."""
    m1 = d.device("M1", "DEMO-MOTOR-4KW")
    m2 = d.device("M2", "DEMO-MOTOR-4KW")
    return m1.motor["PE"], m2.motor["PE"]


def test_two_earth_calls_collect_into_the_one_pe_net(demo):
    d = design(demo, place="C1")
    a, b = _earthed(d)
    d.earth(a)
    d.earth(b, a)
    nets = [n for n in _records(d, Net) if n.net_class is NetClass.PE]
    assert [sorted(n.ports, key=str) for n in nets] == [sorted([a.id, b.id], key=str)]


def test_an_earth_call_after_the_draft_was_read_raises(demo):
    """The ordering trap: a net frozen early would silently lose the later call."""
    d = design(demo, place="C1")
    a, b = _earthed(d)
    d.earth(a)
    d.draft()
    with pytest.raises(AuthorError, match=r"d\.earth came after the draft was read"):
        d.earth(b)


def test_a_pe_net_after_earth_raises_naming_earth(demo):
    d = design(demo, place="C1")
    a, b = _earthed(d)
    d.earth(a)
    with pytest.raises(AuthorError, match=r"d\.earth"):
        d.detail.net("PE", b)


def test_earth_after_a_pe_net_raises_naming_earth(demo):
    d = design(demo, place="C1")
    a, b = _earthed(d)
    d.detail.net("PE", b)
    with pytest.raises(AuthorError, match=r"d\.earth"):
        d.earth(a)
