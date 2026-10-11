"""`d.layout.chain(..., beside=host)`: the chain's end nets must be two nets of the host."""

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


def test_beside_names_the_nets_when_the_ends_are_not_the_hosts(parts: Draft) -> None:
    d, _host, one, two, _ = _loop(parts)
    other = d.device("K4", "TEST-RLY-2CO")
    d.wire(two.coil["A2"], other.coil["A1"], wire=_WIRE)
    with pytest.raises(AuthorError, match=r"end nets .*K3.*not two nets of that function"):
        d.layout.chain(one.coil, two.coil, beside=other.coil)


def test_beside_before_the_wires_raises_wire_first(parts: Draft) -> None:
    d, host, one, two, wires = _loop(parts, wire_first=False)
    with pytest.raises(AuthorError, match="wire first"):
        d.layout.chain(one.coil, two.coil, beside=host.coil)
    wires()
    d.layout.chain(one.coil, two.coil, beside=host.coil)
