"""Stage 3 reads no id text beyond `natural_key`: respelling the ids or reordering the input
tuples changes nothing."""

from __future__ import annotations

from dataclasses import replace

import pytest

from fransys_layout.core import (
    Attach,
    Block,
    End,
    FlowGraph,
    natural_key,
    order_columns,
)

from .order_fixtures import OPTIONS, block, box_column, comb, flow

# (column id format, symbol id format): both keep the natural order of the ids, each spells it anew
SPELLINGS = (("C{}", "=Y{}"), ("Q{:04d}", "=Z{:04d}"))


def card() -> tuple[Block, FlowGraph]:
    """Twelve columns on box pins 1 to 12; the box lists pins 3, 1, 2 and the rest tie."""
    cols = [f"c{i:02d}" for i in range(1, 13)]
    edges = (("3", "N"), ("1", "N"), ("2", "N"))
    columns = [box_column(c, str(i)) for i, c in enumerate(cols, 1)]
    return block(cols, kind="card", pin_edges=edges), flow(columns=columns)


CASES = {"twelve": lambda: comb(12), "thirteen": lambda: comb(13), "card": card}


def attaches(fl: FlowGraph) -> list[Attach]:
    found = [a for f in fl.fans for a in (*f.drivers, *f.legs)]
    return found + [a for x in fl.cross_links for a in x.ends]


def spell_maps(
    fl: FlowGraph, blk: Block, fmt: tuple[str, str]
) -> tuple[dict[str, str], dict[str, str]]:
    """Column and symbol id maps: rank by `natural_key`, spell the rank anew."""
    cols = {*blk.columns, *(c.id for c in fl.columns)}
    syms = {a.pin.sym for a in attaches(fl)}
    syms |= {e.pin.sym for c in fl.columns for e in (*c.heads, *c.feet) if e.pin}

    def spell(ids: set[str], form: str) -> dict[str, str]:
        ranked = sorted(ids, key=natural_key)
        return {i: form.format(n) for n, i in enumerate(ranked, 1)}

    return spell(cols, fmt[0]), spell(syms, fmt[1])


def respell(
    fl: FlowGraph, blk: Block, cm: dict[str, str], sm: dict[str, str]
) -> tuple[Block, FlowGraph]:
    def attach(a: Attach) -> Attach:
        return replace(
            a, column=cm[a.column] if a.column else None, pin=replace(a.pin, sym=sm[a.pin.sym])
        )

    def end(e: End) -> End:
        return replace(e, pin=replace(e.pin, sym=sm[e.pin.sym])) if e.pin else e

    fans = tuple(
        replace(f, drivers=tuple(map(attach, f.drivers)), legs=tuple(map(attach, f.legs)))
        for f in fl.fans
    )
    links = tuple(replace(x, ends=tuple(map(attach, x.ends))) for x in fl.cross_links)
    cols = tuple(
        replace(c, id=cm[c.id], heads=tuple(map(end, c.heads)), feet=tuple(map(end, c.feet)))
        for c in fl.columns
    )
    return (
        replace(blk, columns=tuple(cm[c] for c in blk.columns)),
        replace(fl, fans=fans, cross_links=links, columns=cols),
    )


def result(blk: Block, fl: FlowGraph) -> tuple[str, ...]:
    return order_columns(blk, fl, OPTIONS).columns


@pytest.mark.parametrize("case", CASES)
def test_order_does_not_depend_on_how_ids_are_spelled(case: str) -> None:
    blk, fl = CASES[case]()
    want = result(blk, fl)
    assert list(want) != sorted(blk.columns, key=natural_key)  # the order moved: not vacuous
    for fmt in SPELLINGS:
        cm, sm = spell_maps(fl, blk, fmt)
        back = {new: old for old, new in cm.items()}
        got = result(*respell(fl, blk, cm, sm))
        assert tuple(back[c] for c in got) == want


@pytest.mark.parametrize("case", CASES)
def test_order_does_not_depend_on_the_order_of_the_input_tuples(case: str) -> None:
    blk, fl = CASES[case]()
    flipped = replace(
        fl,
        fans=fl.fans[::-1],
        cross_links=fl.cross_links[::-1],
        columns=fl.columns[::-1],
    )
    assert result(replace(blk, columns=blk.columns[::-1]), flipped) == result(blk, fl)
