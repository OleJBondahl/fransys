"""Hand-built Sym, Column, Block and PlacedColumn values for the packing tests."""

from fransys_layout.core.pack import PlacedColumn
from fransys_layout.core.values import (
    Block,
    Box,
    BoxSpec,
    Cell,
    Column,
    End,
    Lane,
    Pin,
    PinRef,
    RowPlan,
    Size,
    Sym,
)


def elem(
    sym_id: str,
    *,
    body: Box | None = None,
    keepout: Box | None = None,
    footprint: Box | None = None,
) -> Sym:
    """A two-pin element, pin n above and pin s below; keepout and footprint default to the body."""
    box = body or Box(-8, -16, 16, 32)
    pins = (Pin("n", "N", 0, -16, 0), Pin("s", "S", 0, 16, 1))
    return Sym(
        sym_id,
        None,
        "",
        Size(0, 0),
        box,
        keepout or box,
        footprint or box,
        pins,
        (("n",), ("s",)),
        frozenset({"R0", "R180"}),
    )


def card(sym_id: str, pin_count: int, pitch: int = 16) -> Sym:
    """A box symbol whose pins p1.. face south in marking order."""
    body = Box(0, 0, pitch * (pin_count + 1), 32)
    pins = tuple(Pin(f"p{i}", "S", pitch * i, 32, i - 1) for i in range(1, pin_count + 1))
    spec = BoxSpec(tuple(p.id for p in pins), "S", pitch, pitch)
    return Sym(
        sym_id,
        None,
        "",
        Size(0, 0),
        body,
        body,
        body,
        pins,
        tuple((p.id,) for p in pins),
        frozenset({"R0"}),
        box=spec,
    )


def lane(*syms: str, offset: int = 0) -> Lane:
    """A lane of R0 cells, each with its n pin on top and s pin below."""
    return Lane(tuple(Cell(s, "R0", "n", "s") for s in syms), offset)


def column(col_id: str, *lanes: Lane, head: End | None = None) -> Column:
    """A column of the given lanes; head is the end of lane 0 (open otherwise)."""
    heads = tuple(head if (i == 0 and head) else End("open") for i in range(len(lanes)))
    return Column(col_id, lanes, heads, tuple(End("open") for _ in lanes), 0, 0)


def boxpin_end(box: str, pin: str) -> End:
    return End("boxpin", pin=PinRef(box, pin))


def card_block(
    box: str, columns: tuple[str, ...], edges: tuple[tuple[str, str], ...], block_id: str = ""
) -> Block:
    return Block(
        block_id or f"b:{box}",
        "card",
        "u",
        columns,
        box,
        None,
        None,
        0,
        0,
        short=False,
        keep_whole=False,
        forced_break_before=False,
        seat="none",
        pin_edges=edges,
    )


def free_block(block_id: str, columns: tuple[str, ...]) -> Block:
    return Block(
        block_id,
        "column",
        "u",
        columns,
        None,
        None,
        None,
        0,
        0,
        short=False,
        keep_whole=False,
        forced_break_before=False,
        seat="none",
    )


def row_of(columns: tuple[str, ...], blocks: tuple[str, ...]) -> RowPlan:
    return RowPlan(columns, blocks, 0)


def placed(col_id: str, *syms: str, offset: int = 0, row: int = 0) -> PlacedColumn:
    """A one-lane placed column of the given symbols."""
    ln = lane(*syms, offset=offset)
    return PlacedColumn(col_id, (ln.cells,), (offset,), row, flipped=False)
