"""LC2 (layout-0215): a device chain's boxes take their hop pins on the facing sides, in order."""

from samples import hid

from fransys_layout.geometry import Facing, generic_box_geometry
from fransys_layout.stages import BoxFeed, DrawnFunction, DrawnPort, FedPin
from fransys_layout.stages.boxes import _paired
from fransys_layout.stages.chain_boxes import chain_boxes
from fransys_layout.stages.types import DeviceChain

_LONG = ("b_in_long_name_1", "b_in_long_name_2", "b_out1", "b_out2")


def _box(n: int, names: tuple[str, ...]) -> DrawnFunction:
    """A generic box of function `n`, its pins `names` on ports `n*10+1`, `n*10+2`, ..."""
    return DrawnFunction(
        function=hid("function", n),
        item=hid("item", n),
        key=("invented", f"box{n}"),
        kind="item",
        geometry=generic_box_geometry(names),
        ports=tuple(
            DrawnPort(port=hid("port", n * 10 + k), symbol_port=name)
            for k, name in enumerate(names, start=1)
        ),
        primary_in=None,
        primary_out=None,
    )


def _redrawn(b_names: tuple[str, ...], below: int) -> dict[int, DrawnFunction]:
    """Boxes 1, 2 (`b_names`), 3; box 1 feeds 2 by two pins, box 2 feeds 3 by `below` pins.

    Each hop's pins are in hop order: box 1's ports 11, 12 meet box 2's 21, 22; box 2's
    ports 23, 24, ... meet box 3's 31, 32, ...
    """
    boxes = (
        _box(1, ("a_out1", "a_out2")),
        _box(2, b_names),
        _box(3, tuple(f"c_in{k}" for k in range(1, below + 1))),
    )
    upper = BoxFeed(
        fed=hid("function", 2),
        feeder=hid("function", 1),
        ports=(
            FedPin(fed=hid("port", 21), feeder=hid("port", 11)),
            FedPin(fed=hid("port", 22), feeder=hid("port", 12)),
        ),
    )
    lower = BoxFeed(
        fed=hid("function", 3),
        feeder=hid("function", 2),
        ports=tuple(
            FedPin(fed=hid("port", 30 + k), feeder=hid("port", 22 + k)) for k in range(1, below + 1)
        ),
    )
    chain = DeviceChain(members=tuple(one.function for one in boxes), hops=(upper, lower))
    drawn = chain_boxes(boxes, (chain,))
    return dict(enumerate(drawn, start=1))


def _sided(one: DrawnFunction, facing: Facing) -> tuple[str, ...]:
    """The names of `one`'s pins on `facing`, left to right."""
    pins = sorted((p for p in one.geometry.ports if p.facing is facing), key=lambda p: p.at.x)
    return tuple(p.name for p in pins)


def _x(one: DrawnFunction, name: str) -> int:
    return next(p.at.x for p in one.geometry.ports if p.name == name)


def _from_axis(one: DrawnFunction, facing: Facing) -> list[int]:
    """The x of `one`'s pins on `facing`, less the x of its axis (`primary_in`, else out)."""
    axis = one.primary_in or one.primary_out
    assert axis is not None
    return [_x(one, name) - _x(one, axis) for name in _sided(one, facing)]


def test_each_box_takes_its_upper_hop_pins_on_top_and_its_lower_hop_pins_beneath_in_order() -> None:
    """Box 2's top pins are those fed by box 1, its bottom pins those that feed box 3."""
    boxes = _redrawn(_LONG, below=2)
    assert _sided(boxes[2], Facing.N) == ("b_in_long_name_1", "b_in_long_name_2")
    assert _sided(boxes[2], Facing.S) == ("b_out1", "b_out2")
    assert _sided(boxes[1], Facing.N) == ()
    assert _sided(boxes[1], Facing.S) == ("a_out1", "a_out2")
    assert _sided(boxes[3], Facing.N) == ("c_in1", "c_in2")
    assert _sided(boxes[3], Facing.S) == ()


def test_each_hop_wire_runs_straight_down_whatever_the_boxes_natural_pitches() -> None:
    """Box 1's and box 2's pitches differ, yet each hop's pins stand at the same offset."""
    boxes = _redrawn(_LONG, below=2)
    for upper, lower in ((1, 2), (2, 3)):
        offsets = _from_axis(boxes[upper], Facing.S)
        assert len(offsets) == 2
        assert offsets == _from_axis(boxes[lower], Facing.N)


def test_a_chain_box_draws_only_its_wired_pins_in_hop_order() -> None:
    """Box 2's `b_extra` is on no hop: it is not drawn, whichever side it would have fallen on."""
    for names, below in ((("b_in1", "b_in2", "b_out1", "b_extra"), 1), ((*_LONG, "b_extra"), 2)):
        box = _redrawn(names, below=below)[2]
        assert "b_extra" not in {p.name for p in box.geometry.ports}
        assert _sided(box, Facing.N) == (names[0], names[1])
        assert _sided(box, Facing.S) == names[2 : 2 + below]


def test_every_redrawn_box_is_chained_and_paired() -> None:
    """A chain's boxes keep their pin order and x: each is `chained`, and `_paired` holds."""
    for one in _redrawn(_LONG, below=2).values():
        assert one.chained
        assert _paired(one)
