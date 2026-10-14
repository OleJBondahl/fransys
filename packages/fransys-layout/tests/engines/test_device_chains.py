"""LC2, LC3, LC5 (layout-0215): device chains read from the functions and wires of one block."""

import dataclasses
from typing import TYPE_CHECKING, Any

from samples import connection, function_spec, hid

from fransys_layout.engines.schematic.read.device_chains import chain_sides, device_chains
from fransys_layout.stages import FunctionSpec, NetGroup, PortRef, Role

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_layout.stages import Connection
    from fransys_layout.stages.types import DeviceChain
    from fransys_model.kernel import Id


def _item(n: int) -> Id[Any]:
    return hid("item", n)


def _device(
    n: int, *, order: int = 1, group: int = 1, connector: bool = True
) -> list[FunctionSpec]:
    """Device `n`: box function `n`, and a connector beside it unless `connector` is off."""
    box = dataclasses.replace(
        function_spec(n, group=group), item=hid("item", n), designation_order=order
    )
    if not connector:
        return [box]
    side = dataclasses.replace(
        function_spec(50 + n, kind="connector", group=group),
        item=hid("item", n),
        designation_order=order,
    )
    return [box, side]


def _chains(
    specs: Sequence[FunctionSpec],
    connections: tuple[Connection, ...],
    *,
    boxed: set[Id[Any]] | None = None,
    kept: set[Id[Any]] | None = None,
    nets: tuple[NetGroup, ...] = (),
) -> tuple[DeviceChain, ...]:
    """`device_chains` with the facts read the way the layout reads them."""
    if boxed is None:
        boxed = {s.function for s in specs if s.kind != "connector"}
    wired = {port for c in connections for port in (c.a.port, c.b.port)}
    return device_chains(specs, connections, nets, (boxed, wired, kept or set()))


def test_hop_to_hop_devices_form_one_chain_led_by_the_lowest_designation_end() -> None:
    """Devices 1-2-3 wired in a line; device 3 has the lowest designation, so it leads."""
    specs = [*_device(1, order=3), *_device(2, order=1), *_device(3, order=2)]
    wires = (connection(1, 1, 2), connection(2, 2, 3))
    (chain,) = _chains(specs, wires)
    assert chain.members == (_item(3), _item(2), _item(1))
    assert chain.closing is None
    assert [(h.feeder, h.fed) for h in chain.hops] == [
        (_item(3), _item(2)),
        (_item(2), _item(1)),
    ]
    assert _chains(tuple(reversed(specs)), tuple(reversed(wires))) == (chain,)


def test_ring_starts_at_its_lowest_designation_and_closes_back_to_it() -> None:
    """Devices 1-2-3 wired in a ring; device 3 leads, device 1 is its lower neighbour."""
    specs = [*_device(1, order=2), *_device(2, order=3), *_device(3, order=1)]
    wires = (connection(1, 1, 2), connection(2, 2, 3), connection(3, 3, 1))
    (chain,) = _chains(specs, wires)
    assert chain.members == (_item(3), _item(1), _item(2))
    assert chain.closing is not None
    assert (chain.closing.feeder, chain.closing.fed) == (_item(2), _item(3))


def test_a_chain_member_wired_to_a_device_outside_the_shape_drops_the_whole_chain() -> None:
    """Device 3 also wired to device 4, a plain symbol: the cascade takes 2 and 1 down too."""
    specs = [*_device(1), *_device(2), *_device(3), *_device(4, connector=False)]
    wires = (connection(1, 1, 2), connection(2, 2, 3), connection(3, 3, 4))
    boxed = {hid("function", n) for n in (1, 2, 3)}
    assert _chains(specs, wires, boxed=boxed) == ()


def test_a_chain_of_one_function_boxes_without_a_connector_is_no_chain() -> None:
    """Three boxed devices wired in a line, none with a connector beside another function."""
    specs = [
        *_device(1, connector=False),
        *_device(2, connector=False),
        *_device(3, connector=False),
    ]
    assert _chains(specs, (connection(1, 1, 2), connection(2, 2, 3))) == ()


def test_a_device_with_a_function_kept_apart_is_no_chain() -> None:
    """Device 2's box is kept apart (mated), so devices 1 and 3 lose their only neighbour."""
    specs = [*_device(1), *_device(2), *_device(3)]
    wires = (connection(1, 1, 2), connection(2, 2, 3))
    assert _chains(specs, wires, kept={hid("function", 2)}) == ()


def test_a_wire_on_a_net_group_port_is_not_alone_so_no_chain() -> None:
    """The port of hop 2-3 on device 2 is also in a net group, so that wire is not alone."""
    specs = [*_device(1), *_device(2), *_device(3)]
    wires = (connection(1, 1, 2), connection(2, 2, 3))
    group = NetGroup(
        net=hid("net", 90),
        physical_net=hid("net", 90),
        role=Role.CONTROL,
        ports=(PortRef(function=hid("function", 2), port=hid("port", 22)),),
    )
    assert _chains(specs, wires, nets=(group,)) == ()


def test_devices_in_different_blocks_are_no_chain() -> None:
    """Devices 1 and 2 are wired, but device 2 stands in another `=` block."""
    specs = [*_device(1, group=1), *_device(2, group=2)]
    assert _chains(specs, (connection(1, 1, 2),)) == ()


def test_chain_sides_put_fed_pins_on_top_and_feeder_pins_beneath_sorted() -> None:
    """Chain 3-2-1: device 2 is fed on port 22 by device 3 and feeds device 1 on port 21."""
    specs = [*_device(1, order=3), *_device(2, order=1), *_device(3, order=2)]
    (chain,) = _chains(specs, (connection(1, 1, 2), connection(2, 2, 3)))
    north, south = chain_sides((chain,))
    assert north == tuple(sorted([hid("port", 12), hid("port", 22)]))
    assert south == tuple(sorted([hid("port", 21), hid("port", 31)]))
