"""Tiny constructors for hand-built stage 1 problems, on the landed values."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from fransys_layout.core.values import (
    Box,
    Hints,
    Net,
    Pin,
    PinRef,
    PlacementProblem,
    Power,
    Side,
    Size,
    Sym,
)

AREA = Size(1312, 854)
LABEL = Size(16, 8)
_POLE_PINS: tuple[tuple[str, Side, int], ...] = (("n", "N", -16), ("s", "S", 16))


def elem(
    sym_id: str,
    width: int = 16,
    *,
    stand_n: Power | None = None,
    stand_s: Power | None = None,
    **kw: Any,
) -> Sym:
    """A two-pin element: pin n on top, pin s below; body, keepout, footprint are `width` wide."""
    box = Box(-(width // 2), -16, width, 32)
    pins = (Pin("n", "N", 0, -16, 0, stand_n), Pin("s", "S", 0, 16, 1, stand_s))
    group = kw.pop("group", None)
    return Sym(
        sym_id,
        group,
        "",
        LABEL,
        box,
        box,
        box,
        pins,
        (("n",), ("s",)),
        frozenset({"R0", "R180"}),
        **kw,
    )


def free(sym_id: str, **kw: Any) -> Sym:
    """A free-sided symbol (a hub): four pins n e s w in one node; kw overrides Sym fields."""
    box = Box(-8, -16, 16, 32)
    pins = (
        Pin("n", "N", 0, -16, 0),
        Pin("e", "E", 8, 0, 0),
        Pin("s", "S", 0, 16, 0),
        Pin("w", "W", -8, 0, 0),
    )
    sym = Sym(
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
    return replace(sym, **kw)


def poles(sym_id: str, count: int = 3) -> Sym:
    """A multi-pole device: pole k has pin n<k> above and s<k> below, 24 G apart."""
    box = Box(-8, -16, 24 * count, 32)
    pins = tuple(
        Pin(f"{c}{k}", side, 24 * k, dy, 2 * k + i)
        for k in range(count)
        for i, (c, side, dy) in enumerate(_POLE_PINS)
    )
    nodes = tuple((p.id,) for p in pins)
    return Sym(sym_id, None, "", LABEL, box, box, box, pins, nodes, frozenset({"R0", "R180"}))


def net(net_id: str, *pins: str, **kw: Any) -> Net:
    """A net over "sym.pin" strings; kw holds rail, bundle or label."""
    return Net(net_id, tuple(PinRef(*p.split(".")) for p in pins), **kw)


def problem(
    syms: list[Sym], nets: list[Net], hints: Hints | None = None, area: Size = AREA
) -> PlacementProblem:
    """A placement problem over the given symbols and nets, default hints and the test area."""
    return PlacementProblem(area, tuple(syms), tuple(nets), hints=hints or Hints())
