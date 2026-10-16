"""Hand-built symbols, nets and a cut wrapper for the cut tests.

Every Sym here has the designation label Size(16, 8): the cut tests do not vary it.
"""

from __future__ import annotations

from itertools import pairwise
from typing import TYPE_CHECKING

from fransys_layout.core import (
    Box,
    BoxSpec,
    Facts,
    Hints,
    Net,
    Options,
    Pin,
    PinRef,
    PlacementProblem,
    Size,
    Sym,
)

from . import pipeline_fixtures

if TYPE_CHECKING:
    from fransys_layout.core.values import CutResult, Ref

AREA = Size(1312, 854)
LABEL = Size(16, 8)


def elem(sym_id: str, width: int = 16, height: int = 32, group: str | None = None) -> Sym:
    """A two-pin element, pin n on top and pin s below."""
    box = Box(-(width // 2), -(height // 2), width, height)
    pins = (Pin("n", "N", 0, -(height // 2), 0), Pin("s", "S", 0, height // 2, 1))
    return Sym(
        sym_id, group, "", LABEL, box, box, box, pins, (("n",), ("s",)), frozenset({"R0", "R180"})
    )


def free(sym_id: str) -> Sym:
    """A free-sided symbol: four pins in one node, so a fan may copy it."""
    box = Box(-8, -16, 16, 32)
    pins = (
        Pin("n", "N", 0, -16, 0),
        Pin("e", "E", 8, 0, 0),
        Pin("s", "S", 0, 16, 0),
        Pin("w", "W", -8, 0, 0),
    )
    return Sym(
        sym_id,
        None,
        "",
        LABEL,
        box,
        box,
        box,
        pins,
        (("e", "n", "s", "w"),),
        frozenset({"R0", "R180"}),
    )


def side(sym_id: str, width: int, height: int, group: str | None = None) -> Sym:
    """One pin e on the east side, so the symbol stands alone in its column."""
    box = Box(-(width // 2), -(height // 2), width, height)
    return Sym(
        sym_id,
        group,
        "",
        LABEL,
        box,
        box,
        box,
        (Pin("e", "E", width // 2, 0, 0),),
        (("e",),),
        frozenset({"R0"}),
    )


def box_sym(count: int) -> Sym:
    """A box A1 of `count` pins p1.. facing south, marking order p1.., natural edge S."""
    body = Box(0, 0, 16 * count + 16, 120)
    pins = tuple(Pin(f"p{i}", "S", 16 * i, 120, i - 1) for i in range(1, count + 1))
    spec = BoxSpec(tuple(p.id for p in pins), "S", 16, 16)
    return Sym(
        "A1",
        "PLC",
        "",
        LABEL,
        body,
        body,
        body,
        pins,
        tuple((p.id,) for p in pins),
        frozenset({"R0"}),
        box=spec,
    )


def net(net_id: str, *pins: str, crosses_unit: bool = False) -> Net:
    """A net over "sym.pin" strings."""
    pin_refs = tuple(PinRef(*p.split(".")) for p in pins)
    return Net(net_id, pin_refs, crosses_unit=crosses_unit)


def chain(sym_ids: list[str], prefix: str = "x") -> list[Net]:
    """The two-pin nets that stack the symbols into one column, s of each on n of the next."""
    return [net(f"{prefix}{i}", f"{a}.s", f"{b}.n") for i, (a, b) in enumerate(pairwise(sym_ids))]


def cut_of(
    syms: list[Sym],
    nets: list[Net],
    facts: Facts | None = None,
    hints: Hints | None = None,
    options: Options | None = None,
) -> CutResult:
    """Run stages 1 to 4 on a problem built from these symbols and nets."""
    prob = PlacementProblem(AREA, tuple(syms), tuple(nets), facts or Facts(), hints or Hints())
    return pipeline_fixtures.cut_of(prob, options)


def refs_of(result: CutResult, kind: str) -> list[Ref]:
    """The reference-plan entries of one kind."""
    return [r for r in result.spec.reference_plan if r.kind == kind]


def page_of(result: CutResult) -> dict[str, int]:
    """The page number of each column."""
    return {col: p.page for p in result.spec.pages for row in p.rows for col in row.columns}
