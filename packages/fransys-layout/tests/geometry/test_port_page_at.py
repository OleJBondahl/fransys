"""`port_page_at`: the one home of a port's position on the page (layout-0083, order Part 7)."""

from fransys_layout.geometry import Facing, Point, PortGeometry, port_page_at


def test_a_port_page_position_is_the_origin_plus_the_port_offset() -> None:
    """Hand-made values: (40, 24) + (8, 16), and (0, 0) + (-16, -8) (a negative offset)."""
    south = PortGeometry(name="out", at=Point(x=8, y=16), facing=Facing.S)
    west = PortGeometry(name="in", at=Point(x=-16, y=-8), facing=Facing.W)
    assert port_page_at(Point(x=40, y=24), south) == Point(x=48, y=40)
    assert port_page_at(Point(x=0, y=0), west) == Point(x=-16, y=-8)
    assert port_page_at(Point(x=40, y=24), west) == Point(x=24, y=16)
