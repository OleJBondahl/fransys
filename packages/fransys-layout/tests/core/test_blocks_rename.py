"""Stage 2 reads no id text beyond `natural_key`: respelling every id, or reversing the input
tuples, changes nothing (layout-0275)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, NamedTuple

import pytest

from fransys_layout.core import natural_key
from fransys_layout.core.values import (
    Attach,
    Block,
    Column,
    End,
    Fan,
    Hints,
    Lane,
    PinRef,
    Sym,
)

from .blocks_fixtures import box_case, build, fan, loose

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

# (column, symbol, fan, group) formats: each keeps the natural order of the ids and spells it anew
SPELLINGS = (("C{}", "=Y{}", "F{}", "G{}"), ("Q{:04d}", "=Z{:04d}", "R{:04d}", "H{:04d}"))


@dataclass(frozen=True)
class World:
    syms: tuple[Sym, ...]
    cols: tuple[Column, ...]
    fans: tuple[Fan, ...]
    hints: Hints


def card_case() -> World:
    """A box with twelve columns on its pins."""
    syms, cols = box_case(12, 64)
    return World(tuple(syms), tuple(cols), (), Hints(group_order=("PLC", "CH")))


def fan_case() -> World:
    """A fan of three columns of group A beside a column of group B; the chain swaps two."""
    syms, cols = loose("A", "A", "A", "B")
    hints = Hints(group_order=("A", "B"), chains=(("s3", "s1"),))
    return World(tuple(syms), tuple(cols), (fan("f1", "c1", "c2", "c3"),), hints)


def groups_case() -> World:
    """Twelve free columns in two groups, a pair hint and a break: c2 sorts before c10."""
    syms, cols = loose(*["A"] * 10, "B", "B")
    hints = Hints(
        group_order=("A", "B"), order_pairs=(("s12", "s1"),), break_before=frozenset({"B"})
    )
    return World(tuple(syms), tuple(cols), (), hints)


CASES: dict[str, Callable[[], World]] = {
    "card": card_case,
    "fan": fan_case,
    "groups": groups_case,
}


def spell(ids: Iterable[str], form: str) -> dict[str, str]:
    """Rank by `natural_key`, spell the rank anew."""
    return {i: form.format(n) for n, i in enumerate(sorted(set(ids), key=natural_key), 1)}


def maps(w: World, fmt: tuple[str, str, str, str]) -> dict[str, str]:
    """One map over column, symbol, fan and group ids (they never collide)."""
    out = spell((c.id for c in w.cols), fmt[0])
    out |= spell((s.id for s in w.syms), fmt[1])
    out |= spell((f.id for f in w.fans), fmt[2])
    out |= spell((s.group for s in w.syms if s.group), fmt[3])
    return out


def respell(w: World, m: dict[str, str]) -> World:
    def pin(p: PinRef) -> PinRef:
        return replace(p, sym=m.get(p.sym, p.sym))

    def end(e: End) -> End:
        return replace(e, pin=pin(e.pin)) if e.pin else e

    def attach(a: Attach) -> Attach:
        return replace(a, column=m[a.column] if a.column else None, pin=pin(a.pin))

    def lane(ln: Lane) -> Lane:
        return replace(ln, cells=tuple(replace(c, sym=m[c.sym]) for c in ln.cells))

    syms = tuple(replace(s, id=m[s.id], group=m[s.group] if s.group else None) for s in w.syms)
    cols = tuple(
        replace(
            c,
            id=m[c.id],
            lanes=tuple(map(lane, c.lanes)),
            heads=tuple(map(end, c.heads)),
            feet=tuple(map(end, c.feet)),
        )
        for c in w.cols
    )
    fans = tuple(
        replace(
            f, id=m[f.id], drivers=tuple(map(attach, f.drivers)), legs=tuple(map(attach, f.legs))
        )
        for f in w.fans
    )
    h = w.hints
    hints = Hints(
        group_order=tuple(m[g] for g in h.group_order),
        break_before=frozenset(m[g] for g in h.break_before),
        keep_together=tuple(frozenset(m[n] for n in s) for s in h.keep_together),
        order_pairs=tuple((m[a], m[b]) for a, b in h.order_pairs),
        chains=tuple(tuple(m[n] for n in c) for c in h.chains),
    )
    return World(syms, cols, fans, hints)


def reverse(w: World) -> World:
    """Every input tuple reversed but the group order, which is the meaning of the hint."""
    h = w.hints
    hints = replace(
        h,
        keep_together=h.keep_together[::-1],
        order_pairs=h.order_pairs[::-1],
        chains=h.chains[::-1],
    )
    fans = tuple(replace(f, legs=f.legs[::-1], drivers=f.drivers[::-1]) for f in w.fans[::-1])
    return World(w.syms[::-1], w.cols[::-1], fans, hints)


class Row(NamedTuple):
    """A block without its opaque id."""

    kind: str
    unit: str
    group: str | None
    anchor: str | None
    cols: tuple[str, ...]
    fan: str | None
    sizes: tuple[int, int, bool, bool, bool]
    pin_edges: tuple[tuple[str, str], ...]
    fixed: bool


def summary(b: Block) -> Row:
    sizes = (b.width_est, b.height_est, b.short, b.keep_whole, b.forced_break_before)
    return Row(
        b.kind, b.unit, b.group, b.anchor, b.columns, b.fan, sizes, b.pin_edges, b.fixed_order
    )


def result(w: World) -> list[tuple[str, list[Row], list[str]]]:
    lists = build(w.syms, w.cols, w.fans, w.hints)
    return [
        (bl.unit, [summary(b) for b in bl.blocks], [f.code for f in bl.findings]) for bl in lists
    ]


def through(
    want: list[tuple[str, list[Row], list[str]]], m: dict[str, str]
) -> list[tuple[str, list[Row], list[str]]]:
    """The original's listing with its group, anchor, column and fan ids sent through the map."""

    def one(x: str | None) -> str | None:
        return m[x] if x else None

    def row(r: Row) -> Row:
        cols = tuple(m[c] for c in r.cols)
        return r._replace(group=one(r.group), anchor=one(r.anchor), cols=cols, fan=one(r.fan))

    return [(unit, [row(r) for r in rows], codes) for unit, rows, codes in want]


@pytest.mark.parametrize("case", CASES)
def test_blocks_do_not_depend_on_how_ids_are_spelled(case: str) -> None:
    world = CASES[case]()
    want = result(world)
    for fmt in SPELLINGS:
        m = maps(world, fmt)
        assert result(respell(world, m)) == through(want, m)


@pytest.mark.parametrize("case", CASES)
def test_blocks_do_not_depend_on_the_order_of_the_input_tuples(case: str) -> None:
    world = CASES[case]()
    assert result(reverse(world)) == result(world)
