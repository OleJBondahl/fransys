"""Helpers of test_order.py: hand-built flows, an independent cost and a brute-force oracle."""

from __future__ import annotations

import itertools
import random

from options_fixtures import core_options

from fransys_layout.core import Options, PinRef, natural_key, order
from fransys_layout.core.values import (
    Attach,
    Block,
    BlockKind,
    Column,
    CrossLink,
    CycleSplit,
    End,
    Fan,
    FlowGraph,
)

OPTIONS = core_options(
    flip_turn="R180",
    tag_stagger=True,
    label_gap=8,
    parallel_pitch=48,
    driver_first=True,
    arrow_sides=("E", "W"),
)


def att(col: str, sym: str | None = None) -> Attach:
    return Attach(col, 0, 0, PinRef(sym or f"=S{col}", "1"), net="n")


def fan(fid: str, legs: list[str], drivers: list[str] | None = None, lanes: int = 1) -> Fan:
    return Fan(
        fid,
        (fid,),
        tuple(att(c) for c in drivers or ()),
        tuple(att(c) for c in legs),
        None,
        lanes,
        "above",
    )


def link(net: str, ends: list[str]) -> CrossLink:
    return CrossLink(net, tuple(att(c) for c in ends))


def flow(
    fans: list[Fan] | None = None,
    links: list[CrossLink] | None = None,
    columns: list[Column] | None = None,
) -> FlowGraph:
    return FlowGraph(
        tuple(columns or ()), tuple(fans or ()), tuple(links or ()), (), CycleSplit(0, 0, 0), ()
    )


def block(
    cols: list[str],
    fan_id: str | None = None,
    kind: BlockKind = "fan",
    pin_edges: tuple[tuple[str, str], ...] = (),
    *,
    fixed_order: bool = False,
) -> Block:
    return Block(
        "b",
        kind,
        "u",
        tuple(cols),
        None,
        fan_id,
        None,
        100,
        100,
        short=False,
        keep_whole=False,
        forced_break_before=False,
        seat="none",
        pin_edges=pin_edges,
        fixed_order=fixed_order,
    )


def box_column(col: str, pin: str) -> Column:
    return Column(col, (), (End("boxpin", pin=PinRef("=U1", pin)),), (), 0, 0)


def ordered(blk: Block, fl: FlowGraph, options: Options = OPTIONS) -> list[str]:
    return list(order.order_columns(blk, fl, options).columns)


def comb(n: int) -> tuple[Block, FlowGraph]:
    """n columns dealt to three hubs in turn (c01 to the first, c02 to the second, ...): every two
    hubs interleave."""
    cols = [f"c{i:02d}" for i in range(1, n + 1)]
    return block(cols), flow([fan(f"h{h}", cols[h::3]) for h in range(3)])


def grouped(n: int) -> list[str]:
    """The comb's best order with natural order winning: hub by hub, each hub's columns in natural
    order."""
    cols = [f"c{i:02d}" for i in range(1, n + 1)]
    return cols[0::3] + cols[1::3] + cols[2::3]


def refuse_exact(*_: object) -> None:
    msg = "the exact search ran"
    raise AssertionError(msg)


# ---- a cost written straight from the design's pseudocode, and a brute-force oracle -------------


def ref_cost(perm: list[str] | tuple[str, ...], fl: FlowGraph) -> int:
    pos = {c: i for i, c in enumerate(perm)}
    spans = [({a.column for a in (*f.drivers, *f.legs) if a.column in pos}, False) for f in fl.fans]
    spans += [({a.column for a in x.ends if a.column in pos}, True) for x in fl.cross_links]
    total = 0
    ranges = []
    for members, is_link in spans:
        if len(members) < 2:
            continue
        lo, hi = min(pos[c] for c in members), max(pos[c] for c in members)
        total += hi - lo + 1 - len(members)  # foreign columns inside the span's reach
        if is_link:
            total += hi - lo - 1  # columns strictly between the ends
        ranges.append((lo, hi))
    for (a0, a1), (b0, b1) in itertools.combinations(ranges, 2):
        if a0 < b0 <= a1 < b1 or b0 < a0 <= b1 < a1:
            total += 1  # the two spans interleave
    return total


