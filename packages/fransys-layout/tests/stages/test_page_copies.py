"""`with_page_copies` (layout-0216): a terminal stands on each page that seats a device it wires to.

Terminal 5 stands on page 1 (set 1); devices stand on page 2. Every symbol is the samples'
vertical through symbol: `in` (port `n1`) on top facing N, `out` (port `n2`) below facing S.
"""

from dataclasses import replace

from samples import column, drawn, hid, page_plan

from fransys_layout.geometry import Facing, Point, PortGeometry
from fransys_layout.stages.page_copies import with_page_copies
from fransys_layout.stages.types import Cell, Home, PortRef


def _ref(number: int, end: str = "in") -> PortRef:
    """The `in` or `out` end of function `number`."""
    return PortRef(
        function=hid("function", number), port=hid("port", number * 10 + (end == "out") + 1)
    )


def _copies(columns):
    """The cells of `columns` marked as a copy at its wire."""
    return [cell for col in columns for cell in col.cells if cell.at_wire]


def test_a_terminal_is_copied_beside_its_device_on_another_page() -> None:
    """Terminal 5 (page 1) wired to device 1 (page 2) gets one copy attached at the device."""
    terminal, device = column("t", (5,)), column("d", (1,))
    plans = (page_plan(("t",), number=1), page_plan(("d",), number=2))

    result = with_page_copies(
        plans, (terminal, device), (drawn(1), drawn(5)), [(_ref(5), _ref(1, "in"))]
    )

    (copy,) = _copies(result)
    assert (copy.function, copy.host, copy.home) == (
        hid("function", 5),
        hid("function", 1),
        Home.ELSEWHERE,
    )
    assert result[0] == terminal


def test_a_page_that_seats_the_terminal_gets_no_copy() -> None:
    """Page 2 seats terminal 5 already, so the columns come back unchanged."""
    terminal, device = column("t", (5,)), column("d", (1,))
    plans = (page_plan(("t",), number=1), page_plan(("d", "t"), number=2))

    result = with_page_copies(plans, (terminal, device), (drawn(1), drawn(5)), [(_ref(5), _ref(1))])

    assert result == (terminal, device)


def test_a_page_of_another_drawing_set_gets_no_copy() -> None:
    """Terminal 5 stands nowhere in set 2, so device 1 on a set 2 page gets none."""
    terminal, device = column("t", (5,)), column("d", (1,))
    plans = (page_plan(("t",)), replace(page_plan(("d",), number=1), drawing_set=2))

    result = with_page_copies(plans, (terminal, device), (drawn(1), drawn(5)), [(_ref(5), _ref(1))])

    assert result == (terminal, device)


def test_a_far_pin_facing_east_gets_no_copy() -> None:
    """Device 1's `in` pin faces E: nothing attaches above or below it."""
    terminal, device = column("t", (5,)), column("d", (1,))
    plans = (page_plan(("t",), number=1), page_plan(("d",), number=2))
    side = drawn(1)
    ports = (
        PortGeometry(name="in", at=Point(x=0, y=-16), facing=Facing.E),
        PortGeometry(name="out", at=Point(x=0, y=16), facing=Facing.S),
    )
    side = replace(side, geometry=replace(side.geometry, ports=ports))

    result = with_page_copies(plans, (terminal, device), (side, drawn(5)), [(_ref(5), _ref(1))])

    assert result == (terminal, device)


def test_two_devices_on_a_page_give_one_copy_at_the_first_end_in_port_order() -> None:
    """Terminal 5 wired to devices 1 and 2 on page 2 is copied once, at device 1."""
    terminal, devices = column("t", (5,)), column("d", (1, 2))
    plans = (page_plan(("t",), number=1), page_plan(("d",), number=2))
    ends = [(_ref(5), _ref(2)), (_ref(5), _ref(1))]

    result = with_page_copies(plans, (terminal, devices), (drawn(1), drawn(2), drawn(5)), ends)

    (copy,) = _copies(result)
    assert copy.host == hid("function", 1)


def test_a_host_with_an_attached_cell_at_another_pin_still_takes_a_copy() -> None:
    """model-0220: the guard is per pin; a cell at device 1's `out` leaves its `in` free."""
    other = Cell(
        function=hid("function", 7), index=1, host=hid("function", 1), port="out", home=Home.MOVED
    )
    terminal, device = column("t", (5,)), column("d", (1,))
    device = replace(device, cells=(*device.cells, other))
    plans = (page_plan(("t",), number=1), page_plan(("d",), number=2))

    result = with_page_copies(plans, (terminal, device), (drawn(1), drawn(5)), [(_ref(5), _ref(1))])

    (copy,) = _copies(result)
    assert (copy.function, copy.host, copy.port) == (hid("function", 5), hid("function", 1), "in")


def test_a_pin_that_holds_an_attached_cell_takes_no_copy() -> None:
    """A cell already attached at device 1's `in` keeps that pin."""
    other = Cell(
        function=hid("function", 7), index=1, host=hid("function", 1), port="in", home=Home.MOVED
    )
    terminal, device = column("t", (5,)), column("d", (1,))
    device = replace(device, cells=(*device.cells, other))
    plans = (page_plan(("t",), number=1), page_plan(("d",), number=2))

    result = with_page_copies(plans, (terminal, device), (drawn(1), drawn(5)), [(_ref(5), _ref(1))])

    assert result == (terminal, device)
