"""Tests: `device_chains` finds the devices that chain, in order (LC2, LC3, LC5, layout-0215)."""

from plant import Plant

from fransys_model.derive import ChainCandidate, DeviceChains, device_chains
from fransys_model.kernel import Id, make_id
from fransys_model.vocab.core import Item, Port


def _item(n: int) -> Id[Item]:
    return make_id(Item, (f"D{n}",))


class _Block:
    """Devices `D<n>`: a box with ports `up` and `down`, and a connector beside it."""

    def __init__(self) -> None:
        self.plant = Plant()
        self.candidates: list[ChainCandidate] = []
        self.wires: list[tuple[Id[Port], Id[Port]]] = []

    def device(
        self, n: int, *, rank: int = 1, connector: bool = True, place: int = 1, boxed: bool = True
    ) -> None:
        """Add device `n` with designation rank `rank` in place `place`."""
        names = (("box", ("up", "down")), ("con", ("c",)))[: 2 if connector else 1]
        for name, ports in names:
            self.plant.pin(f"D{n}", name, ports[0])
            self.candidates.append(
                ChainCandidate(
                    function=Plant.function_id(f"D{n}", name),
                    item=_item(n),
                    key=(f"D{n}", name),
                    connector=name == "con",
                    boxed=boxed and name == "box",
                    plain=True,
                    group_path=(),
                    in_unit=None,
                    location_path=(make_id(Item, (f"L{place}",)),),
                    rank=rank,
                    ports=tuple(self.port(n, p, name) for p in ports),
                )
            )

    def port(self, n: int, name: str, function: str = "box") -> Id[Port]:
        """The port `name` of device `n`'s `function`."""
        return self.plant.pin(f"D{n}", function, name)

    def wire(self, upper: int, lower: int) -> None:
        """A conductor from `upper`'s down port to `lower`'s up port."""
        self.wires.append((self.port(upper, "down"), self.port(lower, "up")))

    def run(self, netted: frozenset[Id[Port]] = frozenset()) -> DeviceChains:
        """`device_chains` over the block as built; every wired port is wired."""
        wired = frozenset(p for w in self.wires for p in w)
        return device_chains(self.plant.model(), self.candidates, self.wires, netted, wired)


def _line(*ranks: int) -> _Block:
    """Devices 1..n wired in a line, device k of designation rank `ranks[k - 1]`."""
    block = _Block()
    for n, rank in enumerate(ranks, 1):
        block.device(n, rank=rank)
    for n in range(1, len(ranks)):
        block.wire(n, n + 1)
    return block


def test_hop_to_hop_devices_form_one_chain_led_by_the_lowest_designation_end() -> None:
    """Devices 1-2-3 wired in a line; device 3 ranks lowest, so it leads."""
    found = _line(3, 1, 2).run()
    (chain,) = found.chains
    assert chain.members == (_item(3), _item(2), _item(1))
    assert chain.closing is None
    assert [(h.feeder, h.fed) for h in chain.hops] == [(_item(3), _item(2)), (_item(2), _item(1))]
    assert found.chained == frozenset(chain.members)


def test_a_hop_lists_the_feeder_pin_and_the_fed_pin_it_is_wired_to() -> None:
    """Hop 1 to 2 is device 1's down port to device 2's up port."""
    block = _line(1, 2)
    (hop,) = block.run().chains[0].hops
    assert [(p.feeder, p.fed) for p in hop.pins] == [(block.port(1, "down"), block.port(2, "up"))]


def test_a_ring_starts_at_its_lowest_designation_and_closes_back_to_it() -> None:
    """Devices 1-2-3 wired in a ring; device 3 leads, device 1 is its lower neighbour."""
    block = _line(2, 3, 1)
    block.wire(3, 1)
    (chain,) = block.run().chains
    assert chain.members == (_item(3), _item(1), _item(2))
    assert chain.closing is not None
    assert (chain.closing.feeder, chain.closing.fed) == (_item(2), _item(3))


def test_a_member_wired_to_a_device_outside_the_shape_drops_the_whole_chain() -> None:
    """Device 3 also wired to device 4, a plain box: the cascade takes 2 and 1 down too."""
    block = _line(1, 1, 1)
    block.device(4, connector=False, boxed=False)
    block.wire(3, 4)
    assert block.run().chains == ()


def test_a_line_of_devices_with_no_connector_beside_a_function_is_no_chain() -> None:
    """Three boxed devices in a line, none holding a connector."""
    block = _Block()
    for n in (1, 2, 3):
        block.device(n, connector=False)
    block.wire(1, 2)
    block.wire(2, 3)
    assert block.run() == DeviceChains(chains=())


def test_a_device_with_a_mated_function_is_no_chain() -> None:
    """Device 2's connector is mated, so devices 1 and 3 lose their only neighbour."""
    block = _line(1, 1, 1)
    block.plant.pin("D9", "con", "c")
    block.plant.mate(Plant.function_id("D2", "con"), Plant.function_id("D9", "con"))
    assert block.run().chains == ()


def test_a_wire_on_a_net_group_port_is_not_alone_so_no_chain() -> None:
    """The port of hop 2-3 on device 2 is also in a net group, so that wire is not alone."""
    block = _line(1, 1, 1)
    assert block.run(frozenset({block.port(2, "down")})).chains == ()


def test_devices_in_different_places_are_no_chain() -> None:
    """Devices 1 and 2 are wired, but device 2 stands in another place."""
    block = _Block()
    block.device(1)
    block.device(2, place=2)
    block.wire(1, 2)
    assert block.run().chains == ()
