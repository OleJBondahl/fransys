"""The one shape of a `PE` net: `earth_net` builds it, and each author site still writes it."""

import fransys_parts
import pytest
from fransys_author._earth_net import earth_net
from fransys_author.surface import design

from fransys_model.kernel import make_id
from fransys_model.vocab import Net, NetClass

WIRE = ("GNYE", 2.5)


@pytest.fixture(scope="module")
def demo():
    return fransys_parts.load("demo_parts")


def _pe_nets(d):
    nets = [r for r in d.draft().records() if isinstance(r, Net)]
    return [n for n in nets if n.net_class is NetClass.PE]


def _assert_pe_net(net, ports):
    assert net.name == "PE"
    assert net.net_class is NetClass.PE
    assert net.potential is None
    assert net.id == make_id(Net, net.key)
    assert sorted(net.ports) == sorted(ports)


def test_earth_net_is_the_literal_pe_net(demo):
    d = design(demo, place="C1")
    p = d.device("M1", "DEMO-MOTOR-4KW").motor["PE"].id
    key = ("scope", "net", "PE")
    expected = Net(
        id=make_id(Net, key),
        key=key,
        name="PE",
        net_class=NetClass.PE,
        ports=(p,),
        potential=None,
    )
    assert earth_net(key, (p,)) == expected


def test_d_earth_and_a_bar_screw_give_pe_nets(demo):
    d = design(demo, place="C1")
    a = d.device("M1", "DEMO-MOTOR-4KW").motor["PE"]
    b = d.device("M2", "DEMO-MOTOR-4KW").motor["PE"]
    d.earth(a, b)
    pe1 = d.device("PE1", "DEMO-PEBAR-20")
    d.detail.wire(d.device("M3", "DEMO-MOTOR-4KW").motor["PE"], pe1.pe, wire=WIRE)
    nets = _pe_nets(d)
    earthed = [n for n in nets if a.id in n.ports]
    (screw_net,) = [n for n in nets if pe1.pe.pins[0].id in n.ports]
    assert len(nets) == 2
    _assert_pe_net(earthed[0], (a.id, b.id))
    _assert_pe_net(screw_net, (pe1.pe.pins[0].id,))
