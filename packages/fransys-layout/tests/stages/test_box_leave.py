"""A boxed connector's hidden pin views leave their columns (layout-0206), on hand-made columns."""

from samples import hid

from fransys_layout.geometry import (
    WIRING_GRID,
    Box,
    Facing,
    Orientation,
    Point,
    PortGeometry,
    SymbolGeometry,
)
from fransys_layout.stages.box_leave import box_columns, narrowed, wired_ends
from fransys_layout.stages.box_views import BoxSpec
from fransys_layout.stages.connector_boxes import box_size, cell_width
from fransys_layout.stages.types import (
    Cell,
    Column,
    Connection,
    DrawnFunction,
    NetGroup,
    PortRef,
    Role,
)

TH = 8
PORTS = tuple(hid("port", n) for n in range(1, 5))


def _spec(*, cells: bool) -> BoxSpec:
    return BoxSpec(
        function=hid("function", 1),
        lines=("-P1",),
        cells=tuple((port, str(n)) for n, port in enumerate(PORTS, 1)) if cells else (),
        ports=PORTS,
    )


def _column(*cells: Cell) -> Column:
    return Column(key=("invented", "a"), cells=cells, group=None, role=Role.CONTROL, location=None)


def _row(lanes: int, **options) -> Column:
    """The four pin views of one connector in one row, then a lamp (function 9) under it."""
    cells = [Cell(function=PORTS[n], index=0, lane=n, **options) for n in range(lanes)]
    return _column(*cells, Cell(function=hid("port", 9), index=1))


def _wire(port) -> Connection:
    ref = PortRef(function=port, port=port)
    other = PortRef(function=hid("port", 8), port=hid("port", 8))
    return Connection(
        handle=hid("conductor", 1), physical_net=hid("net", 1), role=Role.CONTROL, a=ref, b=other
    )


def _kept(column: Column) -> list:
    return [cell.function for cell in column.cells]


def test_a_cell_less_box_keeps_one_pin_view_per_column() -> None:
    (out,) = box_columns([_row(4)], [_spec(cells=False)], [], [])
    assert _kept(out) == [PORTS[0], hid("port", 9)]


def test_a_wired_view_stays_and_the_rest_leave_bar_the_first() -> None:
    (out,) = box_columns([_row(4)], [_spec(cells=False)], [_wire(PORTS[2])], [])
    assert _kept(out) == [PORTS[0], PORTS[2], hid("port", 9)]


def test_a_view_with_a_cell_stays() -> None:
    (out,) = box_columns([_row(4)], [_spec(cells=True)], [], [])
    assert _kept(out) == [*PORTS, hid("port", 9)]


def test_a_view_a_symbol_hangs_on_stays() -> None:
    column = _column(
        Cell(function=PORTS[0], index=0, lane=0),
        Cell(function=PORTS[1], index=0, lane=1),
        Cell(function=hid("port", 9), index=1, host=PORTS[1]),
    )
    (out,) = box_columns([column], [_spec(cells=False)], [], [])
    assert _kept(out) == [PORTS[0], PORTS[1], hid("port", 9)]


def test_the_rows_close_up_after_the_views_leave() -> None:
    (out,) = box_columns([_row(4)], [_spec(cells=False)], [], [])
    assert [cell.index for cell in out.cells] == [0, 1]


def test_wired_ends_hold_the_ends_of_connections_and_net_groups() -> None:
    a, b, c = (PortRef(function=hid("port", n), port=hid("port", n)) for n in (1, 2, 3))
    wire = Connection(
        handle=hid("conductor", 1), physical_net=hid("net", 1), role=Role.CONTROL, a=a, b=b
    )
    group = NetGroup(net=hid("net", 2), physical_net=hid("net", 2), role=Role.CONTROL, ports=(c,))
    assert wired_ends([wire], [group]) == {a.function, b.function, c.function}


def _view(function) -> DrawnFunction:
    """A pin view drawn as a wide symbol, as `narrowed` finds it before it narrows it."""
    body = Box(x=-66, y=-16, width=80, height=32)
    geometry = SymbolGeometry(
        key="contact-female",
        poles=1,
        orientation=Orientation.R0,
        body=body,
        keepout=body,
        through=None,
        ports=(PortGeometry(name="1", at=Point(x=0, y=-16), facing=Facing.N),),
        slots=(),
    )
    return DrawnFunction(
        function=function,
        item=hid("item", 1),
        key=("k",),
        kind="x",
        geometry=geometry,
        ports=(),
        primary_in=None,
        primary_out=None,
    )


def test_narrowed_makes_a_boxed_views_keepout_as_wide_as_its_cell() -> None:
    boxed, other = _view(PORTS[0]), _view(hid("port", 9))
    mine, theirs = narrowed([boxed, other], [_spec(cells=True)], TH, [])
    width = cell_width("1", TH)
    assert mine.geometry.keepout == Box(x=-(width // 2), y=-16, width=width, height=32)
    assert theirs.geometry.keepout == other.geometry.keepout


def test_narrowed_gives_a_cell_less_boxs_one_kept_view_the_whole_box_width() -> None:
    spec = BoxSpec(hid("function", 1), ("-P1-A-LONG-NAME", "FLD-PLG"), (), PORTS[:2])
    kept = _column(Cell(function=PORTS[0], index=0))
    (mine,) = narrowed([_view(PORTS[0])], [spec], TH, [kept])
    wide = box_size(spec.lines, [], text_height=TH)[0]
    assert wide > 2 * WIRING_GRID
    assert mine.geometry.keepout.width == wide
    assert mine.boxed
