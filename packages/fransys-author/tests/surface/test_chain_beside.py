"""`d.layout.chain(..., beside=host)`: a chain joins its host by one or two end nets (CB1-3)."""

import pytest
from fransys_author import AuthorError
from fransys_author.surface import design
from fransys_author.surface.colours import BU

from fransys_model.layout import Chain
lazy from fransys_model.kernel import Draft

_WIRE = (BU, 0.75)


def _loop(parts: Draft, *, wire_first: bool = True):
    """A host coil and a two-coil branch from its A1 net round to its A2 net."""
    d = design(parts)
    host, one, two = (d.device(tag, "TEST-RLY-2CO") for tag in ("K1", "K2", "K3"))

    def wires() -> None:
        d.wire(host.coil["A1"], one.coil["A1"], wire=_WIRE)
        d.wire(one.coil["A2"], two.coil["A1"], wire=_WIRE)
        d.wire(two.coil["A2"], host.coil["A2"], wire=_WIRE)

    if wire_first:
        wires()
    return d, host, one, two, wires


def _chains(d) -> list[Chain]:
    return [r for r in d.draft().records() if isinstance(r, Chain)]


def test_a_chain_beside_its_host_records_the_host(parts: Draft) -> None:
    d, host, one, two, _ = _loop(parts)
    d.layout.chain(one.coil, two.coil, beside=host.coil)
    (chain,) = _chains(d)
    assert chain.beside == host.coil._fn.id


def test_a_chain_without_beside_records_none(parts: Draft) -> None:
    d, _, one, two, _ = _loop(parts)
    d.layout.chain(one.coil, two.coil)
    assert _chains(d)[0].beside is None


def test_a_reversed_chain_is_also_beside_its_host(parts: Draft) -> None:
    d, host, one, two, _ = _loop(parts)
    d.layout.chain(two.coil, one.coil, beside=host.coil)
    assert _chains(d)[0].beside == host.coil._fn.id


def test_beside_names_the_nets_when_no_end_net_is_the_hosts(parts: Draft) -> None:
    d, _host, one, two, _ = _loop(parts)
    other, far = d.device("K4", "TEST-RLY-2CO"), d.device("K5", "TEST-RLY-2CO")
    d.wire(other.coil["A1"], far.coil["A1"], wire=_WIRE)
    with pytest.raises(AuthorError, match=r"no end net is a net of that function.*K3"):
        d.layout.chain(one.coil, two.coil, beside=other.coil)


def test_one_end_net_on_the_host_is_enough(parts: Draft) -> None:
    d, host, one, two, _ = _loop(parts)
    far = d.device("K4", "TEST-RLY-2CO")
    d.wire(two.coil["A2"], far.coil["A1"], wire=_WIRE)  # the return leaves the host's net
    d.layout.chain(one.coil, two.coil, beside=host.coil)
    assert _chains(d)[0].beside == host.coil._fn.id


def test_a_one_pin_box_at_the_tail_joins_nothing(parts: Draft) -> None:
    d, host, one, _two, _ = _loop(parts)
    box = d.device("A1", "TEST-CLASH")
    d.wire(one.coil["A2"], box.co_1["13"], wire=_WIRE)
    d.layout.chain(one.coil, box.co_1, beside=host.coil)
    assert _chains(d)[0].beside == host.coil._fn.id


def test_beside_refuses_a_chain_that_leaves_by_more_than_two_nets(parts: Draft) -> None:
    d, host, one, _two, _ = _loop(parts)
    far = d.device("K4", "TEST-RLY-2CO")
    d.wire(host.coil["A1"], one.co_2["21"], wire=_WIRE)
    d.wire(host.coil["A2"], one.co_2["22"], wire=_WIRE)
    d.wire(far.coil["A1"], one.co_2["24"], wire=_WIRE)
    with pytest.raises(AuthorError, match=r"the chain leaves by 3 nets"):
        d.layout.chain(one.co_2, beside=host.coil)


def test_beside_refuses_both_end_nets_on_one_host_net(parts: Draft) -> None:
    d = design(parts)
    host, one, mid, two = (d.device(tag, "TEST-RLY-2CO") for tag in ("K1", "K2", "K3", "K4"))
    d.wire(host.coil["A1"], one.coil["A1"], wire=_WIRE)
    d.wire(one.coil["A2"], mid.coil["A1"], wire=_WIRE)
    d.wire(mid.coil["A2"], two.coil["A1"], wire=_WIRE)
    d.wire(two.coil["A2"], host.coil["A1"], wire=_WIRE)
    with pytest.raises(AuthorError, match=r"both end nets are the same net"):
        d.layout.chain(one.coil, mid.coil, two.coil, beside=host.coil)


def test_beside_refuses_an_end_with_two_nets_its_neighbour_lacks(parts: Draft) -> None:
    d = design(parts)
    host, one, two, far = (d.device(tag, "TEST-RLY-2CO") for tag in ("K1", "K2", "K3", "K4"))
    d.wire(host.coil["A1"], one.coil["A1"], wire=_WIRE)
    d.wire(one.coil["A2"], two.co_2["21"], wire=_WIRE)
    d.wire(two.co_2["22"], host.coil["A2"], wire=_WIRE)
    d.wire(two.co_2["24"], far.coil["A1"], wire=_WIRE)
    with pytest.raises(AuthorError, match=r"two or more nets its neighbour lacks"):
        d.layout.chain(one.coil, two.co_2, beside=host.coil)


def test_beside_before_the_wires_raises_wire_first(parts: Draft) -> None:
    d, host, one, two, wires = _loop(parts, wire_first=False)
    with pytest.raises(AuthorError, match="wire first"):
        d.layout.chain(one.coil, two.coil, beside=host.coil)
    wires()
    d.layout.chain(one.coil, two.coil, beside=host.coil)
