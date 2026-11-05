"""The house conventions a placement test builds: `layout.toml`'s table, read as the facade does."""

import tomllib
from dataclasses import replace
from pathlib import Path

from fransys_el import Conventions, house_conventions

import fransys_layout
from electrical_symbols import LIBRARY
from fransys_layout.core import PinRef, PlacementProblem

LAYOUT = tomllib.loads((Path(fransys_layout.__file__).parent / "layout.toml").read_text(encoding="utf-8"))["layout"]


def house() -> Conventions:
    """The house conventions of the stock library and `layout.toml`."""
    return house_conventions(LAYOUT, LIBRARY, text_height=8)


def unwired(problem: PlacementProblem) -> PlacementProblem:
    """`problem` with no wire drawn: each unit boundary pin has one required conductor to a pin outside it, so the cut stubs it (R407)."""
    edge = {p for u in problem.facts.units for p in u.boundary}
    out = tuple((p, PinRef("out", f"{p.sym}.{p.pin}")) for p in sorted(edge, key=lambda p: (p.sym, p.pin)))
    return replace(problem, facts=replace(problem.facts, far_ends=out, groups=out))
