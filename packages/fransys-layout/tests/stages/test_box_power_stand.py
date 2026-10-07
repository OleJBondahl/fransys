"""layout-0132: a generic box's port pitch fits the power symbols standing at its pins."""

from dataclasses import replace

from samples import drawn, hid

from fransys_layout.geometry import generic_box_geometry, symbol_geometry, text_width
from fransys_layout.stages import DrawnPort
from fransys_layout.stages.box_power import power_stand
from fransys_layout.stages.boxes import potential_sides


def _psu(stands: dict[str, int]):
    """Function 1: an AC pin `L` on top, a supply pin `+` and a ground pin `-` below it."""
    names = ("L", "+", "-")
    ports = tuple(
        DrawnPort(port=hid("port", 10 + i), symbol_port=n, ac=n == "L", stand=stands.get(n, 0))
        for i, n in enumerate(names)
    )
    return replace(drawn(1), geometry=generic_box_geometry(names), ports=ports)


def _gap(stands: dict[str, int]) -> int:
    """The x distance between the `+` and `-` pins once D5 has put both below."""
    kinds = {hid("port", 11): "supply", hid("port", 12): "ground"}
    (box,) = potential_sides((_psu(stands),), {hid("port", 10): 2}, kinds)
    x = {g.name: g.at.x for g in box.geometry.ports}
    return x["-"] - x["+"]


def test_the_stand_is_the_wider_of_the_symbol_and_its_text() -> None:
    """The symbol's own width, unless its text is wider; both by the one text width."""
    # CAN-FAIL: box_power.py `power_stand`: `max(` -> `min(` fails the long-text case
    bar = symbol_geometry("power-supply").body.width
    long = "+24V DC FEED"
    assert power_stand("power-supply", "24V") == bar
    assert power_stand("power-supply", long) == text_width(long, height=8) > bar


def test_two_power_symbols_at_one_side_stand_a_symbol_width_apart() -> None:
    """`+` and `-` carry a 16 G bar and a 16 G ground: their pins stand 24 G apart, not 16."""
    # CAN-FAIL: generic_box.py `box_pitch`: `max(longest, stand)` -> `longest` (the symbol term)
    # gives 16 G, the two symbols touch and the ground is pushed off the bar's row
    stands = {"+": power_stand("power-supply", "24V"), "-": power_stand("ground", None)}
    assert _gap(stands) >= 24
    assert _gap({}) == 16