def keeps_rules(perm: tuple[str, ...], blk: Block, fl: FlowGraph) -> bool:
    """Driver first (unless it is a leg too) and every one-column-per-leg bundle in pole order."""
    pos = {c: i for i, c in enumerate(perm)}
    own = next((f for f in fl.fans if f.id == blk.fan), None)
    if own is not None:
        drivers = [a.column for a in own.drivers if a.column in pos]
        if drivers and drivers[0] not in {a.column for a in own.legs} and perm[0] != drivers[0]:
            return False
    for f in fl.fans:
        legs = [a.column for a in f.legs if a.column in pos]
        if (
            f.lanes > 1
            and len(set(legs)) == len(legs)
            and [pos[c] for c in legs] != sorted(pos[c] for c in legs)
        ):
            return False
    return True


def oracle(blk: Block, fl: FlowGraph) -> list[str]:
    """The first order of least cost over all permutations of the natural order that keep the
    rules."""
    best: list[str] | None = None
    best_cost = 0
    for perm in itertools.permutations(sorted(blk.columns, key=natural_key)):
        if keeps_rules(perm, blk, fl) and (best is None or ref_cost(perm, fl) < best_cost):
            best, best_cost = list(perm), ref_cost(perm, fl)
    assert best is not None
    return best


def random_case(
    seed: int, sizes: tuple[int, ...] = (5, 6, 6, 7), more_fans: tuple[int, int] = (2, 4)
) -> tuple[Block, FlowGraph]:
    """A block fan with an optional driver, other fans (one may be a bundle) and cross-links over n
    columns."""
    rng = random.Random(seed)  # noqa: S311 - seeded test data
    n = rng.choice(sizes)
    cols = [f"c{i}" for i in range(1, n + 1)]
    driver = rng.choice(cols) if rng.random() < 0.5 else None
    rest = [c for c in cols if c != driver]
    fans = [fan("f0", rng.sample(rest, rng.randint(1, len(rest))), [driver] if driver else None)]
    bundled = False
    for k in range(1, rng.randint(*more_fans)):
        bundle = not bundled and rng.random() < 0.4
        bundled = bundled or bundle
        fans.append(
            fan(
                f"f{k}",
                rng.sample(rest if bundle else cols, rng.randint(2, n - 1)),
                None,
                2 if bundle else 1,
            )
        )
    links = [link(f"x{k}", rng.sample(cols, rng.randint(2, 3))) for k in range(rng.randint(0, 2))]
    return block(rng.sample(cols, n), "f0"), flow(fans, links)


# ---- the cost ------------------------------------------------------------------------------------


DENSE_FANS = (
    "10 12",
    "03 09 11",
    "01 02",
    "01 03 11 12",
)  # planted: the sweep ends at cost 11, the optimum is 8
DENSE_LINKS = ("05 09", "06 09", "02 12")


def cs(text: str) -> list[str]:
    return [f"c{n}" for n in text.split()]


def dense() -> tuple[Block, FlowGraph]:
    """Twelve columns, four fans and three cross-links in each other's way: the exact search needs
    about 3000 nodes."""
    fans = [fan(f"f{k}", cs(t)) for k, t in enumerate(DENSE_FANS)]
    links = [link(f"x{k}", cs(t)) for k, t in enumerate(DENSE_LINKS)]
    return block(cs("01 02 03 04 05 06 07 08 09 10 11 12")), flow(fans, links)


def kind_case(sym: str, col: str) -> tuple[list[str], FlowGraph]:
    """Nine columns in three interleaved hubs and a cross-link; symbol ids come from `sym`, column
    ids from `col`."""
    cols = [col.format(i) for i in range(1, 10)]
    fans = [
        Fan(
            f"f{h}",
            (f"n{h}",),
            (),
            tuple(att(cols[i - 1], sym.format(i)) for i in range(h, 10, 3)),
            sym.format(90 + h),
            1,
            "above",
        )
        for h in (1, 2, 3)
    ]
    cross = CrossLink("x", (att(cols[0], sym.format(1)), att(cols[7], sym.format(8))))
    return cols, flow(fans, [cross])


def shuffled(cols: tuple[str, ...], seed: int) -> list[str]:
    """The columns in a seeded random order."""
    return random.Random(seed).sample(list(cols), len(cols))  # noqa: S311 - seeded test data
